import { createHash } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { dirname, relative, resolve, sep } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const GENERATOR_VERSION = "1.0.0";
const workspaceRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const backendRoot = resolve(workspaceRoot, "backend");
const frontendRoot = resolve(workspaceRoot, "frontend");
const outputPath = resolve(workspaceRoot, "docs/generated/project-inventory.json");

const ignoredDirectoryNames = new Set([
  ".git",
  ".next",
  ".pytest_cache",
  ".swc",
  ".uv-cache",
  ".uv-python",
  ".venv",
  "__pycache__",
  "node_modules",
  "playwright-report",
  "test-results",
  "uploads",
  "venv",
]);

function toPosix(path) {
  return path.split(sep).join("/");
}

function walkFiles(root) {
  if (!existsSync(root)) {
    return [];
  }
  const files = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    if (entry.isDirectory() && ignoredDirectoryNames.has(entry.name)) {
      continue;
    }
    const absolutePath = resolve(root, entry.name);
    if (entry.isDirectory()) {
      files.push(...walkFiles(absolutePath));
    } else if (entry.isFile()) {
      files.push(absolutePath);
    }
  }
  return files.sort();
}

function run(command, args, cwd, environment = {}) {
  const result = spawnSync(command, args, {
    cwd,
    env: { ...process.env, ...environment },
    encoding: "utf8",
    maxBuffer: 20 * 1024 * 1024,
    shell: false,
  });
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    process.stderr.write(result.stderr || "");
    throw new Error(`${command} exited with ${result.status}`);
  }
  return result.stdout.trim();
}

function backendInventory() {
  const stdout = run(
    "uv",
    ["run", "--frozen", "python", "-m", "scripts.emit_inventory"],
    backendRoot,
    {
      UV_CACHE_DIR: resolve(backendRoot, ".uv-cache"),
      UV_PYTHON_INSTALL_DIR: resolve(backendRoot, ".uv-python"),
    },
  );
  return JSON.parse(stdout);
}

function exportedNames(source) {
  const names = new Set();
  const pattern = /export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+([A-Za-z_$][\w$]*)/gu;
  for (const match of source.matchAll(pattern)) {
    names.add(match[1]);
  }
  return [...names].sort();
}

function routePath(pagePath) {
  const appRoot = resolve(frontendRoot, "src/app");
  const directory = dirname(pagePath);
  const segments = toPosix(relative(appRoot, directory))
    .split("/")
    .filter((segment) => segment && !(segment.startsWith("(") && segment.endsWith(")")));
  return segments.length === 0 ? "/" : `/${segments.join("/")}`;
}

function routeScope(relativePath) {
  if (relativePath.includes("/(admin)/")) {
    return "admin_or_teacher";
  }
  if (relativePath.includes("/student/")) {
    return "student";
  }
  if (relativePath.includes("/(auth)/")) {
    return "unauthenticated";
  }
  return "public_or_runtime_guarded";
}

function frontendInventory() {
  const sourceFiles = walkFiles(resolve(frontendRoot, "src"));
  const pageFiles = sourceFiles.filter((path) => /[\\/]page\.tsx$/u.test(path));
  const layoutFiles = sourceFiles.filter((path) => /[\\/]layout\.tsx$/u.test(path));
  const hookFiles = sourceFiles.filter((path) => /[\\/]hooks[\\/]use[^\\/]+\.tsx?$/u.test(path));
  const serviceFiles = sourceFiles.filter((path) => /[\\/]services[\\/][^\\/]+\.tsx?$/u.test(path));
  const bffFiles = sourceFiles.filter((path) => /[\\/]app[\\/]api[\\/].*[\\/]route\.ts$/u.test(path));

  const pages = pageFiles.map((path) => {
    const relativePath = toPosix(relative(workspaceRoot, path));
    return {
      route: routePath(path),
      file: relativePath,
      scope: routeScope(`/${relativePath}`),
    };
  });

  const layouts = layoutFiles.map((path) => {
    const relativePath = toPosix(relative(workspaceRoot, path));
    return {
      file: relativePath,
      route_prefix: routePath(resolve(dirname(path), "page.tsx")),
      scope: routeScope(`/${relativePath}`),
    };
  });

  const describeModules = (paths) =>
    paths.map((path) => ({
      file: toPosix(relative(workspaceRoot, path)),
      exports: exportedNames(readFileSync(path, "utf8")),
    }));

  const bffRoutes = bffFiles.map((path) => {
    const source = readFileSync(path, "utf8");
    const methods = [...source.matchAll(/export\s+const\s+(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b/gu)]
      .map((match) => match[1])
      .sort();
    return {
      file: toPosix(relative(workspaceRoot, path)),
      methods,
    };
  });

  return {
    pages: pages.sort((left, right) => left.route.localeCompare(right.route)),
    layouts: layouts.sort((left, right) => left.file.localeCompare(right.file)),
    hooks: describeModules(hookFiles),
    services: describeModules(serviceFiles),
    bff_routes: bffRoutes.sort((left, right) => left.file.localeCompare(right.file)),
  };
}

function frontendTests() {
  const candidates = [
    ...walkFiles(resolve(frontendRoot, "src")),
    ...walkFiles(resolve(frontendRoot, "tests")),
    ...walkFiles(resolve(frontendRoot, "e2e")),
  ];
  return candidates
    .filter((path) => /\.(test|spec)\.[jt]sx?$/u.test(path))
    .map((path) => {
      const relativePath = toPosix(relative(workspaceRoot, path));
      const source = readFileSync(path, "utf8");
      const testCount = [...source.matchAll(/\b(?:it|test)\s*\(/gu)].length;
      let tier = "unit";
      if (relativePath.includes("/tests/e2e/") || relativePath.includes("/e2e/")) {
        tier = "e2e";
      } else if (relativePath.includes("/tests/component/")) {
        tier = "component";
      }
      return { path: relativePath, tier, test_count: testCount };
    })
    .sort((left, right) => left.path.localeCompare(right.path));
}

function sourceFiles() {
  const paths = [
    ...walkFiles(resolve(backendRoot, "app")),
    ...walkFiles(resolve(backendRoot, "tests")),
    ...walkFiles(resolve(backendRoot, "alembic")),
    ...walkFiles(resolve(backendRoot, "scripts")),
    ...walkFiles(resolve(frontendRoot, "src")),
    ...walkFiles(resolve(frontendRoot, "tests")),
    ...walkFiles(resolve(frontendRoot, "e2e")),
    ...walkFiles(resolve(workspaceRoot, "scripts")),
    resolve(backendRoot, "pyproject.toml"),
    resolve(frontendRoot, "package.json"),
    resolve(frontendRoot, "jest.config.ts"),
    resolve(frontendRoot, "playwright.config.ts"),
    resolve(frontendRoot, "playwright.mocked.config.ts"),
    resolve(workspaceRoot, "config/coverage-baseline.json"),
    resolve(workspaceRoot, "config/architecture-guard-baseline.json"),
    resolve(workspaceRoot, "config/database-model-signature.json"),
    resolve(workspaceRoot, ".github/workflows/ci.yml"),
  ];
  return [...new Set(paths.filter((path) => existsSync(path) && statSync(path).isFile()))].sort();
}

function sourceTreeHash(paths) {
  const hash = createHash("sha256");
  for (const path of paths) {
    hash.update(toPosix(relative(workspaceRoot, path)));
    hash.update("\0");
    hash.update(readFileSync(path));
    hash.update("\0");
  }
  return hash.digest("hex");
}

function gitValue(args) {
  return run("git", args, workspaceRoot);
}

function buildInventory() {
  const backend = backendInventory();
  const frontend = frontendInventory();
  const frontendTestEntries = frontendTests();
  const relevantFiles = sourceFiles();
  const backendTestCount = backend.tests.reduce((sum, entry) => sum + entry.tests.length, 0);
  const frontendTestCount = frontendTestEntries.reduce((sum, entry) => sum + entry.test_count, 0);
  const coverageBaseline = JSON.parse(
    readFileSync(resolve(workspaceRoot, "config/coverage-baseline.json"), "utf8"),
  );

  return {
    schema_version: 1,
    generator_version: GENERATOR_VERSION,
    provenance: {
      source_commit: gitValue(["rev-parse", "HEAD"]),
      source_commit_timestamp: gitValue(["show", "-s", "--format=%cI", "HEAD"]),
      source_tree_sha256: sourceTreeHash(relevantFiles),
      relevant_file_count: relevantFiles.length,
      alembic_heads: backend.alembic_heads,
    },
    summary: {
      sqlalchemy_models: backend.models.length,
      pydantic_schemas: backend.schemas.length,
      fastapi_routes: backend.routes.length,
      next_pages: frontend.pages.length,
      frontend_hooks: frontend.hooks.length,
      frontend_services: frontend.services.length,
      backend_test_functions: backendTestCount,
      frontend_test_calls: frontendTestCount,
    },
    backend: {
      models: backend.models,
      schemas: backend.schemas,
      routes: backend.routes,
    },
    frontend,
    tests: {
      backend: backend.tests,
      frontend: frontendTestEntries,
    },
    coverage: {
      backend: {
        provider: "pytest-cov",
        command: "uv run --frozen python -m scripts.run_coverage",
        baseline_percent: coverageBaseline.backend.lines_percent,
        baseline_status: "measured",
      },
      frontend: {
        provider: "Jest v8 coverage",
        command: "npm run test:unit:coverage",
        baseline_percent: coverageBaseline.frontend.lines_percent,
        baseline_status: "measured",
      },
      changed_code_lines_target_percent: coverageBaseline.changed_code.lines_percent,
    },
  };
}

function stableInventory(value) {
  const clone = structuredClone(value);
  if (clone.provenance) {
    delete clone.provenance.source_commit;
    delete clone.provenance.source_commit_timestamp;
  }
  return clone;
}

function checkInventory(current, quiet = false) {
  if (!existsSync(outputPath)) {
    throw new Error("Generated inventory is missing; run generate first");
  }
  const stored = JSON.parse(readFileSync(outputPath, "utf8"));
  if (JSON.stringify(stableInventory(stored)) !== JSON.stringify(stableInventory(current))) {
    throw new Error(
      "Generated inventory is stale; run `node scripts/project-inventory.mjs generate`",
    );
  }
  if (!quiet) {
    console.log(
      `INVENTORY_OK source_tree_sha256=${current.provenance.source_tree_sha256} files=${current.provenance.relevant_file_count}`,
    );
  }
  return stored;
}

function contextEntries(inventory, term) {
  const groups = {
    models: inventory.backend.models,
    schemas: inventory.backend.schemas,
    api_routes: inventory.backend.routes,
    pages: inventory.frontend.pages,
    layouts: inventory.frontend.layouts,
    hooks: inventory.frontend.hooks,
    services: inventory.frontend.services,
    bff_routes: inventory.frontend.bff_routes,
    backend_tests: inventory.tests.backend,
    frontend_tests: inventory.tests.frontend,
  };
  const result = {};
  for (const [name, entries] of Object.entries(groups)) {
    result[name] = term
      ? entries.filter((entry) => JSON.stringify(entry).toLowerCase().includes(term))
      : entries;
  }
  return result;
}

const mode = process.argv[2];
if (!["generate", "check", "context"].includes(mode)) {
  console.error("Usage: node scripts/project-inventory.mjs <generate|check|context> [term]");
  process.exit(2);
}

try {
  const current = buildInventory();
  if (mode === "generate") {
    mkdirSync(dirname(outputPath), { recursive: true });
    writeFileSync(outputPath, `${JSON.stringify(current, null, 2)}\n`, "utf8");
    console.log(
      `INVENTORY_GENERATED path=${toPosix(relative(workspaceRoot, outputPath))} source_tree_sha256=${current.provenance.source_tree_sha256}`,
    );
  } else if (mode === "check") {
    checkInventory(current);
  } else {
    const stored = checkInventory(current, true);
    const term = process.argv.slice(3).join(" ").trim().toLowerCase();
    console.log(JSON.stringify({ term: term || null, matches: contextEntries(stored, term) }, null, 2));
  }
} catch (error) {
  console.error(`INVENTORY_ERROR ${error.message}`);
  process.exit(1);
}

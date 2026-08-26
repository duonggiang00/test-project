import { readFileSync } from "node:fs";
import { basename, dirname, extname, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

import {
  buildInventory,
  contextEntries,
  outputPath as storedInventoryPath,
  sourceFiles,
  stableInventory,
  toPosix,
  workspaceRoot,
} from "./project-inventory.mjs";

const DEFAULT_MAX_BYTES = 12 * 1024;
const DEFAULT_MAX_LINES = 180;
const MAX_CATEGORY_ENTRIES = 8;
const RISKS = new Set(["L0", "L1", "L2", "L3", "L4"]);
const SOURCE_EXTENSIONS = new Set([".js", ".jsx", ".mjs", ".py", ".ts", ".tsx"]);
const TERM_STOP_WORDS = new Set([
  "admin",
  "app",
  "backend",
  "component",
  "components",
  "frontend",
  "index",
  "lib",
  "page",
  "route",
  "scripts",
  "src",
  "test",
  "tests",
]);

const domainPolicy = {
  workflow: {
    spec: ["## 1. Purpose and authority", "## 10. Testing and CI", "## 11. Agent operating policy"],
    adrs: ["docs/adr/0008-agent-risk-and-verification.md"],
  },
  frontend: {
    spec: ["## 5. Authentication and application boundary", "## 8. Frontend architecture and design", "## 10. Testing and CI"],
    adrs: [
      "docs/adr/0003-bff-cookie-authentication.md",
      "docs/adr/0004-frontend-state-and-data-fetching.md",
      "docs/adr/0005-brutalist-design-system.md",
      "docs/adr/0008-agent-risk-and-verification.md",
    ],
  },
  backend: {
    spec: ["## 4. Backend and data architecture", "## 10. Testing and CI"],
    adrs: [
      "docs/adr/0001-postgresql-and-sqlalchemy-2.md",
      "docs/adr/0002-transaction-boundaries.md",
      "docs/adr/0008-agent-risk-and-verification.md",
    ],
  },
  auth: {
    spec: ["## 3. Roles, permissions, and ownership", "## 5. Authentication and application boundary"],
    adrs: ["docs/adr/0003-bff-cookie-authentication.md", "docs/adr/0008-agent-risk-and-verification.md"],
  },
  database: {
    spec: ["## 4. Backend and data architecture", "## 10. Testing and CI"],
    adrs: [
      "docs/adr/0001-postgresql-and-sqlalchemy-2.md",
      "docs/adr/0002-transaction-boundaries.md",
      "docs/adr/0008-agent-risk-and-verification.md",
    ],
  },
  ai: {
    spec: ["## 9. AI content generation", "## 10. Testing and CI"],
    adrs: ["docs/adr/0006-ai-provider-approval-and-evaluation.md", "docs/adr/0008-agent-risk-and-verification.md"],
  },
  docs: {
    spec: ["## 1. Purpose and authority", "## 11. Agent operating policy"],
    adrs: ["docs/adr/0007-spec-drift-and-source-of-truth.md", "docs/adr/0008-agent-risk-and-verification.md"],
  },
};

function parseArgs(argv) {
  const values = { paths: [], terms: [], format: "markdown" };
  const multiValue = new Set(["--paths", "--terms"]);
  for (let index = 0; index < argv.length; index += 1) {
    const option = argv[index];
    if (multiValue.has(option)) {
      const key = option.slice(2);
      while (argv[index + 1] && !argv[index + 1].startsWith("--")) {
        values[key].push(argv[index + 1]);
        index += 1;
      }
      continue;
    }
    if (["--task", "--risk", "--format"].includes(option)) {
      if (!argv[index + 1] || argv[index + 1].startsWith("--")) {
        throw new Error(`${option} requires a value`);
      }
      values[option.slice(2)] = argv[index + 1];
      index += 1;
      continue;
    }
    if (option === "--help" || option === "help") {
      values.help = true;
      continue;
    }
    throw new Error(`Unknown option: ${option}`);
  }

  if (values.help) return values;
  if (!values.task) throw new Error("--task is required");
  if (!RISKS.has(values.risk)) throw new Error("--risk must be one of L0, L1, L2, L3, or L4");
  if (values.paths.length === 0) throw new Error("--paths requires at least one workspace path");
  if (!["markdown", "json"].includes(values.format)) {
    throw new Error("--format must be markdown or json");
  }
  return values;
}

function normalizedWorkspacePath(input) {
  const absolutePath = resolve(workspaceRoot, input);
  const relativePath = relative(workspaceRoot, absolutePath);
  if (relativePath === ".." || relativePath.startsWith(`..${sep}`)) {
    throw new Error(`Path is outside the workspace: ${input}`);
  }
  return toPosix(relativePath || ".");
}

function inferDomains(paths, terms) {
  const text = [...paths, ...terms].join(" ").toLowerCase();
  const domains = new Set();
  if (paths.some((path) => path.startsWith("frontend/")) || /\b(ui|react|next|bff|browser)\b/u.test(text)) domains.add("frontend");
  if (paths.some((path) => path.startsWith("backend/")) || /\b(fastapi|sqlalchemy|pydantic|endpoint|repository)\b/u.test(text)) domains.add("backend");
  if (/\b(auth|login|logout|permission|ownership|tenant|session|rbac)\b|\b(?:access|refresh) token\b/u.test(text)) domains.add("auth");
  if (/\b(database|postgres|alembic|migration|models?|query)\b/u.test(text)) domains.add("database");
  if (/\b(ai|rag|retrieval|grading|prompt|generation)\b/u.test(text)) domains.add("ai");
  if (paths.some((path) => path.startsWith("docs/"))) domains.add("docs");
  if (paths.some((path) => path === "AGENTS.md" || path.startsWith("scripts/") || path.startsWith(".github/") || path.startsWith("config/"))) domains.add("workflow");
  if (domains.size === 0) domains.add("workflow");
  return [...domains].sort();
}

function relevantTerms(paths, explicitTerms) {
  const terms = new Set(explicitTerms.map((term) => term.trim().toLowerCase()).filter(Boolean));
  for (const path of paths) {
    const withoutExtension = path.slice(0, path.length - extname(path).length);
    for (const part of withoutExtension.split(/[\/._()[\]-]+/u)) {
      const normalized = part.toLowerCase();
      if (normalized.length >= 3 && !TERM_STOP_WORDS.has(normalized)) terms.add(normalized);
    }
  }
  return [...terms].sort();
}

function inventoryState(current, storedPath = storedInventoryPath) {
  try {
    const stored = JSON.parse(readFileSync(storedPath, "utf8"));
    return JSON.stringify(stableInventory(stored)) === JSON.stringify(stableInventory(current))
      ? "current"
      : "stale";
  } catch {
    return "missing";
  }
}

function powershellQuote(value) {
  return `'${value.replaceAll("'", "''")}'`;
}

function headingReference(file, heading) {
  const lines = readFileSync(resolve(workspaceRoot, file), "utf8").split(/\r?\n/u);
  const line = lines.findIndex((value) => value.trim() === heading);
  if (line < 0) throw new Error(`Canonical heading not found: ${file}#${heading}`);
  return { file, heading: heading.replace(/^#+\s+/u, ""), line: line + 1 };
}

function policyReferences(domains, paths, risk) {
  const rules = new Set(["AGENTS.md", "docs/agent-workflows/TASK_RISK_CLASSIFICATION.md"]);
  if (domains.includes("frontend")) rules.add("frontend/AGENTS.md");
  if (domains.includes("backend")) rules.add("backend/AGENTS.md");
  if (paths.some((path) => path.startsWith("frontend/tests/") || /frontend\/src\/.*\.test\./u.test(path))) rules.add("frontend/tests/AGENTS.md");
  if (paths.some((path) => path.startsWith("backend/tests/"))) rules.add("backend/tests/AGENTS.md");

  const specHeadings = new Set();
  const adrs = new Set();
  for (const domain of domains) {
    for (const heading of domainPolicy[domain].spec) specHeadings.add(heading);
    for (const adr of domainPolicy[domain].adrs) adrs.add(adr);
  }
  if (["L3", "L4"].includes(risk)) {
    specHeadings.add("## 1. Purpose and authority");
    specHeadings.add("## 11. Agent operating policy");
  }

  const canonical = [...specHeadings]
    .sort()
    .map((heading) => headingReference("docs/spec/CANONICAL_PROJECT_SPEC.md", heading));
  if (domains.includes("auth")) {
    canonical.push(headingReference("docs/spec/PERMISSION_AND_OWNERSHIP_MATRIX.md", "## 4. Named policies"));
  }
  if (domains.some((domain) => ["backend", "auth", "ai"].includes(domain))) {
    canonical.push(headingReference("docs/spec/ERROR_AND_AUDIT_CONTRACTS.md", "## 1. API error contract"));
  }
  if (domains.includes("ai")) {
    canonical.push(headingReference("docs/spec/ERROR_AND_AUDIT_CONTRACTS.md", "### 2.4 AI metadata"));
  }

  const primaryDomains = new Set();
  if (domains.includes("frontend")) primaryDomains.add("frontend");
  if (domains.some((domain) => ["backend", "auth", "database", "ai"].includes(domain))) primaryDomains.add("backend");
  if (domains.some((domain) => ["workflow", "docs"].includes(domain))) primaryDomains.add("workflow");

  return {
    rules: [...rules].sort(),
    canonical: canonical.sort((left, right) => left.file.localeCompare(right.file) || left.line - right.line),
    adrs: [...adrs].sort(),
    full_spec_required: ["L3", "L4"].includes(risk) || primaryDomains.size >= 2,
  };
}

function relevanceScore(value, terms, paths) {
  const text = JSON.stringify(value).toLowerCase();
  let score = 0;
  for (const term of terms) if (text.includes(term)) score += 3;
  for (const path of paths) {
    const directory = toPosix(dirname(path)).toLowerCase();
    const name = basename(path, extname(path)).toLowerCase();
    if (directory !== "." && text.includes(directory)) score += 4;
    if (name && !TERM_STOP_WORDS.has(name) && text.includes(name)) score += 5;
  }
  return score;
}

function matchedInventory(inventory, terms, paths) {
  const groups = contextEntries(inventory, "");
  const matches = {};
  const truncatedCategories = [];
  for (const [name, entries] of Object.entries(groups)) {
    const relevantEntries = entries
      .map((entry) => ({ entry, score: relevanceScore(entry, terms, paths) }))
      .filter(({ score }) => score > 0)
      .sort((left, right) => right.score - left.score || JSON.stringify(left.entry).localeCompare(JSON.stringify(right.entry)));
    if (relevantEntries.length > MAX_CATEGORY_ENTRIES) truncatedCategories.push(`inventory_matches.${name}`);
    matches[name] = relevantEntries
      .slice(0, MAX_CATEGORY_ENTRIES)
      .map(({ entry }) => compactInventoryEntry(name, entry));
  }
  return { matches, truncatedCategories };
}

function compactInventoryEntry(group, entry) {
  if (group === "models") return { class: entry.class, module: entry.module, table: entry.table };
  if (group === "schemas") return { class: entry.class, module: entry.module };
  if (group === "api_routes") return { path: entry.path, methods: entry.methods, endpoint: entry.endpoint };
  if (group === "pages") return { route: entry.route, file: entry.file, scope: entry.scope };
  if (group === "layouts") return { file: entry.file, route_prefix: entry.route_prefix, scope: entry.scope };
  if (["hooks", "services"].includes(group)) return { file: entry.file, exports: entry.exports };
  if (group === "bff_routes") return { file: entry.file, methods: entry.methods };
  if (group === "backend_tests") return { path: entry.path, test_count: entry.tests?.length ?? entry.test_count ?? null };
  if (group === "frontend_tests") return { path: entry.path, tier: entry.tier, test_count: entry.test_count };
  return entry;
}

function sourceMatches(terms, paths, domains) {
  if (terms.length === 0) return { entries: [], truncated: false };
  const matches = [];
  for (const absolutePath of sourceFiles()) {
    if (!SOURCE_EXTENSIONS.has(extname(absolutePath))) continue;
    const relativePath = toPosix(relative(workspaceRoot, absolutePath));
    const relevantDomain =
      (domains.includes("frontend") && relativePath.startsWith("frontend/")) ||
      (domains.some((domain) => ["backend", "auth", "database", "ai"].includes(domain)) && relativePath.startsWith("backend/")) ||
      (domains.includes("workflow") && (relativePath.startsWith("scripts/") || relativePath.startsWith("config/")));
    if (!relevantDomain) continue;
    const lines = readFileSync(absolutePath, "utf8").split(/\r?\n/u);
    for (let index = 0; index < lines.length; index += 1) {
      const lower = lines[index].toLowerCase();
      if (!terms.some((term) => lower.includes(term))) continue;
      matches.push({
        file: relativePath,
        line: index + 1,
        text: lines[index].trim().replace(/\s+/gu, " ").slice(0, 180),
        score: relevanceScore({ file: relativePath, text: lower }, terms, paths),
      });
    }
  }
  const sortedMatches = matches
    .sort((left, right) => right.score - left.score || left.file.localeCompare(right.file) || left.line - right.line);
  return {
    truncated: sortedMatches.length > MAX_CATEGORY_ENTRIES,
    entries: sortedMatches
    .slice(0, MAX_CATEGORY_ENTRIES)
    .map(({ score: _score, ...entry }) => entry),
  };
}

function dependencyReferences(domains) {
  const dependencies = [];
  if (domains.includes("backend") || domains.includes("database") || domains.includes("auth") || domains.includes("ai")) {
    dependencies.push({ file: "backend/pyproject.toml", lockfile: "backend/uv.lock", tool: "uv" });
  }
  if (domains.includes("frontend") || domains.includes("workflow")) {
    dependencies.push({ file: "frontend/package.json", lockfile: "frontend/package-lock.json", tool: "npm" });
  }
  return dependencies;
}

function verificationCommands(task, risk, domains, inventoryMatches) {
  const commands = [];
  const frontendTests = inventoryMatches.frontend_tests ?? [];
  const backendTests = inventoryMatches.backend_tests ?? [];
  if (backendTests[0]?.path) {
    commands.push(`Set-Location -LiteralPath 'backend'; uv run --frozen pytest -q -p no:cacheprovider '${backendTests[0].path.replace(/^backend\//u, "")}'`);
  }
  if (frontendTests[0]?.path) {
    commands.push(`Set-Location -LiteralPath 'frontend'; npm test -- --runInBand '${frontendTests[0].path.replace(/^frontend\//u, "")}'`);
  }
  if (risk === "L0") {
    commands.push("git diff --check");
    return [...new Set(commands)];
  }
  if (domains.includes("backend") && !domains.includes("frontend")) commands.push(`node scripts/verify.mjs backend --task ${task}`);
  if (domains.includes("frontend") && !domains.includes("backend")) commands.push(`node scripts/verify.mjs frontend --task ${task}`);
  if (domains.includes("workflow") || (domains.includes("frontend") && domains.includes("backend"))) commands.push(`node scripts/verify.mjs fast --task ${task}`);
  if (["L2", "L3", "L4"].includes(risk) && domains.some((domain) => ["backend", "auth", "database", "ai"].includes(domain))) {
    commands.push(`node scripts/verify.mjs integration --task ${task}`);
  }
  if (["L3", "L4"].includes(risk) && domains.includes("database")) commands.push(`node scripts/verify.mjs migration --task ${task}`);
  if (["L2", "L3", "L4"].includes(risk) && domains.includes("frontend")) commands.push(`node scripts/verify.mjs e2e-mocked --task ${task}`);
  commands.push("git diff --check");
  return [...new Set(commands)];
}

function buildPacket({ inventory, task, risk, paths, terms }) {
  const normalizedPaths = paths.map(normalizedWorkspacePath);
  const domains = inferDomains(normalizedPaths, terms);
  const searchTerms = relevantTerms(normalizedPaths, terms);
  const inventoryResult = matchedInventory(inventory, searchTerms, normalizedPaths);
  const inventoryMatches = inventoryResult.matches;
  const sourceResult = sourceMatches(searchTerms, normalizedPaths, domains);
  const allTestMatches = [
    ...(inventoryMatches.backend_tests ?? []).map((entry) => ({ ...entry, path: entry.path?.startsWith("backend/") ? entry.path : `backend/${entry.path}` })),
    ...(inventoryMatches.frontend_tests ?? []),
  ];
  const testMatches = allTestMatches.slice(0, MAX_CATEGORY_ENTRIES);
  delete inventoryMatches.backend_tests;
  delete inventoryMatches.frontend_tests;

  const truncatedCategories = inventoryResult.truncatedCategories
    .filter((category) => !["inventory_matches.backend_tests", "inventory_matches.frontend_tests"].includes(category));
  if (sourceResult.truncated) truncatedCategories.push("source_matches");
  if (allTestMatches.length > MAX_CATEGORY_ENTRIES) truncatedCategories.push("tests");

  const storedState = inventoryState(inventory);
  return {
    schema_version: 1,
    task,
    risk,
    paths: normalizedPaths,
    terms: searchTerms,
    domains,
    inventory: {
      source: "live",
      stored_state: storedState,
      source_tree_sha256: inventory.provenance.source_tree_sha256,
      stored_inventory_is_canonical: storedState === "current",
    },
    policy: policyReferences(domains, normalizedPaths, risk),
    inventory_matches: inventoryMatches,
    source_matches: sourceResult.entries,
    tests: testMatches,
    dependencies: dependencyReferences(domains),
    verification: {
      review: risk === "L0" || risk === "L1" ? "self-review" : "independent review",
      commands: verificationCommands(task, risk, domains, {
        backend_tests: testMatches.filter((entry) => entry.path?.startsWith("backend/")),
        frontend_tests: testMatches.filter((entry) => entry.path?.startsWith("frontend/")),
      }),
    },
    truncated: truncatedCategories.length > 0,
    truncation: { categories: [...new Set(truncatedCategories)].sort() },
    follow_up: searchTerms.length > 0
      ? `rg -n --fixed-strings ${searchTerms.map((term) => `-e ${powershellQuote(term)}`).join(" ")} -- ${normalizedPaths.map(powershellQuote).join(" ")}`
      : null,
    limits: { max_bytes: DEFAULT_MAX_BYTES, max_lines: DEFAULT_MAX_LINES },
  };
}

function renderMarkdown(packet) {
  const lines = [
    `# Task Context: ${packet.task}`,
    "",
    `- Risk: ${packet.risk}`,
    `- Domains: ${packet.domains.join(", ")}`,
    `- Paths: ${packet.paths.join(", ")}`,
    `- Live inventory: ${packet.inventory.stored_state} stored snapshot; source ${packet.inventory.source_tree_sha256}`,
    `- Full canonical spec required: ${packet.policy.full_spec_required ? "yes" : "no"}`,
    "",
    "## Rules",
    ...packet.policy.rules.map((file) => `- ${file}`),
    "",
    "## Canonical sections",
    ...packet.policy.canonical.map((entry) => `- ${entry.file}:${entry.line} — ${entry.heading}`),
    "",
    "## ADRs",
    ...packet.policy.adrs.map((file) => `- ${file}`),
    "",
    "## Inventory matches",
  ];
  for (const [name, entries] of Object.entries(packet.inventory_matches)) {
    if (entries.length === 0) continue;
    lines.push(`### ${name}`);
    for (const entry of entries) lines.push(`- ${JSON.stringify(entry)}`);
  }
  lines.push("", "## Source matches", ...packet.source_matches.map((entry) => `- ${entry.file}:${entry.line} — ${entry.text}`));
  lines.push("", "## Tests", ...packet.tests.map((entry) => `- ${entry.path} (${entry.tier ?? "backend"})`));
  lines.push("", "## Dependencies", ...packet.dependencies.map((entry) => `- ${entry.file}; ${entry.lockfile}; ${entry.tool}`));
  lines.push("", "## Verification", `- Review: ${packet.verification.review}`, ...packet.verification.commands.map((command) => `- \`${command}\``));
  if (packet.truncated) {
    lines.push("", `- Output was truncated in: ${packet.truncation.categories.join(", ")}.`);
  }
  if (packet.follow_up) lines.push(`- Follow-up: \`${packet.follow_up}\``);
  return `${lines.join("\n")}\n`;
}

function renderPacket(packet, format) {
  return format === "json" ? `${JSON.stringify(packet)}\n` : renderMarkdown(packet);
}

function boundedPacket(packet, format, maxBytes = DEFAULT_MAX_BYTES, maxLines = DEFAULT_MAX_LINES) {
  const candidate = structuredClone(packet);
  const collections = [candidate.source_matches, candidate.tests, ...Object.values(candidate.inventory_matches)];
  let output = renderPacket(candidate, format);
  while ((Buffer.byteLength(output, "utf8") > maxBytes || output.split(/\r?\n/u).length > maxLines) && collections.some((items) => items.length > 0)) {
    collections.sort((left, right) => right.length - left.length);
    collections[0].pop();
    candidate.truncated = true;
    candidate.truncation.categories = [...new Set([...candidate.truncation.categories, "packet_budget"])].sort();
    output = renderPacket(candidate, format);
  }
  if (Buffer.byteLength(output, "utf8") > maxBytes || output.split(/\r?\n/u).length > maxLines) {
    throw new Error("Required policy metadata exceeds the task-context output budget");
  }
  return output;
}

function printUsage() {
  console.log("Usage: node scripts/task-context.mjs --task <id> --risk <L0-L4> --paths <path...> [--terms <term...>] [--format markdown|json]");
}

function main(argv = process.argv.slice(2), inventoryFactory = buildInventory) {
  try {
    const options = parseArgs(argv);
    if (options.help) {
      printUsage();
      return 0;
    }
    const packet = buildPacket({ inventory: inventoryFactory(), ...options });
    process.stdout.write(boundedPacket(packet, options.format));
    return 0;
  } catch (error) {
    console.error(`TASK_CONTEXT_ERROR ${error.message}`);
    return 1;
  }
}

const invokedPath = process.argv[1] ? resolve(process.argv[1]) : null;
if (invokedPath === fileURLToPath(import.meta.url)) process.exitCode = main();

export {
  boundedPacket,
  buildPacket,
  inferDomains,
  inventoryState,
  main,
  normalizedWorkspacePath,
  parseArgs,
  policyReferences,
  powershellQuote,
  relevantTerms,
  renderMarkdown,
};

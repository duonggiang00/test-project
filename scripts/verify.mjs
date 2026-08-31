import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { basename, dirname, relative, resolve, sep } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const workspaceRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const backendRoot = resolve(workspaceRoot, "backend");
const frontendRoot = resolve(workspaceRoot, "frontend");
const nodeExecutable = process.execPath;
const workflowReportsRoot = resolve(workspaceRoot, "reports/agent-workflow");
const frontendDependencyRoot = process.env.FRONTEND_NODE_MODULES
  ? resolve(process.env.FRONTEND_NODE_MODULES)
  : resolve(frontendRoot, "node_modules");

mkdirSync(resolve(backendRoot, "reports"), { recursive: true });
mkdirSync(resolve(frontendRoot, "reports"), { recursive: true });

const frontendBins = {
  eslint: resolve(frontendDependencyRoot, "eslint/bin/eslint.js"),
  jest: resolve(frontendDependencyRoot, "jest/bin/jest.js"),
  next: resolve(frontendDependencyRoot, "next/dist/bin/next"),
  playwright: resolve(frontendDependencyRoot, "@playwright/test/cli.js"),
};

const uvEnvironment = {
  UV_CACHE_DIR: process.env.UV_CACHE_DIR ?? resolve(backendRoot, ".uv-cache"),
  UV_PYTHON_INSTALL_DIR: process.env.UV_PYTHON_INSTALL_DIR ?? resolve(backendRoot, ".uv-python"),
};

function command(label, executable, args, cwd, environment = {}) {
  return { label, executable, args, cwd, environment };
}

const steps = {
  env: command(
    "environment contract",
    nodeExecutable,
    [resolve(workspaceRoot, "scripts/validate-env-example.mjs")],
    workspaceRoot,
  ),
  inventory: command(
    "generated project inventory",
    nodeExecutable,
    [resolve(workspaceRoot, "scripts/project-inventory.mjs"), "check"],
    workspaceRoot,
  ),
  architecture: command(
    "architecture and anti-pattern guard",
    nodeExecutable,
    [resolve(workspaceRoot, "scripts/architecture-guard.mjs"), "check"],
    workspaceRoot,
  ),
  openapi: command(
    "generated OpenAPI contract",
    nodeExecutable,
    [resolve(workspaceRoot, "scripts/openapi-contract.mjs"), "check"],
    workspaceRoot,
  ),
  databaseDrift: command(
    "SQLAlchemy and Alembic drift guard",
    nodeExecutable,
    [resolve(workspaceRoot, "scripts/database-model-drift.mjs"), "check"],
    workspaceRoot,
  ),
  githubBranchPolicy: command(
    "GitHub branch protection policy",
    nodeExecutable,
    [resolve(workspaceRoot, "scripts/check-github-branch-policy.mjs")],
    workspaceRoot,
  ),
  aiBaselineIntegrity: command(
    "owner-approved AI baseline integrity",
    "uv",
    [
      "run",
      "--frozen",
      "python",
      "-m",
      "scripts.check_ai_regression_policy",
      "evals/golden/v1.jsonl",
      "evals/baselines/ai-008-v8.comparison.json",
      "--approval-manifest",
      "evals/golden/v1.approval.json",
    ],
    backendRoot,
    uvEnvironment,
  ),
  backendUnit: command(
    "backend unit tests",
    "uv",
    [
      "run",
      "--frozen",
      "pytest",
      "-q",
      "-p",
      "no:cacheprovider",
      "-m",
      "unit",
      "--junitxml=reports/unit.xml",
    ],
    backendRoot,
    uvEnvironment,
  ),
  backendLint: command(
    "backend Python lint baseline",
    "uv",
    ["run", "--frozen", "ruff", "check", "app", "scripts", "tests"],
    backendRoot,
    uvEnvironment,
  ),
  backendType: command(
    "backend Python type baseline",
    "uv",
    ["run", "--frozen", "mypy"],
    backendRoot,
    uvEnvironment,
  ),
  backendContract: command(
    "backend API contract tests",
    "uv",
    [
      "run",
      "--frozen",
      "pytest",
      "-q",
      "-p",
      "no:cacheprovider",
      "-m",
      "contract",
      "--junitxml=reports/contract.xml",
    ],
    backendRoot,
    uvEnvironment,
  ),
  backendIntegration: command(
    "backend PostgreSQL integration tests",
    "uv",
    ["run", "--frozen", "python", "-m", "scripts.run_integration"],
    backendRoot,
    uvEnvironment,
  ),
  backendCoverage: command(
    "backend full-suite coverage",
    "uv",
    [
      "run",
      "--frozen",
      "python",
      "-m",
      "scripts.run_coverage",
    ],
    backendRoot,
    uvEnvironment,
  ),
  migration: command(
    "Alembic upgrade/downgrade/upgrade round trip",
    "uv",
    ["run", "--frozen", "python", "-m", "scripts.run_migration_roundtrip"],
    backendRoot,
    uvEnvironment,
  ),
  frontendLint: command(
    "frontend lint",
    nodeExecutable,
    [frontendBins.eslint, "."],
    frontendRoot,
  ),
  frontendUnit: command(
    "frontend unit tests",
    nodeExecutable,
    [
      frontendBins.jest,
      "--runInBand",
      "--json",
      "--outputFile=reports/jest.json",
    ],
    frontendRoot,
  ),
  frontendCoverage: command(
    "frontend full-source coverage",
    nodeExecutable,
    [
      frontendBins.jest,
      "--runInBand",
      "--coverage",
      "--coverageReporters=json",
      "--coverageReporters=json-summary",
    ],
    frontendRoot,
  ),
  coveragePolicy: command(
    "coverage baseline and changed-code policy",
    nodeExecutable,
    [resolve(workspaceRoot, "scripts/check-coverage.mjs"), "check"],
    workspaceRoot,
  ),
  frontendBuild: command(
    "frontend production build",
    nodeExecutable,
    [frontendBins.next, "build", "--webpack"],
    frontendRoot,
  ),
  e2eMockedBuild: command(
    "mocked E2E production build",
    nodeExecutable,
    [resolve(workspaceRoot, "scripts/build-e2e-mocked.mjs")],
    workspaceRoot,
  ),
  e2eMocked: command(
    "frontend mocked Playwright E2E",
    nodeExecutable,
    [frontendBins.playwright, "test", "--config=playwright.mocked.config.ts"],
    frontendRoot,
  ),
  e2eReal: command(
    "frontend real-backend Playwright E2E",
    "uv",
    [
      "run",
      "--frozen",
      "python",
      "-m",
      "scripts.run_real_e2e",
      "--",
      nodeExecutable,
      frontendBins.playwright,
      "test",
      "--config=playwright.config.ts",
    ],
    backendRoot,
    uvEnvironment,
  ),
  e2eMockedPolicy: command(
    "mocked Playwright flake/owner policy",
    nodeExecutable,
    [
      resolve(workspaceRoot, "scripts/check-playwright-results.mjs"),
      "reports/playwright/mocked.json",
    ],
    frontendRoot,
  ),
  e2eRealPolicy: command(
    "real Playwright flake/owner policy",
    nodeExecutable,
    [
      resolve(workspaceRoot, "scripts/check-playwright-results.mjs"),
      "reports/playwright/real.json",
    ],
    frontendRoot,
  ),
};

const modes = {
  env: [steps.env],
  fast: [
    steps.env,
    steps.githubBranchPolicy,
    steps.aiBaselineIntegrity,
    steps.databaseDrift,
    steps.inventory,
    steps.architecture,
    steps.openapi,
    steps.backendLint,
    steps.backendType,
    steps.backendUnit,
    steps.backendContract,
    steps.frontendLint,
    steps.frontendUnit,
    steps.frontendBuild,
  ],
  backend: [
    steps.aiBaselineIntegrity,
    steps.backendLint,
    steps.backendType,
    steps.backendUnit,
    steps.backendContract,
    steps.backendIntegration,
  ],
  frontend: [
    steps.frontendLint,
    steps.frontendUnit,
    steps.frontendBuild,
  ],
  integration: [steps.backendIntegration],
  contract: [steps.backendContract],
  migration: [steps.migration],
  "ai-baseline-integrity": [steps.aiBaselineIntegrity],
  inventory: [steps.inventory],
  architecture: [steps.architecture],
  openapi: [steps.openapi],
  "database-drift": [steps.databaseDrift],
  coverage: [steps.backendCoverage, steps.frontendCoverage, steps.coveragePolicy],
  e2e: [steps.e2eReal, steps.e2eRealPolicy],
  "e2e-mocked": [steps.e2eMockedBuild, steps.e2eMocked, steps.e2eMockedPolicy],
  "e2e-real": [steps.e2eReal, steps.e2eRealPolicy],
  all: [
    steps.env,
    steps.githubBranchPolicy,
    steps.aiBaselineIntegrity,
    steps.databaseDrift,
    steps.inventory,
    steps.architecture,
    steps.openapi,
    steps.backendLint,
    steps.backendType,
    steps.backendUnit,
    steps.backendContract,
    steps.backendIntegration,
    steps.migration,
    steps.frontendLint,
    steps.frontendUnit,
    steps.frontendBuild,
    steps.e2eReal,
    steps.e2eRealPolicy,
  ],
};

for (const [key, step] of Object.entries(steps)) step.key = key;

const safeResumeSteps = new Set([
  "env",
  "githubBranchPolicy",
  "aiBaselineIntegrity",
  "databaseDrift",
  "inventory",
  "architecture",
  "openapi",
  "backendLint",
  "backendType",
  "backendUnit",
  "backendContract",
  "frontendLint",
  "frontendUnit",
  "frontendBuild",
]);

function printUsage() {
  console.log("Usage: node scripts/verify.mjs <mode> [--compact|--verbose] [--task <id>] [--resume <manifest-path>]");
  console.log(`Modes: ${Object.keys(modes).join(", ")}`);
}

function assertStepDependencies(step) {
  if (step.executable === nodeExecutable && step.args[0]?.includes("node_modules")) {
    if (!existsSync(step.args[0])) {
      throw new Error(
        `Missing ${step.args[0]}. Run npm ci in ${frontendRoot} first.`,
      );
    }
  }
}

function parseOptions(argv) {
  const options = { compact: true, task: "local", resume: null };
  let outputMode = null;
  for (let index = 0; index < argv.length; index += 1) {
    const option = argv[index];
    if (option === "--compact" || option === "--verbose") {
      if (outputMode && outputMode !== option) throw new Error("Use only one of --compact or --verbose");
      outputMode = option;
      options.compact = option === "--compact";
      continue;
    }
    if (option === "--task" || option === "--resume") {
      if (!argv[index + 1] || argv[index + 1].startsWith("--")) throw new Error(`${option} requires a value`);
      options[option.slice(2)] = argv[index + 1];
      index += 1;
      continue;
    }
    throw new Error(`Unknown verification option: ${option}`);
  }
  if (!/^[A-Za-z0-9._-]{1,80}$/u.test(options.task)) {
    throw new Error("--task must contain only letters, numbers, dot, underscore, or dash");
  }
  if (process.env.CI && options.resume) throw new Error("--resume is disabled in CI");
  return options;
}

function workspaceRelative(path) {
  const relativePath = relative(workspaceRoot, path);
  return relativePath === "" ? "." : relativePath.split(sep).join("/");
}

function resolveWorkspaceFile(path) {
  const absolutePath = resolve(workspaceRoot, path);
  const relativePath = relative(workspaceRoot, absolutePath);
  if (relativePath === ".." || relativePath.startsWith(`..${sep}`)) {
    throw new Error(`Path is outside the workspace: ${path}`);
  }
  return absolutePath;
}

function gitOutput(args) {
  const result = spawnSync("git", args, { cwd: workspaceRoot, encoding: "utf8", shell: false });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(result.stderr || `git exited with ${result.status}`);
  return result.stdout.trim();
}

function workspaceSourceHash() {
  const files = gitOutput(["ls-files", "--cached", "--others", "--exclude-standard"])
    .split(/\r?\n/u)
    .filter(Boolean)
    .sort();
  const hash = createHash("sha256");
  for (const file of files) {
    const absolutePath = resolveWorkspaceFile(file);
    if (!existsSync(absolutePath)) continue;
    hash.update(file.split("\\").join("/"));
    hash.update("\0");
    hash.update(readFileSync(absolutePath));
    hash.update("\0");
  }
  return hash.digest("hex");
}

function displayCommand(step) {
  const executable = step.executable === nodeExecutable ? "node" : basename(step.executable);
  const args = step.args.map((argument) => {
    if (typeof argument !== "string") return String(argument);
    const normalized = argument.split("\\").join("/");
    const root = workspaceRoot.split("\\").join("/");
    return normalized.startsWith(`${root}/`) ? normalized.slice(root.length + 1) : argument;
  });
  return [executable, ...args].join(" ");
}

function localEnvironmentFiles() {
  return [
    resolve(workspaceRoot, ".env"),
    resolve(workspaceRoot, ".env.local"),
    resolve(backendRoot, ".env"),
    resolve(frontendRoot, ".env.local"),
  ];
}

function isSensitiveName(name) {
  return /(?:SECRET|TOKEN|PASSWORD|PASS(?:WORD)?|API[_-]?KEY|PRIVATE[_-]?KEY|CLIENT[_-]?SECRET|DATABASE_URL|COOKIE|CREDENTIAL|AUTHORIZATION)/iu.test(name);
}

function sensitiveFileValues(paths = localEnvironmentFiles()) {
  const values = [];
  for (const path of paths) {
    if (!existsSync(path)) continue;
    for (const rawLine of readFileSync(path, "utf8").split(/\r?\n/u)) {
      const line = rawLine.trim();
      if (!line || line.startsWith("#")) continue;
      const separator = line.indexOf("=");
      if (separator <= 0) continue;
      const name = line.slice(0, separator).trim();
      if (!isSensitiveName(name)) continue;
      let secret = line.slice(separator + 1).trim();
      if ((secret.startsWith('"') && secret.endsWith('"')) || (secret.startsWith("'") && secret.endsWith("'"))) {
        secret = secret.slice(1, -1);
      }
      if (secret.length >= 4) values.push([name, secret]);
    }
  }
  return values;
}

function redactSensitive(value, additionalEnvironment = {}, environmentFiles = localEnvironmentFiles()) {
  let redacted = value;
  const environment = { ...process.env, ...additionalEnvironment };
  const sensitive = [
    ...Object.entries(environment)
      .filter(([name, secret]) => isSensitiveName(name) && typeof secret === "string" && secret.length >= 4),
    ...sensitiveFileValues(environmentFiles),
  ]
    .sort((left, right) => right[1].length - left[1].length);
  for (const [name, secret] of sensitive) redacted = redacted.split(secret).join(`[REDACTED:${name}]`);
  redacted = redacted.replace(
    /-----BEGIN ([A-Z0-9 ]*PRIVATE KEY)-----[\s\S]*?-----END \1-----/gu,
    "[REDACTED:PRIVATE_KEY]",
  );
  redacted = redacted.replace(/\bBearer\s+[^\s"']+/giu, "Bearer [REDACTED:BEARER_TOKEN]");
  redacted = redacted.replace(
    /([a-z][a-z0-9+.-]*:\/\/[^:\s/@]+:)[^@\s/]+@/giu,
    "$1[REDACTED:URL_PASSWORD]@",
  );
  redacted = redacted.replace(
    /((?:"|')?(?:secret|token|password|api[_-]?key|private[_-]?key|client[_-]?secret|database_url|credential)(?:"|')?\s*[:=]\s*)(?:"[^"]*"|'[^']*'|[^\s,;]+)/giu,
    "$1[REDACTED:SENSITIVE_VALUE]",
  );
  redacted = redacted.replace(
    /(^|\n)((?:set-cookie|cookie|authorization)\s*:\s*)[^\r\n]*/giu,
    "$1$2[REDACTED:HEADER_VALUE]",
  );
  return redacted;
}

let cachedToolchainVersions = null;

function toolchainVersions() {
  if (cachedToolchainVersions) return cachedToolchainVersions;
  const uv = spawnSync("uv", ["--version"], { cwd: workspaceRoot, encoding: "utf8", shell: false });
  const configuredEnvironment = process.env.UV_PROJECT_ENVIRONMENT
    ? resolve(process.env.UV_PROJECT_ENVIRONMENT)
    : resolve(backendRoot, ".venv");
  const pythonExecutable = process.platform === "win32"
    ? resolve(configuredEnvironment, "Scripts/python.exe")
    : resolve(configuredEnvironment, "bin/python");
  const python = existsSync(pythonExecutable)
    ? spawnSync(pythonExecutable, ["--version"], { cwd: backendRoot, encoding: "utf8", shell: false })
    : null;
  cachedToolchainVersions = {
    node: process.version,
    uv: uv.status === 0 ? uv.stdout.trim() : "unavailable",
    python: python?.status === 0 ? `${python.stdout}${python.stderr}`.trim() : "unavailable",
  };
  return cachedToolchainVersions;
}

function environmentFilesHash(candidates) {
  const hash = createHash("sha256");
  let found = false;
  for (const path of candidates) {
    if (!existsSync(path)) continue;
    found = true;
    hash.update(workspaceRelative(path));
    hash.update("\0");
    hash.update(readFileSync(path));
    hash.update("\0");
  }
  return found ? hash.digest("hex") : "missing";
}

function localEnvironmentHash() {
  return environmentFilesHash(localEnvironmentFiles());
}

function stepFingerprint(step, sourceHash) {
  const environmentContract = {
    ci: Boolean(process.env.CI),
    database_url_present: Boolean(process.env.DATABASE_URL),
    secret_key_present: Boolean(process.env.SECRET_KEY),
    uv_project_environment_present: Boolean(process.env.UV_PROJECT_ENVIRONMENT),
    frontend_node_modules_override_present: Boolean(process.env.FRONTEND_NODE_MODULES),
    local_environment_hash: localEnvironmentHash(),
  };
  return createHash("sha256")
    .update(JSON.stringify({
      command: displayCommand(step),
      cwd: workspaceRelative(step.cwd),
      environment_contract: environmentContract,
      source_hash: sourceHash,
      toolchain: toolchainVersions(),
    }))
    .digest("hex");
}

function lastLines(value, count = 80) {
  return value.split(/\r?\n/u).filter((line) => line.length > 0).slice(-count).join("\n");
}

function numericMatch(text, patterns) {
  for (const pattern of patterns) {
    const matches = [...text.matchAll(pattern)];
    if (matches.length > 0) return Number(matches.at(-1)[1]);
  }
  return null;
}

function testReportPath(step) {
  if (step.key === "frontendUnit") return resolve(frontendRoot, "reports", "jest.json");
  if (step.key === "frontendComponent") return resolve(frontendRoot, "reports", "jest-component.json");
  return null;
}

function resultCounts(step, output, minimumReportMtime = 0) {
  const reportPath = testReportPath(step);
  if (reportPath) {
    if (existsSync(reportPath) && statSync(reportPath).mtimeMs >= minimumReportMtime) {
      const report = JSON.parse(readFileSync(reportPath, "utf8"));
      return {
        collected: report.numTotalTests ?? null,
        passed: report.numPassedTests ?? null,
        failed: report.numFailedTests ?? null,
        skipped: report.numPendingTests ?? null,
      };
    }
  }
  const passed = numericMatch(output, [/(\d+)\s+passed\b/gu, /Tests:\s+(\d+)\s+passed/gu]);
  const failed = numericMatch(output, [/(\d+)\s+failed\b/gu, /Tests:.*?(\d+)\s+failed/gu]);
  const skipped = numericMatch(output, [/(\d+)\s+skipped\b/gu, /(\d+)\s+pending\b/gu]);
  const collected = numericMatch(output, [/(\d+)\s+tests? collected\b/gu, /Tests:\s+(\d+)\s+total/gu]);
  return { collected: collected ?? (passed === null ? null : passed + (failed ?? 0) + (skipped ?? 0)), passed, failed, skipped };
}

function loadResumeManifest(path) {
  if (!path) return null;
  const absolutePath = resolveWorkspaceFile(path);
  if (!existsSync(absolutePath)) throw new Error(`Resume manifest is missing: ${path}`);
  const manifest = JSON.parse(readFileSync(absolutePath, "utf8"));
  if (manifest.schema_version !== 1 || !Array.isArray(manifest.steps)) {
    throw new Error("Resume manifest has an unsupported schema");
  }
  return manifest;
}

function reusableStep(step, fingerprint, resumeManifest) {
  if (!resumeManifest || !safeResumeSteps.has(step.key)) return null;
  return resumeManifest.steps.find(
    (entry) => entry.key === step.key && ["passed", "reused"].includes(entry.status) && entry.fingerprint === fingerprint,
  ) ?? null;
}

function writeManifest(path, manifest) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
}

function runStep(step, { compact, reportDirectory, sourceHash }) {
  const existingReportPath = testReportPath(step);
  const existingReportMtime = existingReportPath && existsSync(existingReportPath)
    ? statSync(existingReportPath).mtimeMs
    : null;
  const started = Date.now();
  let result;
  try {
    assertStepDependencies(step);
    result = spawnSync(step.executable, step.args, {
      cwd: step.cwd,
      env: { ...process.env, ...step.environment },
      encoding: "utf8",
      maxBuffer: 100 * 1024 * 1024,
      shell: false,
    });
  } catch (error) {
    result = { stdout: "", stderr: "", status: null, error };
  }
  const durationMs = Date.now() - started;
  const stdout = result.stdout ?? "";
  const stderr = result.stderr ?? "";
  const errorText = result.error ? `${result.error.stack ?? result.error.message}\n` : "";
  const completeOutput = redactSensitive(`${stdout}${stderr}${errorText}`, step.environment);
  const logPath = resolve(reportDirectory, `${step.key}.log`);
  mkdirSync(reportDirectory, { recursive: true });
  writeFileSync(logPath, completeOutput, "utf8");
  if (!compact && completeOutput) process.stdout.write(completeOutput);
  const statusCode = result.error ? 1 : (result.status ?? 1);
  const minimumReportMtime = existingReportMtime === null ? started - 1000 : existingReportMtime + 0.001;
  const counts = resultCounts(step, completeOutput, minimumReportMtime);
  const record = {
    key: step.key,
    label: step.label,
    command: redactSensitive(displayCommand(step), step.environment),
    cwd: workspaceRelative(step.cwd),
    status: statusCode === 0 ? "passed" : "failed",
    exit_code: statusCode,
    duration_ms: durationMs,
    ...counts,
    fingerprint: stepFingerprint(step, sourceHash),
    log: workspaceRelative(logPath),
  };
  const tests = counts.collected === null ? "n/a" : `${counts.passed ?? 0}/${counts.collected}`;
  console.log(`[verify] ${statusCode === 0 ? "PASS" : "FAIL"} step=${step.key} duration_ms=${durationMs} tests=${tests} log=${record.log}`);
  if (statusCode !== 0 && compact) {
    console.error(`[verify] command=${record.command}`);
    const tail = lastLines(completeOutput);
    if (tail) console.error(tail);
  }
  return record;
}

function main(argv = process.argv.slice(2)) {
  const requestedMode = argv[0];
  if (!requestedMode || requestedMode === "--help" || requestedMode === "help") {
    printUsage();
    return requestedMode ? 0 : 1;
  }
  if (requestedMode === "list") {
    console.log(Object.keys(modes).join("\n"));
    return 0;
  }
  if (!(requestedMode in modes)) {
    printUsage();
    console.error(`Unknown verification mode: ${requestedMode}`);
    return 2;
  }

  let options;
  try {
    options = parseOptions(argv.slice(1));
  } catch (error) {
    console.error(`VERIFY_ERROR ${error.message}`);
    return 2;
  }

  const reportDirectory = resolve(workflowReportsRoot, options.task);
  const manifestPath = resolve(reportDirectory, `${requestedMode}.json`);
  let resumeManifest;
  let sourceHash;
  try {
    resumeManifest = loadResumeManifest(options.resume);
    sourceHash = workspaceSourceHash();
  } catch (error) {
    console.error(`VERIFY_ERROR ${error.message}`);
    return 2;
  }

  const manifest = {
    schema_version: 1,
    task_id: options.task,
    mode: requestedMode,
    source_commit: gitOutput(["rev-parse", "HEAD"]),
    source_hash: sourceHash,
    started_at: new Date().toISOString(),
    finished_at: null,
    compact: options.compact,
    resume_used: Boolean(options.resume),
    steps: [],
    summary: null,
  };

  for (const step of modes[requestedMode]) {
    const fingerprint = stepFingerprint(step, sourceHash);
    const reused = reusableStep(step, fingerprint, resumeManifest);
    if (reused) {
      const record = { ...reused, status: "reused", reused_from: options.resume, fingerprint };
      manifest.steps.push(record);
      console.log(`[verify] REUSE step=${step.key} tests=${record.collected === null ? "n/a" : `${record.passed ?? 0}/${record.collected}`} from=${options.resume}`);
      writeManifest(manifestPath, manifest);
      continue;
    }

    const record = runStep(step, { compact: options.compact, reportDirectory, sourceHash });
    manifest.steps.push(record);
    writeManifest(manifestPath, manifest);
    if (record.status === "failed") {
      manifest.finished_at = new Date().toISOString();
      manifest.summary = {
        status: "failed",
        passed_steps: manifest.steps.filter((entry) => entry.status === "passed").length,
        reused_steps: manifest.steps.filter((entry) => entry.status === "reused").length,
        failed_steps: 1,
      };
      writeManifest(manifestPath, manifest);
      console.error(`VERIFY_FAILED mode=${requestedMode} task=${options.task} manifest=${workspaceRelative(manifestPath)}`);
      return record.exit_code;
    }
  }

  manifest.finished_at = new Date().toISOString();
  manifest.summary = {
    status: "passed",
    passed_steps: manifest.steps.filter((entry) => entry.status === "passed").length,
    reused_steps: manifest.steps.filter((entry) => entry.status === "reused").length,
    failed_steps: 0,
  };
  writeManifest(manifestPath, manifest);
  console.log(`VERIFY_OK mode=${requestedMode} task=${options.task} manifest=${workspaceRelative(manifestPath)} passed=${manifest.summary.passed_steps} reused=${manifest.summary.reused_steps}`);
  return 0;
}

const invokedPath = process.argv[1] ? resolve(process.argv[1]) : null;
if (invokedPath === fileURLToPath(import.meta.url)) process.exitCode = main();

export {
  displayCommand,
  environmentFilesHash,
  lastLines,
  localEnvironmentHash,
  localEnvironmentFiles,
  loadResumeManifest,
  main,
  modes,
  parseOptions,
  redactSensitive,
  resultCounts,
  reusableStep,
  runStep,
  sensitiveFileValues,
  steps,
  stepFingerprint,
  testReportPath,
  toolchainVersions,
  workspaceSourceHash,
};

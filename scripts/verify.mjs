import { existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const workspaceRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const backendRoot = resolve(workspaceRoot, "backend");
const frontendRoot = resolve(workspaceRoot, "frontend");
const nodeExecutable = process.execPath;

mkdirSync(resolve(backendRoot, "reports"), { recursive: true });
mkdirSync(resolve(frontendRoot, "reports"), { recursive: true });

const frontendBins = {
  eslint: resolve(frontendRoot, "node_modules/eslint/bin/eslint.js"),
  jest: resolve(frontendRoot, "node_modules/jest/bin/jest.js"),
  next: resolve(frontendRoot, "node_modules/next/dist/bin/next"),
  playwright: resolve(frontendRoot, "node_modules/@playwright/test/cli.js"),
};

const uvEnvironment = {
  UV_CACHE_DIR: resolve(backendRoot, ".uv-cache"),
  UV_PYTHON_INSTALL_DIR: resolve(backendRoot, ".uv-python"),
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
  backendUnit: command(
    "backend unit tests",
    "uv",
    [
      "run",
      "--frozen",
      "pytest",
      "-q",
      "-m",
      "unit",
      "--junitxml=reports/unit.xml",
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
  frontendBuild: command(
    "frontend production build",
    nodeExecutable,
    [frontendBins.next, "build", "--webpack"],
    frontendRoot,
  ),
  e2e: command(
    "frontend Playwright E2E",
    nodeExecutable,
    [frontendBins.playwright, "test"],
    frontendRoot,
  ),
};

const modes = {
  env: [steps.env],
  fast: [
    steps.env,
    steps.backendUnit,
    steps.frontendLint,
    steps.frontendUnit,
    steps.frontendBuild,
  ],
  backend: [steps.backendUnit, steps.backendIntegration],
  frontend: [steps.frontendLint, steps.frontendUnit, steps.frontendBuild],
  integration: [steps.backendIntegration],
  migration: [steps.migration],
  e2e: [steps.e2e],
  all: [
    steps.env,
    steps.backendUnit,
    steps.backendIntegration,
    steps.migration,
    steps.frontendLint,
    steps.frontendUnit,
    steps.frontendBuild,
    steps.e2e,
  ],
};

function printUsage() {
  console.log("Usage: node scripts/verify.mjs <mode>");
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

function runStep(step) {
  assertStepDependencies(step);
  console.log(`\n[verify] ${step.label}`);
  const result = spawnSync(step.executable, step.args, {
    cwd: step.cwd,
    env: { ...process.env, ...step.environment },
    stdio: "inherit",
    shell: false,
  });

  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

const requestedMode = process.argv[2];
if (!requestedMode || requestedMode === "--help" || requestedMode === "help") {
  printUsage();
  process.exit(requestedMode ? 0 : 1);
}
if (requestedMode === "list") {
  console.log(Object.keys(modes).join("\n"));
  process.exit(0);
}
if (!(requestedMode in modes)) {
  printUsage();
  console.error(`Unknown verification mode: ${requestedMode}`);
  process.exit(2);
}

for (const step of modes[requestedMode]) {
  runStep(step);
}

console.log(`\nVERIFY_OK mode=${requestedMode}`);

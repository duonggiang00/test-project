import { existsSync, readFileSync } from "node:fs";
import { dirname, relative, resolve, sep } from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const workspaceRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const baselinePath = process.env.COVERAGE_BASELINE_PATH
  ? resolve(workspaceRoot, process.env.COVERAGE_BASELINE_PATH)
  : resolve(workspaceRoot, "config/coverage-baseline.json");
const backendReportPath = resolve(workspaceRoot, "backend/reports/coverage.json");
const frontendReportPath = resolve(
  workspaceRoot,
  "frontend/reports/coverage/coverage-summary.json",
);
const frontendDetailPath = resolve(
  workspaceRoot,
  "frontend/reports/coverage/coverage-final.json",
);

function readJson(path, label) {
  if (!existsSync(path)) {
    throw new Error(`${label} is missing: ${path}`);
  }
  return JSON.parse(readFileSync(path, "utf8"));
}

function percent(covered, total) {
  return total === 0 ? 100 : (covered * 100) / total;
}

function currentCoverage() {
  const backend = readJson(backendReportPath, "Backend coverage report");
  const frontend = readJson(frontendReportPath, "Frontend coverage summary");
  return {
    backend: {
      covered: backend.totals.covered_lines,
      total: backend.totals.num_statements,
      percent: backend.totals.percent_covered,
    },
    frontend: {
      covered: frontend.total.lines.covered,
      total: frontend.total.lines.total,
      percent: frontend.total.lines.pct,
    },
  };
}

function normalizePath(path) {
  return path.split(sep).join("/").replace(/^[A-Za-z]:/u, (drive) => drive.toLowerCase());
}

function changedRanges(baseSha) {
  const output = execFileSync(
    "git",
    ["diff", "--unified=0", `${baseSha}...HEAD`, "--", "backend/app", "frontend/src"],
    { cwd: workspaceRoot, encoding: "utf8" },
  );
  const ranges = new Map();
  let file = null;
  for (const line of output.split(/\r?\n/u)) {
    if (line.startsWith("+++ b/")) {
      file = line.slice(6);
      if (!ranges.has(file)) ranges.set(file, []);
      continue;
    }
    const match = /^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@/u.exec(line);
    if (!file || !match) continue;
    const start = Number(match[1]);
    const count = match[2] === undefined ? 1 : Number(match[2]);
    if (count > 0) ranges.get(file).push([start, start + count - 1]);
  }
  return ranges;
}

function containsLine(ranges, line) {
  return ranges.some(([start, end]) => line >= start && line <= end);
}

function changedCoverage(baseSha) {
  const ranges = changedRanges(baseSha);
  const backend = readJson(backendReportPath, "Backend coverage report");
  const frontend = readJson(frontendDetailPath, "Frontend detailed coverage report");
  let covered = 0;
  let total = 0;

  for (const [reportPath, entry] of Object.entries(backend.files)) {
    const absolute = resolve(workspaceRoot, "backend", reportPath);
    const file = normalizePath(relative(workspaceRoot, absolute));
    const fileRanges = ranges.get(file);
    if (!fileRanges) continue;
    const missing = new Set(entry.missing_lines);
    for (const line of entry.executed_lines) {
      if (containsLine(fileRanges, line)) {
        total += 1;
        covered += 1;
      }
    }
    for (const line of missing) {
      if (containsLine(fileRanges, line)) total += 1;
    }
  }

  for (const [reportPath, entry] of Object.entries(frontend)) {
    const file = normalizePath(relative(workspaceRoot, reportPath));
    const fileRanges = ranges.get(file);
    if (!fileRanges) continue;
    const lineStates = new Map();
    for (const [statementId, location] of Object.entries(entry.statementMap)) {
      const line = location.start.line;
      if (!containsLine(fileRanges, line)) continue;
      const previous = lineStates.get(line) ?? true;
      lineStates.set(line, previous && entry.s[statementId] > 0);
    }
    for (const isCovered of lineStates.values()) {
      total += 1;
      if (isCovered) covered += 1;
    }
  }

  return { covered, total, percent: percent(covered, total) };
}

function assertBaseline(current, baseline) {
  for (const area of ["backend", "frontend"]) {
    const floor = baseline[area].lines_percent;
    if (current[area].percent + 0.005 < floor) {
      throw new Error(
        `${area} line coverage regressed: ${current[area].percent.toFixed(2)}% < ${floor.toFixed(2)}%`,
      );
    }
  }
}

const mode = process.argv[2];
if (!["report", "check"].includes(mode)) {
  console.error("Usage: node scripts/check-coverage.mjs <report|check>");
  process.exit(2);
}

try {
  const current = currentCoverage();
  console.log(`COVERAGE_CURRENT ${JSON.stringify(current)}`);
  if (mode === "check") {
    const baseline = readJson(baselinePath, "Coverage baseline");
    assertBaseline(current, baseline);
    const baseSha = process.env.COVERAGE_BASE_SHA?.trim();
    if (baseSha && !/^0+$/u.test(baseSha)) {
      const changed = changedCoverage(baseSha);
      console.log(`COVERAGE_CHANGED ${JSON.stringify(changed)} base=${baseSha}`);
      if (changed.total > 0 && changed.percent + 0.005 < baseline.changed_code.lines_percent) {
        throw new Error(
          `Changed-code line coverage is ${changed.percent.toFixed(2)}%; target is ${baseline.changed_code.lines_percent.toFixed(2)}%`,
        );
      }
    } else {
      console.log("COVERAGE_CHANGED_SKIPPED reason=no-base-sha");
    }
    console.log("COVERAGE_OK");
  }
} catch (error) {
  console.error(`COVERAGE_ERROR ${error.message}`);
  process.exit(1);
}

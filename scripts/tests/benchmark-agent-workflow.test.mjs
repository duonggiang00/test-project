import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

import { fileMetrics, median } from "../benchmark-agent-workflow.mjs";

const workspaceRoot = resolve(import.meta.dirname, "../..");
const config = JSON.parse(readFileSync(resolve(workspaceRoot, "config/agent-workflow-benchmarks.json"), "utf8"));

test("defines the six fixed risk-representative scenarios", () => {
  assert.equal(config.scenarios.length, 6);
  assert.equal(new Set(config.scenarios.map((scenario) => scenario.id)).size, 6);
  assert.deepEqual(config.scenarios.map((scenario) => scenario.risk), ["L0", "L1", "L1", "L2", "L2", "L3"]);
  for (const scenario of config.scenarios) {
    assert.ok(scenario.paths.length > 0);
    assert.ok(scenario.legacy_context_files.length > 0);
    assert.ok(scenario.required_gates.length > 0);
  }
});

test("measures existing baseline files and computes medians", () => {
  const metrics = fileMetrics(["AGENTS.md", "docs/agent-workflows/TASK_RISK_CLASSIFICATION.md"]);
  assert.ok(metrics.bytes > 0);
  assert.ok(metrics.lines > 0);
  assert.equal(metrics.files, 2);
  assert.equal(median([10, 30, 20]), 20);
  assert.equal(median([10, 20, 30, 40]), 25);
});

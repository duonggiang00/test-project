import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { boundedPacket, buildPacket } from "./task-context.mjs";
import { buildInventory, workspaceRoot } from "./project-inventory.mjs";

const configPath = resolve(workspaceRoot, "config/agent-workflow-benchmarks.json");

function fileMetrics(files) {
  let bytes = 0;
  let lines = 0;
  for (const file of files) {
    const contents = readFileSync(resolve(workspaceRoot, file), "utf8");
    bytes += Buffer.byteLength(contents, "utf8");
    lines += contents.split(/\r?\n/u).length;
  }
  return { bytes, lines, files: files.length };
}

function benchmark(config, inventory) {
  return config.scenarios.map((scenario) => {
    const started = performance.now();
    const packetData = buildPacket({ inventory, task: scenario.id, ...scenario });
    const packet = boundedPacket(packetData, "markdown");
    const elapsedMs = Math.round(performance.now() - started);
    const baseline = fileMetrics(scenario.legacy_context_files);
    const packetBytes = Buffer.byteLength(packet, "utf8");
    const fullSpecBytes = packetData.policy.full_spec_required
      ? fileMetrics(["docs/spec/CANONICAL_PROJECT_SPEC.md"]).bytes
      : 0;
    const effectiveContextBytes = packetBytes + fullSpecBytes;
    const reductionPercent = Number(((1 - effectiveContextBytes / baseline.bytes) * 100).toFixed(2));
    return {
      id: scenario.id,
      risk: scenario.risk,
      baseline_context_bytes: baseline.bytes,
      baseline_context_lines: baseline.lines,
      baseline_files: baseline.files,
      packet_stdout_bytes: packetBytes,
      packet_stdout_lines: packet.split(/\r?\n/u).length,
      full_spec_bytes: fullSpecBytes,
      effective_context_bytes: effectiveContextBytes,
      packet_elapsed_ms: elapsedMs,
      context_reduction_percent: reductionPercent,
      command_count: scenario.required_gates.length,
      required_gates: scenario.required_gates,
      within_packet_budget: packetBytes <= 12 * 1024 && packet.split(/\r?\n/u).length <= 180,
    };
  });
}

function median(values) {
  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[middle - 1] + sorted[middle]) / 2 : sorted[middle];
}

function main(argv = process.argv.slice(2), inventoryFactory = buildInventory) {
  try {
    if (argv.some((argument) => argument !== "--json")) throw new Error("Usage: node scripts/benchmark-agent-workflow.mjs [--json]");
    const config = JSON.parse(readFileSync(configPath, "utf8"));
    const results = benchmark(config, inventoryFactory());
    const lowRisk = results.filter((entry) => ["L0", "L1", "L2"].includes(entry.risk));
    const summary = {
      schema_version: 1,
      target_context_reduction_percent: config.target_context_reduction_percent,
      median_l0_l2_context_reduction_percent: Number(median(lowRisk.map((entry) => entry.context_reduction_percent)).toFixed(2)),
      all_l0_l2_within_packet_budget: lowRisk.every((entry) => entry.within_packet_budget),
      scenarios: results,
      actual_token_reduction_verified: false,
    };
    if (argv.includes("--json")) {
      console.log(JSON.stringify(summary, null, 2));
    } else {
      console.log(`WORKFLOW_BENCHMARK median_l0_l2_reduction=${summary.median_l0_l2_context_reduction_percent}% packet_budget=${summary.all_l0_l2_within_packet_budget ? "PASS" : "FAIL"}`);
      for (const entry of results) {
        console.log(`SCENARIO id=${entry.id} risk=${entry.risk} baseline_bytes=${entry.baseline_context_bytes} packet_bytes=${entry.packet_stdout_bytes} effective_bytes=${entry.effective_context_bytes} reduction=${entry.context_reduction_percent}% lines=${entry.packet_stdout_lines} elapsed_ms=${entry.packet_elapsed_ms} commands=${entry.command_count}`);
      }
      console.log("TOKEN_TELEMETRY actual_token_reduction=UNVERIFIED");
    }
    return summary.all_l0_l2_within_packet_budget && summary.median_l0_l2_context_reduction_percent >= config.target_context_reduction_percent ? 0 : 1;
  } catch (error) {
    console.error(`WORKFLOW_BENCHMARK_ERROR ${error.message}`);
    return 1;
  }
}

const invokedPath = process.argv[1] ? resolve(process.argv[1]) : null;
if (invokedPath === fileURLToPath(import.meta.url)) process.exitCode = main();

export { benchmark, fileMetrics, main, median };

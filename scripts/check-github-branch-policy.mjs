import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const workspaceRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const policy = JSON.parse(
  readFileSync(resolve(workspaceRoot, "config/github-branch-policy.json"), "utf8"),
);
const workflow = readFileSync(resolve(workspaceRoot, policy.workflow.path), "utf8");

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/gu, "\\$&");
}

function fail(message) {
  throw new Error(`GitHub branch policy drift: ${message}`);
}

function jobBlock(jobId) {
  const escapedId = escapeRegExp(jobId);
  const match = new RegExp(
    `^  ${escapedId}:\\r?\\n([\\s\\S]*?)(?=^  [A-Za-z0-9_-]+:\\r?$|(?![\\s\\S]))`,
    "mu",
  ).exec(workflow);
  if (!match) fail(`workflow job '${jobId}' is missing`);
  return match[1];
}

function assertJob(entry, expectedEvent) {
  const block = jobBlock(entry.job_id);
  const namePattern = new RegExp(
    `^    name:\\s*["']?${escapeRegExp(entry.job_name)}["']?\\s*$`,
    "mu",
  );
  if (!namePattern.test(block)) {
    fail(`job '${entry.job_id}' must retain name '${entry.job_name}'`);
  }

  const condition = /^    if:\s*(.+)$/mu.exec(block)?.[1] ?? "";
  if (expectedEvent === "pull_request" && condition && !condition.includes("pull_request")) {
    fail(`required PR job '${entry.job_id}' is excluded from pull requests`);
  }
  if (expectedEvent === "push" && !condition.includes("push")) {
    fail(`post-merge job '${entry.job_id}' is not restricted to push`);
  }
}

const workflowName = /^name:\s*["']?([^"'\r\n]+)["']?\s*$/mu.exec(workflow)?.[1];
if (workflowName !== policy.workflow.name) {
  fail(`workflow name must be '${policy.workflow.name}'`);
}

const mainTrigger = `branches: [${policy.default_branch}]`;
if ((workflow.match(new RegExp(escapeRegExp(mainTrigger), "gu")) ?? []).length < 2) {
  fail(`pull_request and push must both target '${policy.default_branch}'`);
}

for (const entry of policy.required_pull_request_checks) {
  assertJob(entry, "pull_request");
}
for (const entry of policy.post_merge_checks) {
  assertJob(entry, "push");
}

console.log(
  `GITHUB_BRANCH_POLICY_OK required_pr=${policy.required_pull_request_checks.length} post_merge=${policy.post_merge_checks.length}`,
);

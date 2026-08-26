import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import {
  environmentFilesHash,
  lastLines,
  modes,
  parseOptions,
  redactSensitive,
  resultCounts,
  reusableStep,
  runStep,
  sensitiveFileValues,
  steps,
  stepFingerprint,
} from "../verify.mjs";

function fakeStep(args, environment = {}) {
  return {
    key: "fixture",
    label: "fixture command",
    executable: process.execPath,
    args,
    cwd: process.cwd(),
    environment,
  };
}

test("compact is the default and verbose is explicit", () => {
  assert.deepEqual(parseOptions([]), { compact: true, task: "local", resume: null });
  assert.equal(parseOptions(["--verbose", "--task", "TOK-1"]).compact, false);
  assert.throws(() => parseOptions(["--compact", "--verbose"]), /only one/u);
});

test("canonical frontend modes run the complete Jest suite exactly once", () => {
  assert.equal(steps.frontendUnit.args.some((argument) => argument.startsWith("--testPathPatterns")), false);
  for (const mode of ["fast", "frontend", "all"]) {
    assert.equal(modes[mode].filter((step) => step.key === "frontendUnit").length, 1, mode);
    assert.equal(modes[mode].some((step) => step.key === "frontendComponent"), false, mode);
  }
});

test("test counts are extracted without retaining raw output", () => {
  assert.deepEqual(resultCounts({ key: "fixture" }, "12 passed, 2 skipped, 1 failed in 0.2s"), {
    collected: 15,
    passed: 12,
    failed: 1,
    skipped: 2,
  });
});

test("failure tails contain at most the requested number of non-empty lines", () => {
  const output = Array.from({ length: 100 }, (_, index) => `line-${index + 1}`).join("\n");
  const tail = lastLines(output, 80).split("\n");
  assert.equal(tail.length, 80);
  assert.equal(tail[0], "line-21");
  assert.equal(tail.at(-1), "line-100");
});

test("step fingerprints invalidate on source or command changes", () => {
  const step = fakeStep(["-e", "process.exit(0)"]);
  const first = stepFingerprint(step, "source-a");
  assert.equal(first, stepFingerprint(step, "source-a"));
  assert.notEqual(first, stepFingerprint(step, "source-b"));
  assert.notEqual(first, stepFingerprint(fakeStep(["-e", "console.log('changed')"]), "source-a"));
});

test("environment fingerprints change without exposing file contents", () => {
  const directory = mkdtempSync(join(tmpdir(), "verify-env-"));
  const path = join(directory, ".env");
  try {
    writeFileSync(path, "SECRET_KEY=first-secret\n", "utf8");
    const first = environmentFilesHash([path]);
    writeFileSync(path, "SECRET_KEY=second-secret\n", "utf8");
    const second = environmentFilesHash([path]);
    assert.notEqual(first, second);
    assert.doesNotMatch(first, /first-secret/u);
    assert.doesNotMatch(second, /second-secret/u);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("redacts sensitive values loaded from environment files and common credential formats", () => {
  const directory = mkdtempSync(join(tmpdir(), "verify-redaction-"));
  const environmentPath = join(directory, ".env");
  try {
    writeFileSync(environmentPath, "SERVICE_PRIVATE_KEY=private-value\nPUBLIC_URL=https://example.test\n", "utf8");
    assert.deepEqual(sensitiveFileValues([environmentPath]), [["SERVICE_PRIVATE_KEY", "private-value"]]);
    const output = redactSensitive(
      [
        "private-value",
        "request uses Bearer bearer-value",
        "Authorization: Basic untracked-authorization-value",
        "postgresql://user:database-password@localhost/app",
        "api_key=untracked-key-value",
        "Set-Cookie: session=untracked-cookie-value; HttpOnly",
        "-----BEGIN PRIVATE KEY-----\nprivate-material\n-----END PRIVATE KEY-----",
      ].join("\n"),
      {},
      [environmentPath],
    );
    assert.doesNotMatch(output, /private-value|bearer-value|untracked-authorization-value|database-password|untracked-key-value|untracked-cookie-value|private-material/u);
    assert.match(output, /REDACTED:SERVICE_PRIVATE_KEY/u);
    assert.match(output, /REDACTED:BEARER_TOKEN/u);
    assert.match(output, /REDACTED:URL_PASSWORD/u);
    assert.match(output, /REDACTED:SENSITIVE_VALUE/u);
    assert.match(output, /REDACTED:HEADER_VALUE/u);
    assert.match(output, /REDACTED:PRIVATE_KEY/u);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("resume accepts only matching passed safe steps", () => {
  const step = { ...fakeStep([]), key: "frontendLint" };
  const manifest = { steps: [{ key: "frontendLint", status: "passed", fingerprint: "same" }] };
  assert.ok(reusableStep(step, "same", manifest));
  assert.equal(reusableStep(step, "changed", manifest), null);
  assert.equal(reusableStep({ ...step, key: "backendIntegration" }, "same", manifest), null);
});

test("compact execution persists full logs and excludes environment values from evidence", () => {
  const reportDirectory = mkdtempSync(join(tmpdir(), "verify-report-"));
  try {
    const secret = "must-not-enter-manifest";
    const record = runStep(
      fakeStep(["-e", "console.log(process.env.SECRET_VALUE); console.log('3 passed, 1 skipped')"], { SECRET_VALUE: secret }),
      { compact: true, reportDirectory, sourceHash: "source" },
    );
    assert.equal(record.status, "passed");
    assert.equal(record.passed, 3);
    assert.equal(record.skipped, 1);
    assert.ok(existsSync(join(reportDirectory, "fixture.log")));
    assert.match(readFileSync(join(reportDirectory, "fixture.log"), "utf8"), /3 passed/u);
    assert.doesNotMatch(readFileSync(join(reportDirectory, "fixture.log"), "utf8"), new RegExp(secret, "u"));
    assert.match(readFileSync(join(reportDirectory, "fixture.log"), "utf8"), /REDACTED:SECRET_VALUE/u);
    assert.doesNotMatch(JSON.stringify(record), new RegExp(secret, "u"));
  } finally {
    rmSync(reportDirectory, { recursive: true, force: true });
  }
});

test("failed compact execution records the failure and complete log", () => {
  const reportDirectory = mkdtempSync(join(tmpdir(), "verify-failure-"));
  try {
    const record = runStep(
      fakeStep(["-e", "console.error('fixture failure'); process.exit(7)"]),
      { compact: true, reportDirectory, sourceHash: "source" },
    );
    assert.equal(record.status, "failed");
    assert.equal(record.exit_code, 7);
    assert.match(readFileSync(join(reportDirectory, "fixture.log"), "utf8"), /fixture failure/u);
  } finally {
    rmSync(reportDirectory, { recursive: true, force: true });
  }
});

test("missing step dependencies become persisted compact failures", () => {
  const reportDirectory = mkdtempSync(join(tmpdir(), "verify-dependency-"));
  try {
    const record = runStep(
      fakeStep([join(reportDirectory, "node_modules", "missing", "cli.js")]),
      { compact: true, reportDirectory, sourceHash: "source" },
    );
    assert.equal(record.status, "failed");
    assert.match(readFileSync(join(reportDirectory, "fixture.log"), "utf8"), /Missing .*node_modules/u);
  } finally {
    rmSync(reportDirectory, { recursive: true, force: true });
  }
});

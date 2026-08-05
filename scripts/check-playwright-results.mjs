import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const reportPath = resolve(process.cwd(), process.argv[2] ?? '');
if (!process.argv[2] || !existsSync(reportPath)) {
  console.error(`PLAYWRIGHT_POLICY_ERROR report is missing: ${reportPath}`);
  process.exit(1);
}

const report = JSON.parse(readFileSync(reportPath, 'utf8'));
const violations = [];
let testCount = 0;

function inspectSuite(suite) {
  for (const spec of suite.specs ?? []) {
    const ownerTags = (spec.tags ?? []).filter((tag) => tag.startsWith('owner-'));
    for (const test of spec.tests ?? []) {
      testCount += 1;
      const label = `${test.projectName}: ${spec.title}`;
      if (ownerTags.length !== 1) {
        violations.push(`${label} must have exactly one @owner-* tag`);
      }
      if (test.status !== 'expected') {
        violations.push(`${label} finished with status=${test.status}`);
      }
      if ((test.results ?? []).some((result) => result.retry > 0)) {
        violations.push(`${label} required a diagnostic retry`);
      }
    }
  }
  for (const child of suite.suites ?? []) inspectSuite(child);
}

for (const suite of report.suites ?? []) inspectSuite(suite);
if (testCount === 0) violations.push('report contains no tests');

if (violations.length > 0) {
  for (const violation of violations) console.error(`PLAYWRIGHT_POLICY_VIOLATION ${violation}`);
  process.exit(1);
}

console.log(`PLAYWRIGHT_POLICY_OK tests=${testCount}`);

import { existsSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const workspaceRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const baselinePath = resolve(workspaceRoot, 'config/architecture-guard-baseline.json');

function posix(path) {
  return path.split(sep).join('/');
}

function filesUnder(root, extensions) {
  if (!existsSync(root)) return [];
  const result = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const path = resolve(root, entry.name);
    if (entry.isDirectory()) result.push(...filesUnder(path, extensions));
    else if (entry.isFile() && extensions.some((extension) => entry.name.endsWith(extension))) {
      result.push(path);
    }
  }
  return result.sort();
}

function normalizedSnippet(line) {
  return line.trim().replace(/\s+/gu, ' ');
}

function violation(rule, path, line, source) {
  return {
    rule,
    file: posix(relative(workspaceRoot, path)),
    line,
    snippet: normalizedSnippet(source),
  };
}

function scanBackend(path) {
  const source = readFileSync(path, 'utf8');
  const lines = source.split(/\r?\n/u);
  const results = [];
  const relativePath = posix(relative(workspaceRoot, path));
  const isBadFixture = relativePath.includes('/fixtures/architecture/bad/');
  const loopIndents = [];

  lines.forEach((line, index) => {
    const lineNumber = index + 1;
    const indent = line.match(/^\s*/u)[0].replace(/\t/gu, '    ').length;
    const trimmed = line.trim();
    while (loopIndents.length && trimmed && indent <= loopIndents.at(-1)) loopIndents.pop();
    if (/^(?:async\s+)?(?:for|while)\b.*:/u.test(trimmed)) loopIndents.push(indent);

    if (line.includes('.query(')) results.push(violation('backend.session-query', path, lineNumber, line));
    if (/datetime\.utcnow\s*\(/u.test(line)) results.push(violation('backend.datetime-utcnow', path, lineNumber, line));
    if (/^\s*except\s*:/u.test(line)) results.push(violation('backend.bare-except', path, lineNumber, line));
    if (/message\s*=\s*(?:str\s*\(|f["'][^"']*\{\s*str\s*\()/u.test(line)) {
      results.push(violation('backend.raw-error-message', path, lineNumber, line));
    }
    if (
      loopIndents.length &&
      /(?:\.query\s*\(|\.execute\s*\(|\.scalar\s*\()/u.test(line)
    ) {
      results.push(violation('backend.query-in-loop', path, lineNumber, line));
    }
    if (/^\s*@(?:router|app)\.(?:get|post|put|patch|delete|head|options)\(\s*["'][^"']+\/["']/u.test(line)) {
      results.push(violation('contract.backend-trailing-slash', path, lineNumber, line));
    }

    const isImport = /^\s*(?:from|import)\s+app\./u.test(line);
    if (isImport && (relativePath.includes('/api/endpoints/') || isBadFixture) && /app\.(?:models|db)\b/u.test(line)) {
      results.push(violation('backend.router-layer-import', path, lineNumber, line));
    }
    if (isImport && relativePath.includes('/models/') && /app\.(?:api|services)\b/u.test(line)) {
      results.push(violation('backend.model-layer-import', path, lineNumber, line));
    }
    if (isImport && relativePath.includes('/services/') && /app\.api\b/u.test(line)) {
      results.push(violation('backend.service-layer-import', path, lineNumber, line));
    }

    const importsProviderSdk = /^\s*(?:from\s+openai(?:\.[\w.]+)?\s+import\b|import\s+openai\b)/u.test(line);
    const isOpenRouterAdapter = relativePath === 'backend/app/ai/openrouter_adapter.py';
    if (importsProviderSdk && !isOpenRouterAdapter) {
      results.push(violation('backend.provider-sdk-import', path, lineNumber, line));
    }
  });

  for (const match of source.matchAll(/\.add_task\(/gu)) {
    let depth = 1;
    let cursor = match.index + match[0].length;
    while (cursor < source.length && depth > 0) {
      if (source[cursor] === '(') depth += 1;
      else if (source[cursor] === ')') depth -= 1;
      cursor += 1;
    }
    const call = source.slice(match.index, cursor);
    if (!/,\s*(?:db|session)\b/u.test(call)) continue;
    const lineNumber = source.slice(0, match.index).split(/\r?\n/u).length;
    results.push(violation('backend.request-session-background-task', path, lineNumber, call));
  }
  return results;
}

const forbiddenColors = '(?:red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|zinc|neutral|stone)';

function scanFrontend(path) {
  const source = readFileSync(path, 'utf8');
  const lines = source.split(/\r?\n/u);
  const results = [];
  const relativePath = posix(relative(workspaceRoot, path));
  const isBadFixture = relativePath.includes('/fixtures/architecture/bad/');
  const isBff = relativePath.includes('/src/app/api/');
  const isUiFile = relativePath.includes('/src/app/') || relativePath.includes('/src/components/') || isBadFixture;

  lines.forEach((line, index) => {
    const lineNumber = index + 1;
    if (!isBff && /(?:fetch|axios\.(?:get|post|put|patch|delete))\s*\([^\n]*(?:https?:\/\/|NEXT_PUBLIC_API_URL|BACKEND_API_URL)/u.test(line)) {
      results.push(violation('frontend.bff-bypass', path, lineNumber, line));
    }
    if (isUiFile && /(?:fetch\s*\(|axios\.)/u.test(line)) {
      results.push(violation('frontend.component-data-fetch', path, lineNumber, line));
    }
    if (/localStorage\.(?:getItem|setItem|removeItem)\s*\(\s*["'](?:access_)?token["']/iu.test(line)) {
      results.push(violation('frontend.token-local-storage', path, lineNumber, line));
    }
    if ((relativePath.endsWith('/src/lib/store.ts') || isBadFixture) && /(?:^|[{,])\s*(?:exams|topics|students|questions|materials|submissions)\s*:/u.test(line)) {
      results.push(violation('frontend.server-state-zustand', path, lineNumber, line));
    }
    if (/(?:window\.)?location\.reload\s*\(/u.test(line)) {
      results.push(violation('frontend.reload-mutation', path, lineNumber, line));
    }
    if (
      /["'`]\/(?!\/)[^"'`?]*\/["'`]/u.test(line) &&
      (relativePath.includes('/services/') || relativePath.includes('/hooks/') || isBadFixture)
    ) {
      results.push(violation('contract.frontend-trailing-slash', path, lineNumber, line));
    }
    if (/from\s+["']next\/font\/google["']|@import\s+url\s*\(/u.test(line)) {
      results.push(violation('design.remote-font', path, lineNumber, line));
    }
    if (new RegExp(`\\b(?:bg|text|border|ring|from|via|to)-${forbiddenColors}(?:-|\\b)`, 'u').test(line)) {
      results.push(violation('design.non-monochrome-token', path, lineNumber, line));
    }
    for (const color of line.matchAll(/#[0-9a-fA-F]{3,8}\b/gu)) {
      const normalized = color[0].toLowerCase();
      if (!['#000', '#000000', '#fff', '#ffffff'].includes(normalized)) {
        results.push(violation('design.non-monochrome-literal', path, lineNumber, line));
        break;
      }
    }
  });
  return results;
}

function scan(paths = null) {
  const backendFiles = paths?.filter((path) => path.endsWith('.py')) ?? filesUnder(resolve(workspaceRoot, 'backend/app'), ['.py']);
  const frontendFiles = paths?.filter((path) => /\.[jt]sx?$/u.test(path)) ?? filesUnder(resolve(workspaceRoot, 'frontend/src'), ['.ts', '.tsx', '.js', '.jsx'])
    .filter((path) => !/\.(?:test|spec)\.[jt]sx?$/u.test(path));
  return [
    ...backendFiles.flatMap(scanBackend),
    ...frontendFiles.flatMap(scanFrontend),
  ].sort((left, right) => `${left.rule}:${left.file}:${left.line}`.localeCompare(`${right.rule}:${right.file}:${right.line}`));
}

function fingerprint(item) {
  return `${item.rule}\0${item.file}\0${item.snippet}`;
}

function newViolations(current, baseline) {
  const allowance = new Map();
  for (const item of baseline.violations) {
    const key = fingerprint(item);
    allowance.set(key, (allowance.get(key) ?? 0) + 1);
  }
  return current.filter((item) => {
    const key = fingerprint(item);
    const count = allowance.get(key) ?? 0;
    if (count === 0) return true;
    allowance.set(key, count - 1);
    return false;
  });
}

function summary(violations) {
  const counts = {};
  for (const item of violations) counts[item.rule] = (counts[item.rule] ?? 0) + 1;
  return counts;
}

const mode = process.argv[2];
try {
  if (mode === 'generate') {
    const violations = scan();
    const payload = {
      schema_version: 1,
      policy: 'Existing fingerprints may be removed; every new fingerprint fails.',
      summary: summary(violations),
      violations,
    };
    writeFileSync(baselinePath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
    console.log(`ARCHITECTURE_BASELINE_GENERATED violations=${violations.length}`);
  } else if (mode === 'check') {
    const baseline = JSON.parse(readFileSync(baselinePath, 'utf8'));
    const current = scan();
    const additions = newViolations(current, baseline);
    if (additions.length > 0) {
      for (const item of additions) {
        console.error(`ARCHITECTURE_VIOLATION ${item.rule} ${item.file}:${item.line} ${item.snippet}`);
      }
      process.exit(1);
    }
    console.log(`ARCHITECTURE_OK current=${current.length} baseline=${baseline.violations.length}`);
  } else if (mode === 'fixtures') {
    const fixtureRoot = resolve(workspaceRoot, 'scripts/fixtures/architecture');
    const good = scan(filesUnder(resolve(fixtureRoot, 'good'), ['.py', '.ts', '.tsx']));
    const bad = scan(filesUnder(resolve(fixtureRoot, 'bad'), ['.py', '.ts', '.tsx']));
    if (good.length !== 0) throw new Error(`Compliant fixtures produced ${good.length} violations`);
    const required = new Set([
      'backend.session-query',
      'backend.datetime-utcnow',
      'backend.bare-except',
      'backend.raw-error-message',
      'backend.query-in-loop',
      'backend.request-session-background-task',
      'backend.router-layer-import',
      'backend.provider-sdk-import',
      'contract.backend-trailing-slash',
      'frontend.bff-bypass',
      'frontend.component-data-fetch',
      'frontend.token-local-storage',
      'frontend.server-state-zustand',
      'frontend.reload-mutation',
      'contract.frontend-trailing-slash',
      'design.remote-font',
      'design.non-monochrome-token',
      'design.non-monochrome-literal',
    ]);
    const observed = new Set(bad.map((item) => item.rule));
    const missing = [...required].filter((rule) => !observed.has(rule));
    if (missing.length) throw new Error(`Bad fixtures missed rules: ${missing.join(', ')}`);
    console.log(`ARCHITECTURE_FIXTURES_OK good=0 bad=${bad.length} rules=${observed.size}`);
  } else {
    console.error('Usage: node scripts/architecture-guard.mjs <generate|check|fixtures>');
    process.exit(2);
  }
} catch (error) {
  console.error(`ARCHITECTURE_ERROR ${error.message}`);
  process.exit(1);
}

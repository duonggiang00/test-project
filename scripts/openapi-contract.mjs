import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const workspaceRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const backendRoot = resolve(workspaceRoot, 'backend');
const outputPath = resolve(workspaceRoot, 'docs/generated/openapi.json');
const introspectionDatabaseUrl = 'postgresql://inventory:inventory@127.0.0.1:5432/inventory';

function liveContract() {
  const result = spawnSync(
    'uv',
    ['run', '--frozen', 'python', '-m', 'scripts.emit_openapi'],
    {
      cwd: backendRoot,
      env: {
        ...process.env,
        DATABASE_URL: process.env.DATABASE_URL ?? introspectionDatabaseUrl,
        UV_CACHE_DIR: resolve(backendRoot, '.uv-cache'),
        UV_PYTHON_INSTALL_DIR: resolve(backendRoot, '.uv-python'),
      },
      encoding: 'utf8',
      maxBuffer: 20 * 1024 * 1024,
    },
  );
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(result.stderr || `OpenAPI emitter exited ${result.status}`);
  return JSON.parse(result.stdout);
}

const mode = process.argv[2];
try {
  const current = liveContract();
  const serialized = `${JSON.stringify(current, null, 2)}\n`;
  if (mode === 'generate') {
    writeFileSync(outputPath, serialized, 'utf8');
    console.log(`OPENAPI_GENERATED paths=${Object.keys(current.paths).length}`);
  } else if (mode === 'check') {
    if (!existsSync(outputPath)) throw new Error('Generated OpenAPI contract is missing');
    if (readFileSync(outputPath, 'utf8') !== serialized) {
      throw new Error('Generated OpenAPI contract is stale; review the API diff before regeneration');
    }
    console.log(`OPENAPI_OK paths=${Object.keys(current.paths).length}`);
  } else {
    console.error('Usage: node scripts/openapi-contract.mjs <generate|check>');
    process.exit(2);
  }
} catch (error) {
  console.error(`OPENAPI_ERROR ${error.message}`);
  process.exit(1);
}

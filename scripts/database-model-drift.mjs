import { createHash } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const workspaceRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const backendRoot = resolve(workspaceRoot, 'backend');
const baselinePath = resolve(workspaceRoot, 'config/database-model-signature.json');
const introspectionDatabaseUrl = 'postgresql://inventory:inventory@127.0.0.1:5432/inventory';

function runtimeInventory() {
  const result = spawnSync(
    'uv',
    ['run', '--frozen', 'python', '-m', 'scripts.emit_inventory'],
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
  if (result.status !== 0) throw new Error(result.stderr || `Inventory emitter exited ${result.status}`);
  return JSON.parse(result.stdout);
}

function signature() {
  const inventory = runtimeInventory();
  const serializedModels = JSON.stringify(inventory.models);
  return {
    schema_version: 1,
    sqlalchemy_model_sha256: createHash('sha256').update(serializedModels).digest('hex'),
    sqlalchemy_model_count: inventory.models.length,
    alembic_heads: inventory.alembic_heads,
  };
}

function sameHeads(left, right) {
  return JSON.stringify(left) === JSON.stringify(right);
}

const mode = process.argv[2];
try {
  const current = signature();
  if (mode === 'generate') {
    if (existsSync(baselinePath)) {
      const stored = JSON.parse(readFileSync(baselinePath, 'utf8'));
      if (
        stored.sqlalchemy_model_sha256 !== current.sqlalchemy_model_sha256 &&
        sameHeads(stored.alembic_heads, current.alembic_heads)
      ) {
        throw new Error('SQLAlchemy models changed while Alembic heads did not; add the reviewed migration first');
      }
    }
    writeFileSync(baselinePath, `${JSON.stringify(current, null, 2)}\n`, 'utf8');
    console.log(`DATABASE_SIGNATURE_GENERATED models=${current.sqlalchemy_model_count} heads=${current.alembic_heads.join(',')}`);
  } else if (mode === 'check') {
    if (!existsSync(baselinePath)) throw new Error('Database model signature is missing');
    const stored = JSON.parse(readFileSync(baselinePath, 'utf8'));
    if (stored.sqlalchemy_model_sha256 !== current.sqlalchemy_model_sha256) {
      if (sameHeads(stored.alembic_heads, current.alembic_heads)) {
        throw new Error('SQLAlchemy models changed without a new Alembic head');
      }
      throw new Error('Database model signature is stale after a migration change; review and regenerate it');
    }
    if (!sameHeads(stored.alembic_heads, current.alembic_heads)) {
      throw new Error('Alembic heads changed; review and regenerate the database model signature');
    }
    console.log(`DATABASE_DRIFT_OK models=${current.sqlalchemy_model_count} heads=${current.alembic_heads.join(',')}`);
  } else {
    console.error('Usage: node scripts/database-model-drift.mjs <generate|check>');
    process.exit(2);
  }
} catch (error) {
  console.error(`DATABASE_DRIFT_ERROR ${error.message}`);
  process.exit(1);
}

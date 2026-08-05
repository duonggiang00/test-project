import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const workspaceRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const examplePath = resolve(workspaceRoot, ".env.example");
const content = readFileSync(examplePath, "utf8");

const values = new Map();
const errors = [];

for (const [index, rawLine] of content.split(/\r?\n/u).entries()) {
  const line = rawLine.trim();
  if (!line || line.startsWith("#")) {
    continue;
  }

  const separator = line.indexOf("=");
  if (separator < 1) {
    errors.push(`line ${index + 1} is not KEY=value`);
    continue;
  }

  const key = line.slice(0, separator).trim();
  const value = line.slice(separator + 1).trim();
  if (!/^[A-Z][A-Z0-9_]*$/u.test(key)) {
    errors.push(`line ${index + 1} has an invalid key: ${key}`);
  }
  if (values.has(key)) {
    errors.push(`duplicate key: ${key}`);
  }
  values.set(key, value);
}

const requiredKeys = [
  "PROJECT_NAME",
  "ENV",
  "DATABASE_URL",
  "SECRET_KEY",
  "BACKEND_CORS_ORIGINS",
  "OPENROUTER_API_KEY",
  "BACKEND_API_URL",
];
const forbiddenKeys = [
  "NEXT_PUBLIC_API_URL",
  "NEXT_PUBLIC_API_PROTOCOL",
  "NEXT_PUBLIC_API_HOSTNAME",
  "NEXT_PUBLIC_API_PORT",
];

for (const key of requiredKeys) {
  if (!values.has(key)) {
    errors.push(`missing canonical key: ${key}`);
  }
}
for (const key of forbiddenKeys) {
  if (values.has(key)) {
    errors.push(`deprecated public backend setting is not allowed: ${key}`);
  }
}

const secretKey = values.get("SECRET_KEY") || "";
if (!secretKey.includes("replace-with-")) {
  errors.push("SECRET_KEY must remain an explicit non-secret placeholder");
}
const databaseUrl = values.get("DATABASE_URL") || "";
if (!databaseUrl.startsWith("postgresql://")) {
  errors.push("DATABASE_URL must demonstrate the canonical PostgreSQL scheme");
}
if (!databaseUrl.includes("replace-with-")) {
  errors.push("DATABASE_URL must contain a placeholder password");
}
const backendUrl = values.get("BACKEND_API_URL") || "";
try {
  const parsed = new URL(backendUrl);
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    errors.push("BACKEND_API_URL must use http or https");
  }
} catch {
  errors.push("BACKEND_API_URL must be a valid URL");
}

if (errors.length > 0) {
  console.error("ENV_EXAMPLE_INVALID");
  for (const error of errors) {
    console.error(`- ${error}`);
  }
  process.exit(1);
}

console.log(`ENV_EXAMPLE_OK keys=${values.size}`);

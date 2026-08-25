import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const workspaceRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const examplePath = resolve(workspaceRoot, ".env.example");
const outputPath = resolve(workspaceRoot, ".env");
const postgresDatabaseUrl = "postgresql://postgres:postgres@127.0.0.1:5432/ai_exam";

function buildEnvironment(profile) {
  const example = readFileSync(examplePath, "utf8");
  if (profile === "fast") {
    return example;
  }
  if (profile === "postgres") {
    const replaced = example.replace(
      /^DATABASE_URL=.*$/mu,
      `DATABASE_URL=${postgresDatabaseUrl}`,
    );
    if (replaced === example) {
      throw new Error(".env.example is missing DATABASE_URL");
    }
    return replaced;
  }
  throw new Error(`Unknown CI environment profile: ${profile}`);
}

const mode = process.argv[2];
try {
  if (mode === "check") {
    const fast = buildEnvironment("fast");
    const postgres = buildEnvironment("postgres");
    if (!fast.includes("replace-with-local-password")) {
      throw new Error("Fast profile must retain the example database placeholder");
    }
    if (!postgres.includes(`DATABASE_URL=${postgresDatabaseUrl}`)) {
      throw new Error("PostgreSQL profile must target the GitHub service database");
    }
    console.log("CI_ENV_PROFILES_OK profiles=2");
  } else {
    const content = buildEnvironment(mode);
    writeFileSync(outputPath, content, "utf8");
    console.log(`CI_ENV_CREATED profile=${mode}`);
  }
} catch (error) {
  console.error(`CI_ENV_ERROR ${error.message}`);
  process.exit(1);
}

import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import {
  boundedPacket,
  buildPacket,
  inferDomains,
  inventoryState,
  normalizedWorkspacePath,
  parseArgs,
  powershellQuote,
} from "../task-context.mjs";

function inventory() {
  return {
    provenance: { source_tree_sha256: "live-source-hash" },
    backend: {
      models: [{ class: "RefreshSession", file: "backend/app/models/refresh_session.py" }],
      schemas: [{ class: "LoginRequest", file: "backend/app/schemas/auth.py" }],
      routes: [{ path: "/auth/login", file: "backend/app/api/endpoints/auth.py" }],
    },
    frontend: {
      pages: [{ route: "/login", file: "frontend/src/app/(auth)/login/page.tsx" }],
      layouts: [],
      hooks: [],
      services: [],
      bff_routes: [{ file: "frontend/src/app/api/auth/login/route.ts", methods: ["POST"] }],
    },
    tests: {
      backend: [{ path: "backend/tests/test_auth.py", tests: ["test_login"] }],
      frontend: [{ path: "frontend/src/app/api/auth/login/route.test.ts", tier: "unit", test_count: 2 }],
    },
  };
}

test("parses multiple quoted paths and terms", () => {
  assert.deepEqual(
    parseArgs([
      "--task",
      "AUTH-1",
      "--risk",
      "L3",
      "--paths",
      "frontend/src/app/(auth)/login/page.tsx",
      "backend/app/api/endpoints/auth.py",
      "--terms",
      "refresh session",
      "login",
      "--format",
      "json",
    ]),
    {
      task: "AUTH-1",
      risk: "L3",
      paths: ["frontend/src/app/(auth)/login/page.tsx", "backend/app/api/endpoints/auth.py"],
      terms: ["refresh session", "login"],
      format: "json",
    },
  );
});

test("maps frontend auth work to scoped rules and security contracts", () => {
  const packet = buildPacket({
    inventory: inventory(),
    task: "AUTH-1",
    risk: "L3",
    paths: ["frontend\\src\\app\\(auth)\\login\\page.tsx"],
    terms: ["login", "session"],
  });

  assert.deepEqual(packet.domains, ["auth", "frontend"]);
  assert.ok(packet.policy.rules.includes("frontend/AGENTS.md"));
  assert.ok(packet.policy.adrs.includes("docs/adr/0003-bff-cookie-authentication.md"));
  assert.ok(packet.policy.canonical.some((entry) => entry.file.endsWith("PERMISSION_AND_OWNERSHIP_MATRIX.md")));
  assert.equal(packet.policy.full_spec_required, true);
  assert.equal(packet.inventory.source, "live");
  assert.equal(packet.inventory.stored_inventory_is_canonical, false);
});

test("rejects paths outside the workspace", () => {
  assert.throws(() => normalizedWorkspacePath("..\\outside.txt"), /outside the workspace/u);
});

test("quotes follow-up values without creating an executable injection", () => {
  assert.equal(powershellQuote("path with 'quote'"), "'path with ''quote'''" );
});

test("labels missing, stale, and current stored inventories", () => {
  const directory = mkdtempSync(join(tmpdir(), "task-context-"));
  const storedPath = join(directory, "inventory.json");
  const current = inventory();

  assert.equal(inventoryState(current, storedPath), "missing");
  writeFileSync(storedPath, JSON.stringify({ ...current, extra: true }), "utf8");
  assert.equal(inventoryState(current, storedPath), "stale");
  writeFileSync(storedPath, JSON.stringify(current), "utf8");
  assert.equal(inventoryState(current, storedPath), "current");
  assert.equal(JSON.parse(readFileSync(storedPath, "utf8")).provenance.source_tree_sha256, "live-source-hash");
});

test("keeps markdown and JSON packets within hard budgets deterministically", () => {
  const packet = buildPacket({
    inventory: inventory(),
    task: "AUTH-1",
    risk: "L2",
    paths: ["backend/app/api/endpoints/auth.py", "frontend/src/app/api/auth/login/route.ts"],
    terms: ["auth", "login", "session"],
  });

  const first = boundedPacket(packet, "markdown", 12 * 1024, 180);
  const second = boundedPacket(packet, "markdown", 12 * 1024, 180);
  const json = boundedPacket(packet, "json", 12 * 1024, 180);

  assert.equal(first, second);
  assert.ok(Buffer.byteLength(first, "utf8") <= 12 * 1024);
  assert.ok(first.split(/\r?\n/u).length <= 180);
  assert.ok(Buffer.byteLength(json, "utf8") <= 12 * 1024);
  assert.doesNotThrow(() => JSON.parse(json));
});

test("detects workflow, database, and AI domains", () => {
  assert.deepEqual(inferDomains(["scripts/verify.mjs"], []), ["workflow"]);
  assert.deepEqual(inferDomains(["backend/app/models/material.py"], ["rag retrieval"]), ["ai", "backend", "database"]);
});

test("requires the full specification for cross-domain L2 work", () => {
  const packet = buildPacket({
    inventory: inventory(),
    task: "CROSS-LAYER",
    risk: "L2",
    paths: ["backend/app/api/endpoints/auth.py", "frontend/src/app/api/auth/login/route.ts"],
    terms: ["login"],
  });
  assert.equal(packet.policy.full_spec_required, true);
});

test("reports category truncation instead of silently dropping matches", () => {
  const crowdedInventory = inventory();
  crowdedInventory.backend.models = Array.from({ length: 10 }, (_, index) => ({
    class: `LoginModel${index}`,
    module: `app.models.login_${index}`,
    table: `login_${index}`,
  }));
  const packet = buildPacket({
    inventory: crowdedInventory,
    task: "TRUNCATION",
    risk: "L1",
    paths: ["backend/app/models/login.py"],
    terms: ["login"],
  });

  assert.equal(packet.inventory_matches.models.length, 8);
  assert.equal(packet.truncated, true);
  assert.ok(packet.truncation.categories.includes("inventory_matches.models"));
  assert.match(boundedPacket(packet, "markdown"), /truncated in: inventory_matches\.models/u);
  assert.ok(packet.follow_up);
});

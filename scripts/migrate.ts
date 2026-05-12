/**
 * Migration Runner — runs all pending .sql migration files.
 *
 * Migrations are tracked in a `_migrations` table on first run.
 * Only files not yet applied will be executed, in sort order.
 *
 * Usage:
 *   export TURSO_DATABASE_URL="..."
 *   export TURSO_AUTH_TOKEN="..."
 *   npm run migrate
 */

import { readFileSync, readdirSync } from "fs";
import { join } from "path";
import { createClient } from "@libsql/client";

const url = process.env.TURSO_DATABASE_URL;
const authToken = process.env.TURSO_AUTH_TOKEN;

if (!url || !authToken) {
  console.error("❌ Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN");
  process.exit(1);
}

const db = createClient({ url, authToken });

async function ensureTrackingTable() {
  await db.execute(`
    CREATE TABLE IF NOT EXISTS _migrations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      filename TEXT NOT NULL UNIQUE,
      applied_at TEXT DEFAULT (datetime('now'))
    )
  `);
}

async function getApplied(): Promise<Set<string>> {
  const result = await db.execute("SELECT filename FROM _migrations");
  return new Set(result.rows.map((r) => String(r.filename)));
}

function extractUpSql(filePath: string): string[] {
  const sql = readFileSync(filePath, "utf-8");

  // Extract SQL between +goose Up and +goose Down markers
  const upMatch = sql.match(/-- \+goose Up\n([\s\S]+?)-- \+goose Down/);
  if (!upMatch) {
    console.error(`  ⚠️  Could not parse +goose Up marker in ${filePath}, skipping`);
    return [];
  }

  let upSql = upMatch[1];

  // Remove comment lines
  upSql = upSql
    .split("\n")
    .filter((line) => !line.trim().startsWith("--"))
    .join("\n");

  // Split by semicolons
  return upSql
    .split(";")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

async function main() {
  await ensureTrackingTable();
  const applied = await getApplied();

  const migrationsDir = join(__dirname, "..", "migrations");
  const files = readdirSync(migrationsDir)
    .filter((f) => f.endsWith(".sql"))
    .sort(); // runs in alphabetical order: 001_xxx, 002_xxx, ...

  let pendingCount = 0;

  for (const file of files) {
    if (applied.has(file)) {
      console.log(`   ⏭️  ${file} (already applied)`);
      continue;
    }

    const filePath = join(migrationsDir, file);
    const statements = extractUpSql(filePath);

    if (statements.length === 0) {
      console.log(`   ⏭️  ${file} (no statements to execute)`);
      continue;
    }

    console.log(`📦 Running migration: ${file}`);
    console.log(`   ${statements.length} statement(s) to execute`);

    for (const stmt of statements) {
      const stmtClean = stmt + ";";
      console.log(`   ▶ ${stmtClean.slice(0, 80)}`);
      try {
        await db.execute(stmtClean);
        console.log(`   ✓`);
      } catch (err: any) {
        // If it's a "table/index already exists" error, that's OK on retry
        const msg = String(err?.message || err || "");
        if (msg.includes("already exists")) {
          console.log(`   ✓ (already exists)`);
        } else {
          throw err;
        }
      }
    }

    // Record as applied
    await db.execute({
      sql: "INSERT INTO _migrations (filename) VALUES (?)",
      args: [file],
    });

    pendingCount++;
  }

  if (pendingCount === 0) {
    console.log("✅ All migrations already applied.");
  } else {
    console.log(`\n✅ ${pendingCount} migration(s) applied successfully.`);
  }

  await db.close();
}

main().catch((err) => {
  console.error("❌ Migration failed:", err);
  process.exit(1);
});

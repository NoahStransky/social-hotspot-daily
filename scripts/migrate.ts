import { readFileSync } from "fs";
import { join } from "path";
import { createClient } from "@libsql/client";

const url = process.env.TURSO_DATABASE_URL;
const authToken = process.env.TURSO_AUTH_TOKEN;

if (!url || !authToken) {
  console.error("❌ Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN");
  process.exit(1);
}

const db = createClient({ url, authToken });

async function main() {
  const sql = readFileSync(join(__dirname, "..", "migrations", "001_create_tables.sql"), "utf-8");

  // Extract SQL between +goose Up and +goose Down markers
  const upMatch = sql.match(/-- \+goose Up\n([\s\S]+?)-- \+goose Down/);
  if (!upMatch) {
    console.error("❌ Could not parse migration SQL (missing +goose Up marker)");
    process.exit(1);
  }

  let upSql = upMatch[1];

  // Remove SQL comment lines (-- ...)
  upSql = upSql
    .split("\n")
    .filter((line) => !line.trim().startsWith("--"))
    .join("\n");

  // Split by semicolons
  const statements = upSql
    .split(";")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);

  console.log(`📦 Running migration: 001_create_tables.sql`);
  console.log(`   ${statements.length} statement(s) to execute`);

  for (const stmt of statements) {
    const stmtClean = stmt + ";";
    console.log(`   ▶ ${stmtClean.slice(0, 80)}`);
    await db.execute(stmtClean);
    console.log(`   ✓`);
  }

  console.log("✅ Migration complete!");
}

main().catch((err) => {
  console.error("❌ Migration failed:", err);
  process.exit(1);
});

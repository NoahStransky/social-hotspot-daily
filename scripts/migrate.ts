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

  // Extract just the SQL statements between +goose Up/Down markers
  const upMatch = sql.match(/-- \+goose Up\n([\s\S]*?)-- \+goose Down/);
  if (!upMatch) {
    console.error("❌ Could not parse migration SQL (missing +goose Up marker)");
    process.exit(1);
  }

  const statements = upMatch[1]
    .split(";")
    .map((s) => s.trim())
    .filter((s) => s.length > 0 && !s.startsWith("--"));

  console.log(`📦 Running migration: 001_create_tables.sql`);
  console.log(`   ${statements.length} statement(s) to execute`);

  for (const sql of statements) {
    await db.execute(sql);
    console.log(`   ✓ ${sql.slice(0, 60)}...`);
  }

  console.log("✅ Migration complete!");
}

main().catch((err) => {
  console.error("❌ Migration failed:", err);
  process.exit(1);
});

import { createClient } from "@libsql/client";

async function main() {
  const url = process.env.TURSO_DATABASE_URL || "";
  const token = process.env.TURSO_AUTH_TOKEN || "";
  
  console.log("TURSO_DATABASE_URL:", url);
  console.log("TURSO_AUTH_TOKEN set:", token ? "YES (" + token.length + " chars)" : "NO");
  console.log("---");
  
  const db = createClient({ url, authToken: token });
  const r = await db.execute("SELECT * FROM subscribers ORDER BY created_at DESC");
  console.log("Found rows:", r.rows.length);
  if (r.rows.length > 0) {
    console.log(JSON.stringify(r.rows, null, 2));
  }
  await db.close();
}
main().catch((e) => {
  console.error("Error:", e.message);
  process.exit(1);
});

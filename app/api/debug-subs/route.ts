export async function GET() {
  const { createClient } = await import("@libsql/client");
  
  const db = createClient({
    url: process.env.TURSO_DATABASE_URL!,
    authToken: process.env.TURSO_AUTH_TOKEN!,
  });
  
  const r = await db.execute("SELECT * FROM subscribers ORDER BY created_at DESC");
  const rows = r.rows;
  
  await db.close();

  // Return as plain text (no edge case issues)
  return new Response(
    "DB URL: " + process.env.TURSO_DATABASE_URL!.slice(0, 60) + "...\n\n" +
    "Subscribers (" + rows.length + "):\n" +
    JSON.stringify(rows, null, 2),
    { status: 200, headers: { "Content-Type": "text/plain" } }
  );
}

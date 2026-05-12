export async function GET() {
  return new Response(
    "TURSO_DATABASE_URL: " + (process.env.TURSO_DATABASE_URL || "NOT SET") + "\n" +
    "TURSO_AUTH_TOKEN: " + (process.env.TURSO_AUTH_TOKEN ? "SET (" + process.env.TURSO_AUTH_TOKEN.length + " chars)" : "NOT SET"),
    { status: 200, headers: { "Content-Type": "text/plain" } }
  );
}

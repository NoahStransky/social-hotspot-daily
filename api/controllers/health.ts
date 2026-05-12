import { jsonResponse, handleCors, corsHeaders } from "../lib/http.js";
import { getDb } from "../lib/db.js";

export async function GET(request: Request): Promise<Response> {
  const cors = handleCors(request);
  if (cors) return cors;

  const headers = corsHeaders(request.headers.get("origin"));

  try {
    const db = getDb();
    await db.execute({ sql: "SELECT 1 as ok", args: [] });
    return jsonResponse(
      { ok: true, service: "social-hotspot-subscribe" },
      200,
      headers
    );
  } catch (err) {
    console.error(`[HealthController] Error: ${err}`);
    return jsonResponse(
      { ok: false, error: "Database unavailable" },
      503,
      headers
    );
  }
}

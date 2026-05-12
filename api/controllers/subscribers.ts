import { jsonResponse, handleCors, corsHeaders } from "../lib/http.js";
import { getDb } from "../lib/db.js";

export async function GET(request: Request): Promise<Response> {
  const cors = handleCors(request);
  if (cors) return cors;

  const headers = corsHeaders(request.headers.get("origin"));

  try {
    // Authenticate
    const authHeader = request.headers.get("Authorization") || "";
    const apiKey = process.env.SUBSCRIBERS_API_KEY;

    if (!apiKey || authHeader !== `Bearer ${apiKey}`) {
      return jsonResponse({ error: "Unauthorized" }, 401, headers);
    }

    const db = getDb();
    const result = await db.execute({
      sql: "SELECT email, verified, unsubscribed, created_at, verified_at FROM subscribers WHERE verified = 1 AND unsubscribed = 0 ORDER BY created_at DESC",
      args: [],
    });

    return jsonResponse(
      { subscribers: result.rows, count: result.rows.length },
      200,
      headers
    );
  } catch (err) {
    console.error(`[SubscribersController] Error: ${err}`);
    return jsonResponse({ error: "Internal server error." }, 500, headers);
  }
}

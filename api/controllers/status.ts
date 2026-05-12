import { jsonResponse, handleCors, corsHeaders } from "../lib/http.js";
import { getDb } from "../lib/db.js";
import { isValidEmail } from "../lib/token.js";

export async function GET(request: Request): Promise<Response> {
  const cors = handleCors(request);
  if (cors) return cors;

  const headers = corsHeaders(request.headers.get("origin"));

  try {
    const url = new URL(request.url);
    const email = (url.searchParams.get("email") || "").trim().toLowerCase();

    if (!email || !isValidEmail(email)) {
      return jsonResponse({ error: "Invalid email address." }, 400, headers);
    }

    const db = getDb();
    const result = await db.execute({
      sql: "SELECT email, verified, unsubscribed, created_at, verified_at FROM subscribers WHERE email = ?",
      args: [email],
    });

    if (result.rows.length === 0) {
      return jsonResponse({ status: "not_found", email }, 404, headers);
    }

    const subscriber = result.rows[0] as unknown as {
      email: string;
      verified: number;
      unsubscribed: number;
      created_at: string;
      verified_at: string | null;
    };

    let status: string;
    if (subscriber.unsubscribed) status = "unsubscribed";
    else if (subscriber.verified) status = "verified";
    else status = "pending_verification";

    return jsonResponse(
      {
        status,
        email: subscriber.email,
        created_at: subscriber.created_at,
        verified_at: subscriber.verified_at,
      },
      200,
      headers
    );
  } catch (err) {
    console.error(`[StatusController] Error: ${err}`);
    return jsonResponse({ error: "Internal server error." }, 500, headers);
  }
}

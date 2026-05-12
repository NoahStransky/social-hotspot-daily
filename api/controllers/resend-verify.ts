import { jsonResponse, handleCors, corsHeaders } from "../lib/http.js";
import { getDb } from "../lib/db.js";
import { isValidEmail } from "../lib/token.js";
import { sendVerificationEmail } from "../services/email.js";

export async function POST(request: Request): Promise<Response> {
  const cors = handleCors(request);
  if (cors) return cors;

  const headers = corsHeaders(request.headers.get("origin"));

  try {
    const body = (await request.json()) as { email?: string };
    const email = (body.email || "").trim().toLowerCase();

    if (!email || !isValidEmail(email)) {
      return jsonResponse({ error: "Invalid email address." }, 400, headers);
    }

    const db = getDb();
    const result = await db.execute({
      sql: "SELECT id, verified, verification_token FROM subscribers WHERE email = ?",
      args: [email],
    });

    if (result.rows.length === 0) {
      return jsonResponse(
        { error: "Email not found. Please subscribe first." },
        404,
        headers
      );
    }

    const subscriber = result.rows[0] as unknown as {
      id: number;
      verified: number;
      verification_token: string;
    };

    if (subscriber.verified) {
      return jsonResponse({ error: "Email is already verified." }, 409, headers);
    }

    // Generate new token if missing
    let token = subscriber.verification_token;
    if (!token) {
      token = crypto.randomUUID().replace(/-/g, "");
      await db.execute({
        sql: "UPDATE subscribers SET verification_token = ? WHERE email = ?",
        args: [token, email],
      });
    }

    const sent = await sendVerificationEmail(email, token);
    if (!sent) {
      return jsonResponse(
        { error: "Failed to send verification email. Please try again." },
        500,
        headers
      );
    }

    return jsonResponse(
      { message: "Verification email resent! Please check your inbox.", email },
      200,
      headers
    );
  } catch (err) {
    console.error(`[ResendVerifyController] Error: ${err}`);
    return jsonResponse({ error: "Internal server error." }, 500, headers);
  }
}

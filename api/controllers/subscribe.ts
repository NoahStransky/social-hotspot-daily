import { jsonResponse, handleCors, corsHeaders } from "../lib/http.js";
import { verifyTurnstileToken } from "../lib/turnstile.js";
import { subscribe } from "../services/subscriber.js";

export async function POST(request: Request): Promise<Response> {
  const cors = handleCors(request);
  if (cors) return cors;

  const headers = corsHeaders(request.headers.get("origin"));

  try {
    const body = (await request.json()) as {
      email?: string;
      turnstile_token?: string;
    };
    const email = (body.email || "").trim().toLowerCase();
    const turnstileToken = body.turnstile_token || "";

    // Turnstile verification
    if (!turnstileToken || !(await verifyTurnstileToken(turnstileToken))) {
      return jsonResponse(
        { error: "Bot verification failed. Please try again." },
        403,
        headers
      );
    }

    const result = await subscribe(email);
    return jsonResponse(
      result.success
        ? { message: result.message, email: result.email }
        : { error: result.message },
      result.status,
      headers
    );
  } catch (err) {
    console.error(`[SubscribeController] Error: ${err}`);
    return jsonResponse({ error: "Internal server error." }, 500, headers);
  }
}

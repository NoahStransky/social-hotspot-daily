import { handleCors, jsonResponse, corsHeaders } from "./lib/http.js";
import { verifyTurnstileToken } from "./lib/turnstile.js";
import { subscribe } from "./services/subscriber.js";
import { getDb } from "./lib/db.js";
import { isValidEmail } from "./lib/token.js";
import { sendVerificationEmail } from "./services/email.js";

const BLOG_BASE_URL = process.env.BLOG_BASE_URL || "https://hotspot.edgesoft.org";

function redirect(location: string) {
  return new Response(null, { status: 302, headers: { Location: location } });
}

// ─── Handlers ────────────────────────────────────────────────────────────────

async function handleSubscribe(request: Request): Promise<Response> {
  const headers = corsHeaders(request.headers.get("origin"));

  try {
    const body = (await request.json()) as {
      email?: string;
      turnstile_token?: string;
    };
    const email = (body.email || "").trim().toLowerCase();
    const turnstileToken = body.turnstile_token || "";

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
    console.error(`[Subscribe] Error: ${err}`);
    return jsonResponse({ error: "Internal server error." }, 500, headers);
  }
}

async function handleVerify(request: Request): Promise<Response> {
  try {
    const url = new URL(request.url);
    const token = url.searchParams.get("token");
    if (!token) return redirect(`${BLOG_BASE_URL}/verify.html?status=invalid`);

    const db = getDb();
    const result = await db.execute({
      sql: "SELECT id, verified FROM subscribers WHERE verification_token = ?",
      args: [token],
    });

    if (result.rows.length === 0)
      return redirect(`${BLOG_BASE_URL}/verify.html?status=invalid`);

    const row = result.rows[0] as unknown as { id: number; verified: number };
    if (row.verified)
      return redirect(`${BLOG_BASE_URL}/verify.html?status=already`);

    await db.execute({
      sql: "UPDATE subscribers SET verified = 1, verified_at = datetime('now') WHERE id = ? AND verified = 0",
      args: [row.id],
    });

    return redirect(`${BLOG_BASE_URL}/verify.html?status=success`);
  } catch (err) {
    console.error(`[Verify] Error: ${err}`);
    return redirect(`${BLOG_BASE_URL}/verify.html?status=error`);
  }
}

async function handleUnsubscribe(request: Request): Promise<Response> {
  try {
    const url = new URL(request.url);
    const email = (url.searchParams.get("email") || "").trim().toLowerCase();
    if (!email || !isValidEmail(email))
      return redirect(`${BLOG_BASE_URL}/unsubscribe.html?status=invalid`);

    const db = getDb();
    const result = await db.execute({
      sql: "UPDATE subscribers SET unsubscribed = 1 WHERE email = ?",
      args: [email],
    });

    const affected = result.rowsAffected || 0;
    if (affected === 0)
      return redirect(`${BLOG_BASE_URL}/unsubscribe.html?status=notfound`);

    return redirect(`${BLOG_BASE_URL}/unsubscribe.html?status=success`);
  } catch (err) {
    console.error(`[Unsubscribe] Error: ${err}`);
    return redirect(`${BLOG_BASE_URL}/unsubscribe.html?status=error`);
  }
}

async function handleResendVerify(request: Request): Promise<Response> {
  const headers = corsHeaders(request.headers.get("origin"));

  try {
    const body = (await request.json()) as { email?: string };
    const email = (body.email || "").trim().toLowerCase();

    if (!email || !isValidEmail(email))
      return jsonResponse({ error: "Invalid email address." }, 400, headers);

    const db = getDb();
    const result = await db.execute({
      sql: "SELECT id, verified, verification_token FROM subscribers WHERE email = ?",
      args: [email],
    });

    if (result.rows.length === 0)
      return jsonResponse(
        { error: "Email not found. Please subscribe first." },
        404,
        headers
      );

    const row = result.rows[0] as unknown as {
      id: number;
      verified: number;
      verification_token: string;
    };

    if (row.verified)
      return jsonResponse({ error: "Email is already verified." }, 409, headers);

    let token = row.verification_token;
    if (!token) {
      token = crypto.randomUUID().replace(/-/g, "");
      await db.execute({
        sql: "UPDATE subscribers SET verification_token = ? WHERE email = ?",
        args: [token, email],
      });
    }

    const sent = await sendVerificationEmail(email, token);
    if (!sent)
      return jsonResponse(
        { error: "Failed to send verification email. Please try again." },
        500,
        headers
      );

    return jsonResponse(
      { message: "Verification email resent! Please check your inbox.", email },
      200,
      headers
    );
  } catch (err) {
    console.error(`[ResendVerify] Error: ${err}`);
    return jsonResponse({ error: "Internal server error." }, 500, headers);
  }
}

async function handleStatus(request: Request): Promise<Response> {
  const headers = corsHeaders(request.headers.get("origin"));

  try {
    const url = new URL(request.url);
    const email = (url.searchParams.get("email") || "").trim().toLowerCase();
    if (!email || !isValidEmail(email))
      return jsonResponse({ error: "Invalid email address." }, 400, headers);

    const db = getDb();
    const result = await db.execute({
      sql: "SELECT email, verified, unsubscribed, created_at, verified_at FROM subscribers WHERE email = ?",
      args: [email],
    });

    if (result.rows.length === 0)
      return jsonResponse({ status: "not_found", email }, 404, headers);

    const row = result.rows[0] as unknown as {
      email: string;
      verified: number;
      unsubscribed: number;
      created_at: string;
      verified_at: string | null;
    };

    let status: string;
    if (row.unsubscribed) status = "unsubscribed";
    else if (row.verified) status = "verified";
    else status = "pending_verification";

    return jsonResponse(
      { status, email: row.email, created_at: row.created_at, verified_at: row.verified_at },
      200,
      headers
    );
  } catch (err) {
    console.error(`[Status] Error: ${err}`);
    return jsonResponse({ error: "Internal server error." }, 500, headers);
  }
}

async function handleHealth(_request: Request): Promise<Response> {
  const headers = corsHeaders(null);
  try {
    const db = getDb();
    await db.execute({ sql: "SELECT 1 as ok", args: [] });
    return jsonResponse({ ok: true, service: "social-hotspot-subscribe" }, 200, headers);
  } catch (err) {
    console.error(`[Health] Error: ${err}`);
    return jsonResponse({ ok: false, error: "Database unavailable" }, 503, headers);
  }
}

async function handleSubscribers(request: Request): Promise<Response> {
  const headers = corsHeaders(request.headers.get("origin"));

  try {
    const authHeader = request.headers.get("Authorization") || "";
    const apiKey = process.env.SUBSCRIBERS_API_KEY;
    if (!apiKey || authHeader !== `Bearer ${apiKey}`)
      return jsonResponse({ error: "Unauthorized" }, 401, headers);

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
    console.error(`[Subscribers] Error: ${err}`);
    return jsonResponse({ error: "Internal server error." }, 500, headers);
  }
}

// ─── Router ──────────────────────────────────────────────────────────────────

export async function GET(request: Request): Promise<Response> {
  const cors = handleCors(request);
  if (cors) return cors;

  const url = new URL(request.url);
  const path = url.pathname;

  switch (path) {
    case "/api/verify":
      return handleVerify(request);
    case "/api/unsubscribe":
      return handleUnsubscribe(request);
    case "/api/status":
      return handleStatus(request);
    case "/api/health":
      return handleHealth(request);
    case "/api/subscribers":
      return handleSubscribers(request);
    default:
      return jsonResponse({ error: "Not found", path }, 404, corsHeaders(request.headers.get("origin")));
  }
}

export async function POST(request: Request): Promise<Response> {
  const cors = handleCors(request);
  if (cors) return cors;

  const url = new URL(request.url);
  const path = url.pathname;

  switch (path) {
    case "/api/subscribe":
      return handleSubscribe(request);
    case "/api/resend-verify":
      return handleResendVerify(request);
    default:
      return jsonResponse({ error: "Not found", path }, 404, corsHeaders(request.headers.get("origin")));
  }
}

// CRITICAL: Vercel still reads `export default` for the single-function approach
// but we only need exported handlers named GET/POST when using a single route pattern.

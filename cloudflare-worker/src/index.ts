/**
 * Social Hotspot Subscribe — Cloudflare Worker
 *
 * Endpoints:
 *   POST /subscribe         — Add new subscriber, send verification email
 *   GET  /verify?token=xxx  — Verify email via token, redirect to verify.html
 *   GET  /unsubscribe?email=xxx — Unsubscribe email, redirect to unsubscribe.html
 *   POST /resend-verify     — Resend verification email
 *   GET  /status?email=xxx  — Check subscription status
 *   GET  /health            — Health check
 */

export interface Env {
  DB: D1Database;
  RESEND_API_KEY: string;
  BLOG_BASE_URL: string;
  FROM_EMAIL: string;
}

// ─── CORS ────────────────────────────────────────────────────────────────────

const ALLOWED_ORIGINS = [
  'https://noahstransky.github.io',
  'http://localhost:8787',
  'http://localhost:8788',
  'http://127.0.0.1:8787',
  'http://127.0.0.1:8788',
];

function corsHeaders(request: Request): HeadersInit {
  const origin = request.headers.get('Origin') || '';
  const allowed = ALLOWED_ORIGINS.includes(origin) ? origin : 'https://noahstransky.github.io';
  return {
    'Access-Control-Allow-Origin': allowed,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400',
  };
}

function jsonResponse(data: unknown, status = 200, cors: HeadersInit = {}): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...cors,
    },
  });
}

function redirectResponse(url: string, cors: HeadersInit = {}): Response {
  return new Response(null, {
    status: 302,
    headers: {
      Location: url,
      ...cors,
    },
  });
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function generateToken(): string {
  // Cloudflare Workers runtime supports crypto.randomUUID
  return crypto.randomUUID().replace(/-/g, '') + crypto.randomUUID().replace(/-/g, '');
}

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim().toLowerCase());
}

// ─── Resend Email ────────────────────────────────────────────────────────────

async function sendVerificationEmail(
  resendApiKey: string,
  fromEmail: string,
  toEmail: string,
  token: string,
  blogBaseUrl: string,
): Promise<boolean> {
  // The verification link now points to the Worker endpoint which will redirect
  const verifyUrl = `${blogBaseUrl}/verify.html?token=${token}`;

  const htmlContent = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Verify Your Subscription</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #e2e2f0; padding: 40px 20px; }
    .container { max-width: 600px; margin: 0 auto; background: #12121a; border: 1px solid #252535; border-radius: 12px; padding: 40px; }
    h1 { color: #6366f1; font-size: 24px; margin-bottom: 20px; }
    .button { display: inline-block; background: #6366f1; color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; margin: 20px 0; }
    .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #252535; color: #8b8ba7; font-size: 12px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>📧 Verify Your Subscription</h1>
    <p>Thank you for subscribing to <strong>Tech Hotspot Daily</strong>!</p>
    <p>Click the button below to verify your email and start receiving daily tech news.</p>
    <a href="${verifyUrl}" class="button">Verify Email</a>
    <p style="font-size: 13px; color: #8b8ba7;">Or copy this link: ${verifyUrl}</p>
    <div class="footer">
      <p>If you didn't request this, you can safely ignore this email.</p>
      <p>Tech Hotspot Daily — Curated for IT professionals</p>
    </div>
  </div>
</body>
</html>`;

  try {
    const resp = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${resendApiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: `Tech Hotspot Daily <${fromEmail}>`,
        to: [toEmail],
        subject: 'Verify your subscription to Tech Hotspot Daily',
        html: htmlContent,
      }),
    });

    if (!resp.ok) {
      const body = await resp.text();
      console.error(`[Worker] Resend API error (${resp.status}): ${body}`);
      return false;
    }

    console.log(`[Worker] Verification email sent to ${toEmail}`);
    return true;
  } catch (err) {
    console.error(`[Worker] Failed to send verification email: ${err}`);
    return false;
  }
}

// ─── Route Handlers ──────────────────────────────────────────────────────────

async function handleSubscribe(request: Request, env: Env, cors: HeadersInit): Promise<Response> {
  try {
    const body = (await request.json()) as { email?: string };
    const email = (body.email || '').trim().toLowerCase();

    if (!email || !isValidEmail(email)) {
      return jsonResponse({ error: 'Invalid email address.' }, 400, cors);
    }

    // Check if subscriber exists
    const existing = await env.DB.prepare(
      'SELECT id, verified, unsubscribed, verification_token FROM subscribers WHERE email = ?',
    ).bind(email).first<{ id: number; verified: number; unsubscribed: number; verification_token: string }>();

    if (existing) {
      if (existing.verified && !existing.unsubscribed) {
        return jsonResponse({ error: 'This email is already subscribed and verified.' }, 409, cors);
      }

      if (existing.verified && existing.unsubscribed) {
        // Re-subscribe: re-activate
        const newToken = generateToken();
        await env.DB.prepare(
          'UPDATE subscribers SET unsubscribed = 0, verified = 0, verification_token = ?, verified_at = NULL WHERE email = ?',
        ).bind(newToken, email).run();

        const sent = await sendVerificationEmail(env.RESEND_API_KEY, env.FROM_EMAIL, email, newToken, env.BLOG_BASE_URL);
        if (!sent) {
          return jsonResponse({ error: 'Failed to send verification email. Please try again.' }, 500, cors);
        }

        return jsonResponse({
          message: 'Re-subscription initiated! Please check your email to verify.',
          email,
        }, 200, cors);
      }

      // Not verified yet — resend with existing or new token
      let token = existing.verification_token;
      if (!token) {
        token = generateToken();
        await env.DB.prepare(
          'UPDATE subscribers SET verification_token = ? WHERE email = ?',
        ).bind(token, email).run();
      }

      const sent = await sendVerificationEmail(env.RESEND_API_KEY, env.FROM_EMAIL, email, token, env.BLOG_BASE_URL);
      if (!sent) {
        return jsonResponse({ error: 'Failed to send verification email. Please try again.' }, 500, cors);
      }

      return jsonResponse({
        message: 'Verification email resent! Please check your inbox.',
        email,
      }, 200, cors);
    }

    // New subscriber
    const token = generateToken();
    await env.DB.prepare(
      'INSERT INTO subscribers (email, verification_token) VALUES (?, ?)',
    ).bind(email, token).run();

    const sent = await sendVerificationEmail(env.RESEND_API_KEY, env.FROM_EMAIL, email, token, env.BLOG_BASE_URL);
    if (!sent) {
      return jsonResponse({ error: 'Failed to send verification email. Please try again.' }, 500, cors);
    }

    return jsonResponse({
      message: 'Subscription successful! Please check your email to verify.',
      email,
    }, 201, cors);

  } catch (err) {
    console.error(`[Worker] Subscribe error: ${err}`);
    return jsonResponse({ error: 'Internal server error.' }, 500, cors);
  }
}

async function handleVerify(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const token = url.searchParams.get('token');

  if (!token) {
    return redirectResponse(`${env.BLOG_BASE_URL}/verify.html?status=invalid`);
  }

  try {
    // Find subscriber by token
    const subscriber = await env.DB.prepare(
      'SELECT id, verified, email FROM subscribers WHERE verification_token = ?',
    ).bind(token).first<{ id: number; verified: number; email: string }>();

    if (!subscriber) {
      return redirectResponse(`${env.BLOG_BASE_URL}/verify.html?status=invalid`);
    }

    if (subscriber.verified) {
      // Already verified
      return redirectResponse(`${env.BLOG_BASE_URL}/verify.html?status=already`);
    }

    // Mark as verified
    await env.DB.prepare(
      "UPDATE subscribers SET verified = 1, verified_at = datetime('now') WHERE id = ? AND verified = 0",
    ).bind(subscriber.id).run();

    return redirectResponse(`${env.BLOG_BASE_URL}/verify.html?status=success`);

  } catch (err) {
    console.error(`[Worker] Verify error: ${err}`);
    return redirectResponse(`${env.BLOG_BASE_URL}/verify.html?status=error`);
  }
}

async function handleUnsubscribe(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const email = (url.searchParams.get('email') || '').trim().toLowerCase();

  if (!email || !isValidEmail(email)) {
    return redirectResponse(`${env.BLOG_BASE_URL}/unsubscribe.html?status=invalid`);
  }

  try {
    const result = await env.DB.prepare(
      'UPDATE subscribers SET unsubscribed = 1 WHERE email = ?',
    ).bind(email).run();

    if (result.meta.changes === 0) {
      return redirectResponse(`${env.BLOG_BASE_URL}/unsubscribe.html?status=notfound`);
    }

    return redirectResponse(`${env.BLOG_BASE_URL}/unsubscribe.html?status=success`);

  } catch (err) {
    console.error(`[Worker] Unsubscribe error: ${err}`);
    return redirectResponse(`${env.BLOG_BASE_URL}/unsubscribe.html?status=error`);
  }
}

async function handleResendVerify(request: Request, env: Env, cors: HeadersInit): Promise<Response> {
  try {
    const body = (await request.json()) as { email?: string };
    const email = (body.email || '').trim().toLowerCase();

    if (!email || !isValidEmail(email)) {
      return jsonResponse({ error: 'Invalid email address.' }, 400, cors);
    }

    const subscriber = await env.DB.prepare(
      'SELECT id, verified, verification_token FROM subscribers WHERE email = ?',
    ).bind(email).first<{ id: number; verified: number; verification_token: string }>();

    if (!subscriber) {
      return jsonResponse({ error: 'Email not found. Please subscribe first.' }, 404, cors);
    }

    if (subscriber.verified) {
      return jsonResponse({ error: 'Email is already verified.' }, 409, cors);
    }

    // Generate new token if missing
    let token = subscriber.verification_token;
    if (!token) {
      token = generateToken();
      await env.DB.prepare(
        'UPDATE subscribers SET verification_token = ? WHERE email = ?',
      ).bind(token, email).run();
    }

    const sent = await sendVerificationEmail(env.RESEND_API_KEY, env.FROM_EMAIL, email, token, env.BLOG_BASE_URL);
    if (!sent) {
      return jsonResponse({ error: 'Failed to send verification email. Please try again.' }, 500, cors);
    }

    return jsonResponse({
      message: 'Verification email resent! Please check your inbox.',
      email,
    }, 200, cors);

  } catch (err) {
    console.error(`[Worker] Resend verify error: ${err}`);
    return jsonResponse({ error: 'Internal server error.' }, 500, cors);
  }
}

async function handleStatus(request: Request, env: Env, cors: HeadersInit): Promise<Response> {
  const url = new URL(request.url);
  const email = (url.searchParams.get('email') || '').trim().toLowerCase();

  if (!email || !isValidEmail(email)) {
    return jsonResponse({ error: 'Invalid email address.' }, 400, cors);
  }

  try {
    const subscriber = await env.DB.prepare(
      'SELECT email, verified, unsubscribed, created_at, verified_at FROM subscribers WHERE email = ?',
    ).bind(email).first<{ email: string; verified: number; unsubscribed: number; created_at: string; verified_at: string | null }>();

    if (!subscriber) {
      return jsonResponse({ status: 'not_found', email }, 404, cors);
    }

    let status: string;
    if (subscriber.unsubscribed) {
      status = 'unsubscribed';
    } else if (subscriber.verified) {
      status = 'verified';
    } else {
      status = 'pending_verification';
    }

    return jsonResponse({
      status,
      email: subscriber.email,
      created_at: subscriber.created_at,
      verified_at: subscriber.verified_at,
    }, 200, cors);

  } catch (err) {
    console.error(`[Worker] Status error: ${err}`);
    return jsonResponse({ error: 'Internal server error.' }, 500, cors);
  }
}

async function handleHealth(_request: Request, env: Env, cors: HeadersInit): Promise<Response> {
  try {
    await env.DB.prepare('SELECT 1 as ok').first();
    return jsonResponse({ ok: true, service: 'social-hotspot-subscribe' }, 200, cors);
  } catch (err) {
    return jsonResponse({ ok: false, error: 'Database unavailable' }, 503, cors);
  }
}

// ─── Router ──────────────────────────────────────────────────────────────────

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const method = request.method;
    const cors = corsHeaders(request);

    // Handle CORS preflight
    if (method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: cors,
      });
    }

    // Route matching
    const path = url.pathname;

    try {
      if (method === 'POST' && path === '/subscribe') {
        return await handleSubscribe(request, env, cors);
      }

      if (method === 'GET' && path === '/verify') {
        return await handleVerify(request, env);
      }

      if (method === 'GET' && path === '/unsubscribe') {
        return await handleUnsubscribe(request, env);
      }

      if (method === 'POST' && path === '/resend-verify') {
        return await handleResendVerify(request, env, cors);
      }

      if (method === 'GET' && path === '/status') {
        return await handleStatus(request, env, cors);
      }

      if (method === 'GET' && path === '/health') {
        return await handleHealth(request, env, cors);
      }

      // 404 for everything else
      return jsonResponse({ error: 'Not found', path, method }, 404, cors);

    } catch (err) {
      console.error(`[Worker] Unhandled error: ${err}`);
      return jsonResponse({ error: 'Internal server error.' }, 500, cors);
    }
  },
};

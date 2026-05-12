export async function verifyTurnstileToken(
  token: string
): Promise<boolean> {
  const secret = process.env.TURNSTILE_SECRET_KEY;
  if (!secret) {
    console.error("[Turnstile] TURNSTILE_SECRET_KEY not configured");
    return false;
  }

  try {
    const resp = await fetch(
      "https://challenges.cloudflare.com/turnstile/v0/siteverify",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ secret, response: token }),
      }
    );
    const data = (await resp.json()) as { success?: boolean };
    return data.success === true;
  } catch (err) {
    console.error(`[Turnstile] Verification error: ${err}`);
    return false;
  }
}

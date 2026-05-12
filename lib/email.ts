export async function sendVerificationEmail(
  toEmail: string,
  token: string
): Promise<boolean> {
  const resendApiKey = process.env.RESEND_API_KEY;
  const fromEmail = process.env.FROM_EMAIL || "onboarding@resend.dev";
  const blogBaseUrl = process.env.BLOG_BASE_URL || "https://hotspot.edgesoft.org";

  if (!resendApiKey) {
    console.error("[Email] RESEND_API_KEY not configured");
    return false;
  }

  const verifyUrl = `${blogBaseUrl}/api/verify?token=${token}`;

  console.log(`[Email] Sending to ${toEmail}, from=${fromEmail}, baseUrl=${blogBaseUrl}`);
  console.log(`[Email] Verify URL: ${verifyUrl}`);

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
    const resp = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${resendApiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: `Tech Hotspot Daily <${fromEmail}>`,
        to: [toEmail],
        subject: "Verify your subscription to Tech Hotspot Daily",
        html: htmlContent,
      }),
    });

    if (!resp.ok) {
      const body = await resp.text();
      console.error(`[Email] Resend API error (${resp.status}): ${body}`);
      return false;
    }

    console.log(`[Email] Verification email sent to ${toEmail}`);
    return true;
  } catch (err) {
    console.error(`[Email] Failed to send verification email: ${err}`);
    return false;
  }
}

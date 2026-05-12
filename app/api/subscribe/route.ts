import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { isValidEmail, generateToken } from "../_lib";
import { verifyTurnstileToken } from "@/lib/turnstile";
import { sendVerificationEmail } from "@/lib/email";

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as { email?: string; turnstile_token?: string };
    const email = (body.email || "").trim().toLowerCase();
    const turnstileToken = body.turnstile_token || "";

    if (!email || !isValidEmail(email)) {
      return NextResponse.json({ error: "Invalid email address." }, { status: 400 });
    }

    if (!turnstileToken || !(await verifyTurnstileToken(turnstileToken))) {
      return NextResponse.json({ error: "Bot verification failed. Please try again." }, { status: 403 });
    }

    const db = getDb();
    const existing = await db.execute({
      sql: "SELECT id, verified, unsubscribed, verification_token FROM subscribers WHERE email = ?",
      args: [email],
    });

    if (existing.rows.length > 0) {
      const row = existing.rows[0] as unknown as {
        id: number; verified: number; unsubscribed: number; verification_token: string;
      };

      if (row.verified && !row.unsubscribed) {
        return NextResponse.json({ error: "This email is already subscribed and verified." }, { status: 409 });
      }

      if (row.verified && row.unsubscribed) {
        const newToken = generateToken();
        await db.execute({
          sql: "UPDATE subscribers SET unsubscribed = 0, verified = 0, verification_token = ?, verified_at = NULL WHERE email = ?",
          args: [newToken, email],
        });
        const sent = await sendVerificationEmail(email, newToken);
        if (!sent) return NextResponse.json({ error: "Failed to send verification email." }, { status: 500 });
        return NextResponse.json({ message: "Re-subscription initiated! Please check your email to verify.", email });
      }

      let token = row.verification_token;
      if (!token) {
        token = generateToken();
        await db.execute({
          sql: "UPDATE subscribers SET verification_token = ? WHERE email = ?",
          args: [token, email],
        });
      }
      const sent = await sendVerificationEmail(email, token);
      if (!sent) return NextResponse.json({ error: "Failed to send verification email." }, { status: 500 });
      return NextResponse.json({ message: "Verification email resent! Please check your inbox.", email });
    }

    const token = generateToken();
    console.log(`[Subscribe] Email: ${email}, Token: ${token}`);
    console.log(`[Subscribe] RESEND_API_KEY: ${process.env.RESEND_API_KEY ? 'YES (len=' + process.env.RESEND_API_KEY.length + ')' : 'NO'}`);
    console.log(`[Subscribe] FROM_EMAIL: ${process.env.FROM_EMAIL || 'NOT SET'}`);
    console.log(`[Subscribe] BLOG_BASE_URL: ${process.env.BLOG_BASE_URL || 'NOT SET'}`);

    const sent = await sendVerificationEmail(email, token);
    console.log(`[Subscribe] sendVerificationEmail result: ${sent}`);

    if (!sent) {
      return NextResponse.json({ error: "Failed to send verification email." }, { status: 500 });
    }
    await db.execute({
      sql: "INSERT INTO subscribers (email, verification_token) VALUES (?, ?)",
      args: [email, token],
    });
    console.log(`[Subscribe] DB insert done for ${email}`);
    return NextResponse.json({ message: "Subscription successful! Please check your email to verify.", email }, { status: 201 });
  } catch (err) {
    console.error(`[Subscribe] Error: ${err}`);
    return NextResponse.json({ error: "Internal server error." }, { status: 500 });
  }
}

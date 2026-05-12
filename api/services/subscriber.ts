import { getDb, SubscriberRow } from "../lib/db.js";
import { isValidEmail } from "../lib/token.js";
import { sendVerificationEmail } from "./email.js";

export interface SubscribeResult {
  success: boolean;
  message: string;
  email: string;
  status: number; // HTTP status code
  error?: string;
}

export async function subscribe(
  email: string
): Promise<SubscribeResult> {
  if (!email || !isValidEmail(email)) {
    return { success: false, message: "Invalid email address.", email, status: 400 };
  }

  const db = getDb();

  // Check if subscriber exists
  const existing = await db.execute({
    sql: "SELECT id, verified, unsubscribed, verification_token FROM subscribers WHERE email = ?",
    args: [email],
  });

  if (existing.rows.length > 0) {
    const row = existing.rows[0] as unknown as SubscriberRow;

    if (row.verified && !row.unsubscribed) {
      return {
        success: false,
        message: "This email is already subscribed and verified.",
        email,
        status: 409,
      };
    }

    if (row.verified && row.unsubscribed) {
      // Re-subscribe
      const newToken = crypto.randomUUID().replace(/-/g, "");
      await db.execute({
        sql: "UPDATE subscribers SET unsubscribed = 0, verified = 0, verification_token = ?, verified_at = NULL WHERE email = ?",
        args: [newToken, email],
      });

      const sent = await sendVerificationEmail(email, newToken);
      if (!sent) {
        return {
          success: false,
          message: "Failed to send verification email. Please try again.",
          email,
          status: 500,
        };
      }

      return {
        success: true,
        message: "Re-subscription initiated! Please check your email to verify.",
        email,
        status: 200,
      };
    }

    // Not verified — resend
    let token = row.verification_token;
    if (!token) {
      token = crypto.randomUUID().replace(/-/g, "");
      await db.execute({
        sql: "UPDATE subscribers SET verification_token = ? WHERE email = ?",
        args: [token, email],
      });
    }

    const sent = await sendVerificationEmail(email, token);
    if (!sent) {
      return {
        success: false,
        message: "Failed to send verification email. Please try again.",
        email,
        status: 500,
      };
    }

    return {
      success: true,
      message: "Verification email resent! Please check your inbox.",
      email,
      status: 200,
    };
  }

  // New subscriber
  const token = crypto.randomUUID().replace(/-/g, "");
  await db.execute({
    sql: "INSERT INTO subscribers (email, verification_token) VALUES (?, ?)",
    args: [email, token],
  });

  const sent = await sendVerificationEmail(email, token);
  if (!sent) {
    return {
      success: false,
      message: "Failed to send verification email. Please try again.",
      email,
      status: 500,
    };
  }

  return {
    success: true,
    message: "Subscription successful! Please check your email to verify.",
    email,
    status: 201,
  };
}

import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { isValidEmail, generateToken } from "../_lib";
import { sendVerificationEmail } from "@/lib/email";

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as { email?: string };
    const email = (body.email || "").trim().toLowerCase();

    if (!email || !isValidEmail(email)) {
      return NextResponse.json({ error: "Invalid email address." }, { status: 400 });
    }

    const db = getDb();
    const result = await db.execute({
      sql: "SELECT id, verified, verification_token FROM subscribers WHERE email = ?",
      args: [email],
    });

    if (result.rows.length === 0) {
      return NextResponse.json({ error: "Email not found. Please subscribe first.", email }, { status: 404 });
    }

    const row = result.rows[0] as { id: number; verified: number; verification_token: string | null };

    if (row.verified) {
      return NextResponse.json({ error: "Email is already verified.", email }, { status: 409 });
    }

    const token = row.verification_token || generateToken();
    if (!row.verification_token) {
      await db.execute({
        sql: "UPDATE subscribers SET verification_token = ? WHERE email = ?",
        args: [token, email],
      });
    }

    const sent = await sendVerificationEmail(email, token);
    if (!sent) {
      return NextResponse.json({ error: "Failed to send verification email." }, { status: 500 });
    }

    return NextResponse.json({ message: "Verification email resent. Please check your inbox.", email });
  } catch (err) {
    console.error(`[ResendVerify] Error: ${err}`);
    return NextResponse.json({ error: "Internal server error." }, { status: 500 });
  }
}

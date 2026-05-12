import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { isValidEmail } from "../_lib";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const email = (searchParams.get("email") || "").trim().toLowerCase();

    if (!email || !isValidEmail(email)) {
      return NextResponse.json({ error: "Invalid email address." }, { status: 400 });
    }

    const db = getDb();
    const result = await db.execute({
      sql: "SELECT email, verified, unsubscribed, created_at, verified_at FROM subscribers WHERE email = ?",
      args: [email],
    });

    if (result.rows.length === 0) {
      return NextResponse.json({ status: "not_found", email }, { status: 404 });
    }

    const row = result.rows[0] as {
      email: string;
      verified: number;
      unsubscribed: number;
      created_at: string;
      verified_at: string | null;
    };

    let status: string;
    if (row.unsubscribed) {
      status = "unsubscribed";
    } else if (row.verified) {
      status = "verified";
    } else {
      status = "pending_verification";
    }

    return NextResponse.json({
      status,
      email: row.email,
      created_at: row.created_at,
      verified_at: row.verified_at,
    });
  } catch (err) {
    console.error(`[Status] Error: ${err}`);
    return NextResponse.json({ error: "Internal server error." }, { status: 500 });
  }
}

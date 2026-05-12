import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const token = searchParams.get("token");

    if (!token) {
      return NextResponse.redirect(new URL("/verify?status=invalid", request.url));
    }

    const db = getDb();
    const result = await db.execute({
      sql: "SELECT id, verified FROM subscribers WHERE verification_token = ?",
      args: [token],
    });

    if (result.rows.length === 0) {
      return NextResponse.redirect(new URL("/verify?status=invalid", request.url));
    }

    const row = result.rows[0] as unknown as { id: number; verified: number };

    if (row.verified) {
      return NextResponse.redirect(new URL("/verify?status=already", request.url));
    }

    await db.execute({
      sql: "UPDATE subscribers SET verified = 1, verified_at = datetime('now') WHERE id = ? AND verified = 0",
      args: [row.id],
    });

    return NextResponse.redirect(new URL("/verify?status=success", request.url));
  } catch (err) {
    console.error(`[Verify] Error: ${err}`);
    return NextResponse.redirect(new URL("/verify?status=invalid", request.url));
  }
}

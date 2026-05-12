import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const token = searchParams.get("token");

    console.log(`[Verify] Received token: ${token ? token.slice(0, 12) + '...' : 'NONE'}`);

    if (!token) {
      return NextResponse.redirect(new URL("/verify?status=invalid", request.url));
    }

    const db = getDb();
    console.log(`[Verify] Querying DB for token...`);

    const result = await db.execute({
      sql: "SELECT id, verified, email FROM subscribers WHERE verification_token = ?",
      args: [token],
    });

    console.log(`[Verify] DB result rows: ${result.rows.length}`);
    if (result.rows.length > 0) {
      const row = result.rows[0] as unknown as { id: number; verified: number; email: string };
      console.log(`[Verify] Found: id=${row.id}, email=${row.email}, verified=${row.verified}`);
    }

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

    console.log(`[Verify] Verification successful for user id=${row.id}`);

    return NextResponse.redirect(new URL("/verify?status=success", request.url));
  } catch (err) {
    console.error(`[Verify] Error: ${err}`);
    return NextResponse.redirect(new URL("/verify?status=invalid", request.url));
  }
}

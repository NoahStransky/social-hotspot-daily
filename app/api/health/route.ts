import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";

export async function GET(_request: NextRequest) {
  try {
    const db = getDb();
    await db.execute({ sql: "SELECT 1 as ok", args: [] });
    return NextResponse.json({ ok: true, service: "social-hotspot-subscribe" });
  } catch (err) {
    console.error(`[Health] Error: ${err}`);
    return NextResponse.json(
      { ok: false, service: "social-hotspot-subscribe", error: "Database connection failed" },
      { status: 503 }
    );
  }
}

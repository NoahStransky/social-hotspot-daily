import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";

export async function GET(request: NextRequest) {
  try {
    const authHeader = request.headers.get("Authorization");
    const apiKey = process.env.INTERNAL_API_KEY;

    if (!authHeader || !apiKey || authHeader !== `Bearer ${apiKey}`) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const db = getDb();
    const result = await db.execute({
      sql: "SELECT email, verified, unsubscribed, created_at, verified_at FROM subscribers WHERE verified = 1 AND unsubscribed = 0 ORDER BY created_at DESC",
      args: [],
    });

    const subscribers = result.rows.map((row) => {
      const r = row as {
        email: string;
        verified: number;
        unsubscribed: number;
        created_at: string;
        verified_at: string | null;
      };
      return {
        email: r.email,
        verified: !!r.verified,
        unsubscribed: !!r.unsubscribed,
        created_at: r.created_at,
        verified_at: r.verified_at,
      };
    });

    return NextResponse.json({ subscribers, count: subscribers.length });
  } catch (err) {
    console.error(`[Subscribers] Error: ${err}`);
    return NextResponse.json({ error: "Internal server error." }, { status: 500 });
  }
}

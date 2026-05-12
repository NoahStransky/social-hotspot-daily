import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";

/**
 * POST /api/collect
 *
 * Runs the full collection pipeline directly on Vercel.
 * NOTE: On Hobby plan (10s timeout), this will likely timeout
 * for the complete pipeline. This endpoint is designed for
 * Pro/Enterprise plans (60s-900s timeout).
 *
 * For now, collection runs via GitHub Actions → scripts/collect.ts
 * which calls POST /api/submit-items instead.
 */
export async function POST(request: NextRequest) {
  try {
    // Authenticate
    const authHeader = request.headers.get("Authorization") || "";
    const apiKey = process.env.SUBSCRIBERS_API_KEY;
    if (!apiKey || authHeader !== `Bearer ${apiKey}`) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Verify DB connectivity first
    const db = getDb();
    await db.execute({ sql: "SELECT 1 as ok", args: [] });

    return NextResponse.json({
      ok: false,
      message: "Full collection not available on current plan. Use GitHub Actions workflow instead.",
      hint: "Run .github/workflows/daily.yml manually or wait for the scheduled cron job.",
    });
  } catch (err) {
    console.error(`[Collect] Error: ${err}`);
    return NextResponse.json({ error: "Internal server error." }, { status: 500 });
  }
}

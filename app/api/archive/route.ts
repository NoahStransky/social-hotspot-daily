import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import type { DailyItemRow, DailyAnalysisRow } from "@/types";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const date = searchParams.get("date");

    if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      return NextResponse.json({ error: "Invalid date format. Use YYYY-MM-DD." }, { status: 400 });
    }

    const db = getDb();

    const itemsResult = await db.execute({
      sql: "SELECT * FROM daily_items WHERE date = ? ORDER BY score DESC",
      args: [date],
    });

    if (itemsResult.rows.length === 0) {
      return NextResponse.json({ error: "No data found", date }, { status: 404 });
    }

    const analysisResult = await db.execute({
      sql: "SELECT * FROM daily_analysis WHERE date = ?",
      args: [date],
    });

    const items = itemsResult.rows as unknown as DailyItemRow[];
    const analysis = (analysisResult.rows[0] as unknown as DailyAnalysisRow | undefined) || null;

    return NextResponse.json({ date, items, analysis });
  } catch (err) {
    console.error(`[Archive] Error: ${err}`);
    return NextResponse.json({ error: "Internal server error." }, { status: 500 });
  }
}

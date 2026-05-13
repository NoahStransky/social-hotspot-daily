import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import type { DailyItemRow, DailyAnalysisRow } from "@/types";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const dateParam = searchParams.get("date");

    const db = getDb();

    // Determine date to fetch
    let targetDate = dateParam;
    if (!targetDate) {
      // Get latest available date, or today
      const today = new Date().toISOString().split("T")[0]; // YYYY-MM-DD UTC
      const datesResult = await db.execute({
        sql: "SELECT DISTINCT date FROM daily_items ORDER BY date DESC LIMIT 1",
        args: [],
      });
      targetDate = (datesResult.rows[0] as { date?: string } | undefined)?.date || today;
    }

    // Fetch items
    const itemsResult = await db.execute({
      sql: "SELECT * FROM daily_items WHERE date = ? ORDER BY score DESC",
      args: [targetDate],
    });

    if (itemsResult.rows.length === 0) {
      return NextResponse.json(
        { error: "No data available", date: targetDate },
        { status: 404 }
      );
    }

    // Fetch analysis
    const analysisResult = await db.execute({
      sql: "SELECT * FROM daily_analysis WHERE date = ?",
      args: [targetDate],
    });

    const items = itemsResult.rows as unknown as DailyItemRow[];
    const rawAnalysis = (analysisResult.rows[0] as unknown as DailyAnalysisRow | undefined) || null;

    // Parse JSON string fields from DB into objects
    const analysis = rawAnalysis
      ? {
          ...rawAnalysis,
          top_stories: rawAnalysis.top_stories
            ? (JSON.parse(rawAnalysis.top_stories) as string[])
            : null,
          trend_data: rawAnalysis.trend_data
            ? (JSON.parse(rawAnalysis.trend_data) as Record<string, number>)
            : null,
        }
      : null;

    return NextResponse.json({ date: targetDate, items, analysis });
  } catch (err) {
    console.error(`[Today] Error: ${err}`);
    return NextResponse.json({ error: "Internal server error." }, { status: 500 });
  }
}

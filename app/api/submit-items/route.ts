import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import type { SubmitItemsBody } from "@/types";

export async function POST(request: NextRequest) {
  try {
    // Authenticate
    const authHeader = request.headers.get("Authorization") || "";
    const apiKey = process.env.SUBMIT_API_KEY;
    if (!apiKey || authHeader !== `Bearer ${apiKey}`) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = (await request.json()) as SubmitItemsBody;
    const { date, items, analysis } = body;

    if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      return NextResponse.json({ error: "Invalid or missing date. Use YYYY-MM-DD." }, { status: 400 });
    }

    if (!items || !Array.isArray(items) || items.length === 0) {
      return NextResponse.json({ error: "Missing or empty items array." }, { status: 400 });
    }

    const db = getDb();

    // Delete existing items for this date (replace mode)
    await db.execute({
      sql: "DELETE FROM daily_items WHERE date = ?",
      args: [date],
    });

    // Insert items
    let insertedCount = 0;
    for (const item of items) {
      await db.execute({
        sql: `INSERT INTO daily_items (date, title, english_title, url, summary, insight, source_name, source_display, category, score, language, raw_data)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        args: [
          date,
          item.title,
          item.english_title || null,
          item.url,
          item.summary || null,
          item.insight || null,
          item.source_name,
          item.source_display || item.source_name,
          item.category || "general",
          item.score || 0,
          item.language || "en",
          item.raw_data ? JSON.stringify(item.raw_data) : null,
        ],
      });
      insertedCount++;
    }

    // Upsert analysis
    if (analysis) {
      await db.execute({
        sql: `INSERT INTO daily_analysis (date, top_topic, top_stories, trend_data)
              VALUES (?, ?, ?, ?)
              ON CONFLICT(date) DO UPDATE SET
                top_topic = excluded.top_topic,
                top_stories = excluded.top_stories,
                trend_data = excluded.trend_data`,
        args: [
          date,
          analysis.top_topic || null,
          analysis.top_stories ? JSON.stringify(analysis.top_stories) : null,
          analysis.trend_data ? JSON.stringify(analysis.trend_data) : null,
        ],
      });
    }

    return NextResponse.json({ ok: true, item_count: insertedCount, date });
  } catch (err) {
    console.error(`[SubmitItems] Error: ${err}`);
    return NextResponse.json({ error: "Internal server error." }, { status: 500 });
  }
}

import { NextResponse } from "next/server";
import { getDb } from "@/lib/db";

export async function GET() {
  try {
    const db = getDb();
    const result = await db.execute({
      sql: "SELECT date, COUNT(*) as item_count FROM daily_items GROUP BY date ORDER BY date DESC",
      args: [],
    });

    const dates = result.rows.map((row: unknown) => {
      const r = row as { date: string; item_count: number };
      return { date: r.date, item_count: r.item_count };
    });

    return NextResponse.json({ dates });
  } catch (err) {
    console.error(`[Dates] Error: ${err}`);
    return NextResponse.json({ error: "Internal server error." }, { status: 500 });
  }
}

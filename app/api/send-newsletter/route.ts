import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { buildNewsletterHtml } from "@/lib/newsletter-email";

interface Subscriber {
  email: string;
}

interface NewsItem {
  title: string;
  url: string;
  summary: string | null;
  insight: string | null;
  source_name: string;
  source_display: string | null;
  category: string;
  score: number;
}

interface AnalysisRow {
  date: string;
  top_topic: string | null;
  top_stories: string | null;
}

export async function GET() {
  return NextResponse.json({ error: "Use POST to send newsletter." }, { status: 405 });
}

export async function POST(request: NextRequest) {
  try {
    // Authenticate
    const authHeader = request.headers.get("Authorization") || "";
    const apiKey = process.env.INTERNAL_API_KEY;
    if (!apiKey || authHeader !== `Bearer ${apiKey}`) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Optional: override date (defaults to today)
    const body = (await request.json().catch(() => ({}))) as { date?: string };
    const targetDate = body.date || new Date().toISOString().split("T")[0];

    const db = getDb();

    // ── 1. Fetch subscribers ──────────────────────────────────────────────
    const subsResult = await db.execute({
      sql: "SELECT email FROM subscribers WHERE verified = 1 AND unsubscribed = 0",
      args: [],
    });
    const subscribers = subsResult.rows as unknown as Subscriber[];

    if (subscribers.length === 0) {
      return NextResponse.json({ ok: true, sent: 0, message: "No verified subscribers to send to." });
    }

    // ── 2. Fetch news items ───────────────────────────────────────────────
    const itemsResult = await db.execute({
      sql: `SELECT title, url, summary, insight, source_name, source_display, category, score
            FROM daily_items WHERE date = ? ORDER BY score DESC`,
      args: [targetDate],
    });
    const items = itemsResult.rows as unknown as NewsItem[];

    if (items.length === 0) {
      return NextResponse.json({ error: `No items found for ${targetDate}` }, { status: 404 });
    }

    // ── 3. Fetch analysis ─────────────────────────────────────────────────
    const analysisResult = await db.execute({
      sql: "SELECT date, top_topic, top_stories FROM daily_analysis WHERE date = ?",
      args: [targetDate],
    });
    const analysis = (analysisResult.rows[0] as unknown as AnalysisRow | undefined) || null;

    // ── 4. Build env config ────────────────────────────────────────────────
    const resendApiKey = process.env.RESEND_API_KEY;
    const fromEmail = process.env.FROM_EMAIL || "onboarding@resend.dev";
    const blogBaseUrl = process.env.BLOG_BASE_URL || "https://hotspot.edgesoft.org";

    if (!resendApiKey) {
      return NextResponse.json({ error: "RESEND_API_KEY not configured" }, { status: 500 });
    }

    // ── 5. Send to each subscriber ─────────────────────────────────────────
    let sentCount = 0;
    const errors: Array<{ email: string; reason: string }> = [];

    for (const sub of subscribers) {
      const unsubscribeUrl = `${blogBaseUrl}/api/unsubscribe?email=${encodeURIComponent(sub.email)}`;

      const html = buildNewsletterHtml({
        date: targetDate,
        items,
        analysis,
        blogBaseUrl,
        unsubscribeUrl,
      });

      try {
        const resp = await fetch("https://api.resend.com/emails", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${resendApiKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            from: `Tech Hotspot Daily <${fromEmail}>`,
            to: [sub.email],
            subject: `🚀 Tech Hotspot Daily — ${targetDate}`,
            html,
          }),
        });

        if (!resp.ok) {
          const errBody = await resp.text();
          errors.push({ email: sub.email, reason: `Resend API error (${resp.status}): ${errBody.slice(0, 200)}` });
          console.error(`[SendNewsletter] Failed for ${sub.email}: ${resp.status} ${errBody}`);
          continue;
        }

        sentCount++;
        console.log(`[SendNewsletter] Sent to ${sub.email}`);
      } catch (err) {
        errors.push({ email: sub.email, reason: String(err) });
        console.error(`[SendNewsletter] Network error for ${sub.email}: ${err}`);
      }
    }

    return NextResponse.json({
      ok: true,
      date: targetDate,
      total_subscribers: subscribers.length,
      sent: sentCount,
      failed: errors.length,
      errors: errors.length > 0 ? errors : undefined,
    });
  } catch (err) {
    console.error(`[SendNewsletter] Error: ${err}`);
    return NextResponse.json({ error: "Internal server error." }, { status: 500 });
  }
}

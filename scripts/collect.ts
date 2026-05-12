/**
 * Collection Script — runs in GitHub Actions (no Vercel timeout limit).
 *
 * Usage:
 *   npx tsx scripts/collect.ts
 *   npx tsx scripts/collect.ts --date 2026-05-12
 *
 * Environment Variables (set in GitHub Secrets):
 *   DEEPSEEK_API_KEY        — required for AI filter
 *   DEEPSEEK_MODEL          — optional (default: deepseek-chat)
 *   TWITTER_BEARER_TOKEN    — optional
 *   REDDIT_CLIENT_ID        — optional
 *   REDDIT_CLIENT_SECRET    — optional
 *   YOUTUBE_API_KEY         — optional
 *   TELEGRAM_BOT_TOKEN      — optional (for notifications)
 *   TELEGRAM_CHAT_ID        — optional
 *   SUBMIT_API_KEY          — required (shared with Vercel)
 *   SUBMIT_API_URL          — required (e.g. https://hotspot.edgesoft.org/api/submit-items)
 */

import { loadCollectors } from "../lib/collectors/index";
import { deduplicate } from "../lib/processors/dedup";
import { AIFilter } from "../lib/processors/ai-filter";
import type { NewsItem } from "../types";

async function main() {
  const date = getDateArg();
  console.log(`=" Social Hotspot Daily Collection [${date}] "`);

  // ─── 1. Load config from env ───────────────────────────────────────
  const config = {
    sources: {
      hackernews: { enabled: true },
      reddit: {
        enabled: !!process.env.REDDIT_CLIENT_ID,
        client_id: process.env.REDDIT_CLIENT_ID || "",
        client_secret: process.env.REDDIT_CLIENT_SECRET || "",
        user_agent: "SocialHotspotDaily/1.0",
      },
      rss: { enabled: true, feeds: [] as string[] },
      twitter: {
        enabled: !!process.env.TWITTER_BEARER_TOKEN,
        bearer_token: process.env.TWITTER_BEARER_TOKEN || "",
      },
      youtube: {
        enabled: !!process.env.YOUTUBE_API_KEY,
        api_key: process.env.YOUTUBE_API_KEY || "",
      },
      weibo: { enabled: true },
      zhihu: { enabled: true },
    },
  };

  const apiKey = process.env.SUBMIT_API_KEY;
  const apiUrl = process.env.SUBMIT_API_URL || "https://hotspot.edgesoft.org/api/submit-items";
  const deepseekKey = process.env.DEEPSEEK_API_KEY;

  if (!apiKey) {
    console.error("❌ SUBMIT_API_KEY not set");
    process.exit(1);
  }

  // ─── 2. Collect from all sources ───────────────────────────────────
  console.log("\n📡 Collecting from sources...");
  const collectors = loadCollectors(config);
  const allItems: NewsItem[] = [];

  for (const collector of collectors) {
    try {
      console.log(`  [${collector.name}] Fetching...`);
      const items = await collector.collect();
      console.log(`    → ${items.length} items`);
      allItems.push(...items);
    } catch (err) {
      console.error(`    ✗ Error: ${err}`);
    }
  }

  console.log(`\n📊 Total raw items: ${allItems.length}`);

  if (allItems.length === 0) {
    console.log("No items collected. Nothing to submit.");
    await sendTelegram("❌ Social Hotspot Daily — No items collected today.");
    process.exit(0);
  }

  // ─── 3. Deduplicate ────────────────────────────────────────────────
  console.log("\n🔍 Deduplicating...");
  const uniqueItems = deduplicate(allItems);
  console.log(`  After dedup: ${uniqueItems.length} items`);

  // ─── 4. AI Filter & Enrich ─────────────────────────────────────────
  console.log("\n🤖 AI filtering & enrichment...");
  let enrichedItems = uniqueItems.map((item) => ({
    ...item,
    english_title: item.title,
    insight: "",
    score: 0.5,
    source_display: item.source_name,
  }));
  let trendAnalysis = null;

  if (deepseekKey) {
    try {
      const filter = new AIFilter({
        apiKey: deepseekKey,
        model: process.env.DEEPSEEK_MODEL || "deepseek-chat",
      });
      const result = await filter.process(uniqueItems);
      enrichedItems = result.items;
      trendAnalysis = result.analysis;

      console.log(`  Enriched: ${enrichedItems.length} items`);
      if (trendAnalysis) {
        console.log(`  Top topic: ${trendAnalysis.top_topic}`);
      }
    } catch (err) {
      console.error(`  ✗ AI filter error: ${err}`);
      console.log("  Using default enrichment");
    }
  } else {
    console.log("  ⚠️ DEEPSEEK_API_KEY not set — skipping AI filter");
  }

  // ─── 5. Submit to API ──────────────────────────────────────────────
  console.log("\n📤 Submitting to API...");
  const body = {
    date,
    items: enrichedItems.map((item) => ({
      title: item.title,
      english_title: item.english_title,
      url: item.url,
      summary: item.summary,
      insight: item.insight,
      source_name: item.source,
      source_display: item.source_display,
      category: item.category,
      score: item.score,
      language: item.language,
      raw_data: item.raw_data,
    })),
    analysis: trendAnalysis
      ? {
          top_topic: trendAnalysis.top_topic,
          top_stories: trendAnalysis.top_stories,
          trend_data: trendAnalysis.trend_data,
        }
      : undefined,
  };

  try {
    const resp = await fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify(body),
    });

    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`API error (${resp.status}): ${text}`);
    }

    const result = (await resp.json()) as { ok: boolean; item_count: number; date: string };
    console.log(`  ✅ Submitted ${result.item_count} items for ${result.date}`);

    // ─── 6. Telegram notification ──────────────────────────────────
    const topItems = enrichedItems.slice(0, 5);
    const topTopic = trendAnalysis?.top_topic || "Tech News";
    const message = [
      `📰 *Social Hotspot Daily — ${date}*`,
      ``,
      `📊 *${enrichedItems.length} stories* from ${new Set(enrichedItems.map((i) => i.source)).size} sources`,
      `🏷️ Topic: *${topTopic}*`,
      ``,
      ...topItems.map((item, i) => `${i + 1}. [${item.source_display}] ${item.title}`),
      ``,
      `🔗 hotspot.edgesoft.org`,
    ].join("\n");

    await sendTelegram(message);
    console.log("  ✅ Telegram notification sent");
  } catch (err) {
    console.error(`  ❌ Failed to submit: ${err}`);
    await sendTelegram(`❌ Social Hotspot Daily — Collection failed: ${err}`);
    process.exit(1);
  }

  console.log("\n✅ Collection complete!");
}

// ─── Helpers ────────────────────────────────────────────────────────────

function getDateArg(): string {
  const args = process.argv.slice(2);
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--date" && args[i + 1]) {
      return args[i + 1];
    }
  }
  return new Date().toISOString().split("T")[0];
}

async function sendTelegram(message: string): Promise<void> {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) return;

  try {
    await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chatId,
        text: message,
        parse_mode: "Markdown",
        disable_web_page_preview: true,
      }),
    });
  } catch (err) {
    console.error(`Failed to send Telegram: ${err}`);
  }
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});

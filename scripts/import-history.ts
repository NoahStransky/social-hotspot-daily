/**
 * Import historical data from git history into Turso.
 *
 * Usage:
 *   export TURSO_DATABASE_URL="..."
 *   export TURSO_AUTH_TOKEN="..."
 *   npx tsx scripts/import-history.ts
 */

import { execSync } from "child_process";
import { createClient } from "@libsql/client";

const url = process.env.TURSO_DATABASE_URL;
const authToken = process.env.TURSO_AUTH_TOKEN;

if (!url || !authToken) {
  console.error("❌ Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN");
  process.exit(1);
}

const db = createClient({ url, authToken });

// Format: date string → paths to try in git (flat JSON and directory format)
const DATE_PATHS: { date: string; paths: string[] }[] = [
  { date: "2026-04-28", paths: ["docs/archive/2026-04-28.json"] },
  { date: "2026-04-29", paths: ["docs/archive/2026-04-29.json"] },
  { date: "2026-04-30", paths: ["docs/archive/2026-04-30.json"] },
  { date: "2026-05-01", paths: ["docs/archive/2026-05-01.json"] },
  { date: "2026-05-02", paths: ["docs/archive/2026-05-02.json"] },
  { date: "2026-05-03", paths: ["docs/archive/2026-05-03.json"] },
  { date: "2026-05-04", paths: ["docs/archive/2026-05-04.json"] },
  { date: "2026-05-05", paths: ["docs/archive/2026-05-05.json"] },
  { date: "2026-05-06", paths: ["docs/archive/2026-05-06.json"] },
  { date: "2026-05-11", paths: ["docs/archive/2026/05/11/index.json"] },
  { date: "2026-05-12", paths: ["docs/archive/2026/05/12/index.json"] },
];

interface HistoryItem {
  title: string;
  url: string;
  source: string;
  source_name: string;
  category: string;
  summary: string;
  insight: string;
  english_title: string;
  recommendation?: {
    level: string;
    read_time: string;
    relevance_to_tech: string;
  };
}

interface TrendAnalysis {
  top_topic: string;
  trending_keywords?: string[];
  category_breakdown?: Record<string, number>;
  summary?: string;
  top_stories?: string[];
}

interface HistoryData {
  date: string;
  items: HistoryItem[];
  trend_analysis?: TrendAnalysis;
}

function findCommitAndRead(dateStr: string, paths: string[]): { commit: string; data: HistoryData } | null {
  let fallbackResult: { commit: string; data: HistoryData } | null = null;
  for (const filePath of paths) {
    // git log --all finds all commits touching this path
    // We want the latest version that has trend_analysis, or the latest overall
    const allCommits = execSync(
      `cd /opt/data/home/social-hotspot-daily && git log --all --oneline -- "${filePath}" 2>/dev/null`,
      { encoding: "utf-8", maxBuffer: 1024 * 1024 }
    ).trim();

    const hashes = allCommits ? allCommits.split("\n").map(l => l.split(/\s/)[0]).filter(Boolean) : [];

    if (hashes.length === 0) continue;

    // Skip commits where the file was deleted (3c9a9bf, the migration commit)
    // Try to find a commit with trend_analysis first
    for (const hash of hashes) {
      try {
        const jsonStr = execSync(
          `cd /opt/data/home/social-hotspot-daily && git show ${hash}:"${filePath}" 2>/dev/null`,
          { encoding: "utf-8", maxBuffer: 10 * 1024 * 1024 }
        );
        const data: HistoryData = JSON.parse(jsonStr);
        if (data.trend_analysis) {
          return { commit: hash, data };
        }
        // If no trend_analysis found, save this as fallback
        if (!fallbackResult) {
          fallbackResult = { commit: hash, data };
        }
      } catch {
        continue; // file not in this commit (was deleted)
      }
    }

    if (fallbackResult) return fallbackResult;
  }
  return null;
}

async function main() {
  let totalItems = 0;
  let totalWithAnalysis = 0;
  let successCount = 0;

  for (const { date, paths } of DATE_PATHS) {
    const result = findCommitAndRead(date, paths);
    if (!result) {
      console.log(`  ⏭️  ${date}: not found in git history`);
      continue;
    }

    const { commit, data } = result;

    // Delete existing items for this date (in case rerun)
    await db.execute({
      sql: "DELETE FROM daily_items WHERE date = ?",
      args: [date],
    });

    // Insert items
    for (const item of data.items) {
      const score = item.recommendation?.relevance_to_tech === "high" ? 0.9
        : item.recommendation?.relevance_to_tech === "medium" ? 0.6 : 0.3;

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
          item.source_name || item.source || "unknown",
          item.source_name || item.source || null,
          item.category || "general",
          score,
          "en",
          item.recommendation ? JSON.stringify(item.recommendation) : null,
        ],
      });
    }

    // Insert analysis
    if (data.trend_analysis) {
      const ta = data.trend_analysis;
      await db.execute({
        sql: `INSERT INTO daily_analysis (date, top_topic, top_stories, trend_data)
              VALUES (?, ?, ?, ?)
              ON CONFLICT(date) DO UPDATE SET
                top_topic = excluded.top_topic,
                top_stories = excluded.top_stories,
                trend_data = excluded.trend_data`,
        args: [
          date,
          ta.top_topic || null,
          ta.top_stories ? JSON.stringify(ta.top_stories) : null,
          JSON.stringify({
            trending_keywords: ta.trending_keywords || [],
            category_breakdown: ta.category_breakdown || {},
            summary: ta.summary || "",
          }),
        ],
      });
      totalWithAnalysis++;
    }

    totalItems += data.items.length;
    successCount++;
    console.log(`  ✅ ${date} (commit ${commit.slice(0, 7)}): ${data.items.length} items` +
      (data.trend_analysis ? " + analysis" : ""));
  }

  console.log(`\n📊 Summary: ${successCount} dates, ${totalItems} total items`);
  console.log(`   ${totalWithAnalysis} dates with trend analysis`);
  await db.close();
}

main().catch((err) => {
  console.error("❌ Import failed:", err);
  process.exit(1);
});

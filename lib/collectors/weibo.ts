import type { Collector } from "./base";
import { createNewsItem } from "./base";

const HOT_URL = "https://s.weibo.com/top/summary?cate=realtimehot";
const MAX_ITEMS = 30;

const TECH_KEYWORDS = [
  "AI", "人工智能", "科技", "手机", "芯片", "互联网",
  "软件", "APP", "数码", "电脑", "特斯拉", "苹果",
  "华为", "微软", "谷歌", "OpenAI", "大模型",
];

export class WeiboCollector implements Collector {
  name = "weibo";
  private config: Record<string, unknown>;

  constructor(config: Record<string, unknown>) {
    this.config = config;
  }

  async collect() {
    const items = [];

    try {
      const headers: Record<string, string> = {
        "User-Agent":
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
      };

      const resp = await fetch(HOT_URL, { headers, signal: AbortSignal.timeout(20_000) });
      if (!resp.ok) {
        console.error(`[Weibo] HTTP ${resp.status}`);
        return [];
      }

      const html = await resp.text();

      // Use cheerio for HTML parsing
      let cheerio: any;
      try {
        const mod = await import("cheerio");
        // Cheerio in ESM exports its load function directly
        cheerio = (mod as any).load ? mod : (mod as any).default;
      } catch {
        console.error("[Weibo] cheerio package not available. Install with: npm install cheerio");
        return [];
      }

      const $ = cheerio.load(html);

      // Weibo hot search table rows
      const rows = $("table tr").slice(1); // skip header

      for (let i = 0; i < Math.min(rows.length, MAX_ITEMS); i++) {
        try {
          const row = $(rows[i]);
          const td = row.find("td.td-02");
          if (!td.length) continue;

          const aTag = td.find("a");
          if (!aTag.length) continue;

          const title = aTag.text().trim();
          let href = aTag.attr("href") ?? "";
          if (href.startsWith("/")) {
            href = `https://s.weibo.com${href}`;
          }

          if (!title) continue;

          // Categorize: tech if keyword match
          const isTech = TECH_KEYWORDS.some((kw) => title.includes(kw));
          const hotScore = Math.max(1000 - i * 30, 100);

          items.push(
            createNewsItem(title, href, "weibo", "微博热搜", {
              hot_score: hotScore,
              category: isTech ? "technology" : "general",
              language: "zh",
              raw_data: { rank: i + 1 },
            })
          );
        } catch {
          // per-item error: skip
        }
      }
    } catch (err) {
      console.error(`[Weibo] Error: ${err}`);
    }

    return items;
  }
}

import type { Collector } from "./base";
import { createNewsItem } from "./base";

const HOT_URL = "https://www.zhihu.com/hot";
const MAX_ITEMS = 30;

const TECH_KEYWORDS = [
  "AI", "人工智能", "科技", "手机", "芯片", "互联网",
  "软件", "APP", "数码", "电脑", "特斯拉", "苹果",
  "华为", "微软", "谷歌", "OpenAI", "大模型", "算法",
  "编程", "代码", "GPT",
];

export class ZhihuCollector implements Collector {
  name = "zhihu";
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
        Cookie: "_zap=1; d_c0=1;",
      };

      const resp = await fetch(HOT_URL, { headers, signal: AbortSignal.timeout(20_000) });
      if (!resp.ok) {
        console.error(`[Zhihu] HTTP ${resp.status}`);
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
        console.error("[Zhihu] cheerio package not available. Install with: npm install cheerio");
        return [];
      }

      const $ = cheerio.load(html);

      // Zhihu hot list: try multiple selectors
      let hotItems = $(".HotList-item");
      if (!hotItems.length) {
        hotItems = $("[data-za-detail-view-path]");
      }
      if (!hotItems.length) {
        // Fallback: parse all link cards to questions
        hotItems = $("a[href^='/question/']");
      }

      for (let i = 0; i < Math.min(hotItems.length, MAX_ITEMS); i++) {
        try {
          const item = $(hotItems[i]);

          // Try multiple title selectors
          const titleElem =
            item.find(".HotList-itemTitle").first() ??
            item.find("h2").first() ??
            item;
          let title = titleElem.text().trim();
          if (!title) title = item.text().trim();

          if (!title || title.length < 3) continue;

          // Find the link
          let link = item.attr("href") ?? "";
          if (!link.startsWith("http")) {
            link = `https://www.zhihu.com${link}`;
          }

          // Categorize: tech if keyword match
          const isTech = TECH_KEYWORDS.some((kw) => title.includes(kw));
          const hotScore = Math.max(1000 - i * 30, 100);

          items.push(
            createNewsItem(title, link, "zhihu", "知乎热榜", {
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
      console.error(`[Zhihu] Error: ${err}`);
    }

    return items;
  }
}

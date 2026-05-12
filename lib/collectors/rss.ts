import type { Collector } from "./base";
import { createNewsItem } from "./base";

// Note: rss-parser is ESM-only in recent versions.
// We use a dynamic import pattern to stay compatible with both CJS and ESM.

const DEFAULT_FEEDS: { url: string; name: string; category: string }[] = [
  { url: "https://feeds.feedburner.com/TheHackersNews", name: "The Hacker News", category: "security" },
  { url: "https://blog.google/threat-analysis-group/rss", name: "Google TAG", category: "security" },
  { url: "https://arxiv.org/rss/cs.AI", name: "arXiv AI", category: "ai" },
  { url: "https://arxiv.org/rss/cs.CL", name: "arXiv NLP", category: "ai" },
  { url: "https://feeds.arstechnica.com/arstechnica/index", name: "Ars Technica", category: "tech" },
  { url: "https://www.theverge.com/rss/index.xml", name: "The Verge", category: "tech" },
  { url: "https://www.techradar.com/rss", name: "TechRadar", category: "tech" },
  { url: "https://www.zdnet.com/news/rss.xml", name: "ZDNet", category: "tech" },
];

export class RSSCollector implements Collector {
  name = "rss";
  private config: Record<string, unknown>;

  constructor(config: Record<string, unknown>) {
    this.config = config;
  }

  async collect() {
    const items = [];

    // Load rss-parser dynamically to handle ESM/CJS interop
    let Parser: any;
    try {
      const mod = await import("rss-parser");
      Parser = mod.default ?? mod;
    } catch {
      console.error("[RSS] rss-parser package not available. Install with: npm install rss-parser");
      return [];
    }

    const feeds = (this.config.feeds as { url: string; name: string; category: string }[]) ?? DEFAULT_FEEDS;
    const parser = new Parser();
    const maxPerFeed = (this.config.max_per_feed as number) ?? 15;
    const maxTotal = (this.config.max_total as number) ?? 30;

    for (const feed of feeds) {
      if (items.length >= maxTotal) break;

      try {
        const parsed = await parser.parseURL(feed.url);
        const entries = (parsed.items ?? []).slice(0, maxPerFeed);

        for (let i = 0; i < entries.length; i++) {
          if (items.length >= maxTotal) break;

          const entry = entries[i];
          const title = entry.title ?? "";
          const link = entry.link ?? "";

          if (!title || !link) continue;

          const hotScore = Math.max(500 - i * 20, 50);

          items.push(
            createNewsItem(title, link, "rss", feed.name, {
              hot_score: hotScore,
              category: feed.category,
              language: "en",
              raw_data: { feed: feed.url },
            })
          );
        }
      } catch (err) {
        console.error(`[RSS] Error parsing ${feed.url}: ${err}`);
      }
    }

    return items;
  }
}

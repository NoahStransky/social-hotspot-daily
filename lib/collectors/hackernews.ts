import type { Collector, CollectorConfig } from "./base";
import { createNewsItem } from "./base";

const BASE_URL = "https://hacker-news.firebaseio.com/v0";
const DEFAULT_LIMIT = 30;

export class HackerNewsCollector implements Collector {
  name = "hackernews";
  private config: Record<string, unknown>;

  constructor(config: Record<string, unknown>) {
    this.config = config;
  }

  async collect() {
    const items = [];
    const limit = (this.config.top_stories_limit as number) ?? DEFAULT_LIMIT;

    try {
      const topResp = await fetch(`${BASE_URL}/topstories.json`, {
        signal: AbortSignal.timeout(30_000),
      });
      if (!topResp.ok) {
        console.error(`[HackerNews] HTTP ${topResp.status} fetching top stories`);
        return [];
      }
      const storyIds: number[] = await topResp.json();
      const ids = storyIds.slice(0, limit);

      for (const storyId of ids) {
        try {
          const itemResp = await fetch(`${BASE_URL}/item/${storyId}.json`, {
            signal: AbortSignal.timeout(10_000),
          });
          if (!itemResp.ok) continue;

          const story: Record<string, unknown> = await itemResp.json();
          if (!story || story.deleted || story.dead) continue;

          const title = (story.title as string) ?? "";
          const url = (story.url as string) ?? `https://news.ycombinator.com/item?id=${storyId}`;
          const score = (story.score as number) ?? 0;
          const descendants = (story.descendants as number) ?? 0;

          // HN hot score: weighted combination
          const hotScore = score * 0.7 + descendants * 0.3;

          items.push(
            createNewsItem(title, url, "hackernews", "Hacker News", {
              hot_score: Math.round(hotScore * 10) / 10,
              category: "technology",
              language: "en",
              raw_data: story as Record<string, unknown>,
            })
          );
        } catch {
          // per-item error: skip and continue
        }
      }
    } catch (err) {
      console.error(`[HackerNews] Error: ${err}`);
    }

    return items;
  }
}

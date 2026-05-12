import type { Collector } from "./base";
import { createNewsItem } from "./base";

const API_BASE = "https://youtube.googleapis.com/youtube/v3";

export class YouTubeCollector implements Collector {
  name = "youtube";
  private config: Record<string, unknown>;
  private apiKey: string | null = null;

  constructor(config: Record<string, unknown>) {
    this.config = config;
    this.apiKey = (config.api_key as string) ?? null;
  }

  async collect() {
    if (!this.apiKey) return [];

    const items = [];
    const region = (this.config.region_code as string) ?? "US";
    const category = (this.config.category_id as string) ?? "28"; // Science & Tech
    const maxResults = (this.config.max_results as number) ?? 10;

    try {
      const params = new URLSearchParams({
        part: "snippet,statistics",
        chart: "mostPopular",
        regionCode: region,
        videoCategoryId: category,
        maxResults: String(maxResults),
        key: this.apiKey,
      });

      const resp = await fetch(`${API_BASE}/videos?${params}`, {
        signal: AbortSignal.timeout(15_000),
      });

      if (!resp.ok) {
        console.error(`[YouTube] HTTP ${resp.status}: ${await resp.text()}`);
        return [];
      }

      const data = (await resp.json()) as {
        items?: {
          id: string;
          snippet: {
            title: string;
            channelTitle: string;
            defaultLanguage?: string;
          };
          statistics?: {
            viewCount?: string;
            likeCount?: string;
            commentCount?: string;
          };
        }[];
      };

      for (const item of data.items ?? []) {
        try {
          const snippet = item.snippet;
          const stats = item.statistics ?? {};
          const videoId = item.id;

          const title = snippet.title ?? "";
          const url = `https://youtube.com/watch?v=${videoId}`;
          const views = parseInt(stats.viewCount ?? "0", 10);
          const likes = parseInt(stats.likeCount ?? "0", 10);
          const hotScore = views * 0.001 + likes * 0.1;

          items.push(
            createNewsItem(title, url, "youtube", snippet.channelTitle ?? "YouTube", {
              hot_score: Math.round(hotScore * 10) / 10,
              category: "technology",
              language: snippet.defaultLanguage ?? "en",
              raw_data: stats as Record<string, unknown>,
            })
          );
        } catch {
          // per-item error: skip
        }
      }
    } catch (err) {
      console.error(`[YouTube] Error: ${err}`);
    }

    return items;
  }
}

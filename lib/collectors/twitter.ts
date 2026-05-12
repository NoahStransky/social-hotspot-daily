import type { Collector } from "./base";
import { createNewsItem } from "./base";

const API_BASE = "https://api.twitter.com/2";

// Tech news / AI accounts and topics to track
const DEFAULT_QUERY =
  '(tech OR AI OR programming OR "machine learning" OR cybersecurity OR "open source") lang:en -is:retweet -is:reply';

const FEATURED_USERS = [
  "ylecun",
  "goodside",
  "katecrawford",
  "kareem_carr",
  "sama",
  "elonmusk",
];

export class TwitterCollector implements Collector {
  name = "twitter";
  private config: Record<string, unknown>;
  private bearerToken: string | null = null;

  constructor(config: Record<string, unknown>) {
    this.config = config;
    this.bearerToken = (config.bearer_token as string) ?? null;
  }

  async collect() {
    if (!this.bearerToken) return [];

    const items = [];
    const maxResults = (this.config.max_results as number) ?? 15;

    try {
      // Search recent tweets with tech keywords
      const searchUrl = `${API_BASE}/tweets/search/recent`;
      const params = new URLSearchParams({
        query: DEFAULT_QUERY,
        "tweet.fields": "public_metrics,created_at,author_id",
        "user.fields": "username",
        expansions: "author_id",
        max_results: String(Math.min(maxResults, 20)),
      });

      const resp = await fetch(`${searchUrl}?${params}`, {
        headers: {
          Authorization: `Bearer ${this.bearerToken}`,
          "Content-Type": "application/json",
        },
        signal: AbortSignal.timeout(15_000),
      });

      if (!resp.ok) {
        console.error(`[Twitter] HTTP ${resp.status}: ${await resp.text()}`);
        return [];
      }

      const data = (await resp.json()) as {
        data?: { id: string; text: string; author_id: string; public_metrics?: Record<string, number> }[];
        includes?: { users?: { id: string; username: string }[] };
      };

      if (!data.data || data.data.length === 0) return [];

      // Build author_id → username map
      const users = new Map<string, string>();
      for (const user of data.includes?.users ?? []) {
        users.set(user.id, user.username);
      }

      for (const tweet of data.data) {
        const username = users.get(tweet.author_id) ?? "unknown";
        const metrics = tweet.public_metrics ?? {};
        const hotScore =
          (metrics.like_count ?? 0) * 1.0 +
          (metrics.retweet_count ?? 0) * 2.0 +
          (metrics.reply_count ?? 0) * 0.5;

        const url = `https://twitter.com/${username}/status/${tweet.id}`;

        items.push(
          createNewsItem(tweet.text.slice(0, 200), url, "twitter", `@${username}`, {
            hot_score: Math.round(hotScore * 10) / 10,
            category: "technology",
            language: "en",
            raw_data: metrics as Record<string, unknown>,
          })
        );
      }
    } catch (err) {
      console.error(`[Twitter] Error: ${err}`);
    }

    return items;
  }
}

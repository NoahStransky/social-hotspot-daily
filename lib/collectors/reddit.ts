import type { Collector } from "./base";
import { createNewsItem } from "./base";

const DEFAULT_SUBREDDITS = [
  "technology",
  "programming",
  "MachineLearning",
  "science",
  "Futurology",
];

export class RedditCollector implements Collector {
  name = "reddit";
  private config: Record<string, unknown>;
  private snoowrap: any = null;

  constructor(config: Record<string, unknown>) {
    this.config = config;
    const clientId = config.client_id as string | undefined;
    const clientSecret = config.client_secret as string | undefined;

    if (clientId && clientSecret) {
      try {
        // Dynamic import to avoid crash if package not installed
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const snoowrap = require("snoowrap");
        this.snoowrap = new snoowrap({
          clientId,
          clientSecret,
          userAgent: (config.user_agent as string) ?? "SocialHotspotBot/1.0",
        });
      } catch (err) {
        console.error(`[Reddit] Auth failed: ${err}`);
      }
    }
  }

  async collect() {
    if (!this.snoowrap) return [];

    const items = [];
    const subreddits = (this.config.subreddits as string[]) ?? DEFAULT_SUBREDDITS;
    const limit = (this.config.limit as number) ?? 25;

    for (const subName of subreddits) {
      try {
        const sub = await this.snoowrap.getSubreddit(subName);
        const posts = await sub.getHot({ limit });

        for (const post of posts) {
          if (post.stickied) continue;

          const hotScore = post.score * 0.6 + post.num_comments * 0.4;

          items.push(
            createNewsItem(
              post.title,
              post.url,
              "reddit",
              `r/${subName}`,
              {
                hot_score: Math.round(hotScore * 10) / 10,
                category: "technology",
                language: "en",
                raw_data: {
                  score: post.score,
                  comments: post.num_comments,
                  upvote_ratio: post.upvote_ratio,
                },
              }
            )
          );
        }
      } catch (err) {
        console.error(`[Reddit] Error in r/${subName}: ${err}`);
      }
    }

    return items;
  }
}

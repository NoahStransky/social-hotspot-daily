import type { Collector } from "./base";
import { HackerNewsCollector } from "./hackernews";
import { RedditCollector } from "./reddit";
import { RSSCollector } from "./rss";
import { TwitterCollector } from "./twitter";
import { YouTubeCollector } from "./youtube";
import { WeiboCollector } from "./weibo";
import { ZhihuCollector } from "./zhihu";

const COLLECTOR_CLASSES: Record<string, new (config: Record<string, unknown>) => Collector> = {
  hackernews: HackerNewsCollector,
  reddit: RedditCollector,
  rss: RSSCollector,
  twitter: TwitterCollector,
  youtube: YouTubeCollector,
  weibo: WeiboCollector,
  zhihu: ZhihuCollector,
};

export function loadCollectors(config: Record<string, unknown>): Collector[] {
  const sources = (config.sources as Record<string, Record<string, unknown>>) || {};
  const instances: Collector[] = [];

  for (const [name, cls] of Object.entries(COLLECTOR_CLASSES)) {
    const sourceConfig = sources[name] || {};
    instances.push(new cls(sourceConfig));
  }

  return instances;
}

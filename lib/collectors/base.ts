import type { NewsItem } from "@/types";

export interface CollectorConfig {
  enabled: boolean;
  [key: string]: unknown;
}

export interface Collector {
  name: string;
  collect(): Promise<NewsItem[]>;
}

export function createNewsItem(
  title: string,
  url: string,
  source: string,
  sourceName: string,
  overrides?: Partial<NewsItem>
): NewsItem {
  return {
    title,
    url,
    source,
    source_name: sourceName,
    hot_score: overrides?.hot_score ?? 0,
    category: overrides?.category ?? "general",
    language: overrides?.language ?? "en",
    summary: overrides?.summary ?? "",
    collected_at: new Date().toISOString(),
    raw_data: overrides?.raw_data ?? {},
    ...overrides,
  };
}

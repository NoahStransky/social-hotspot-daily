import type { NewsItem } from "@/types";

/**
 * Deduplicate news items by URL (exact) and title (fuzzy).
 */
export function deduplicate(items: NewsItem[]): NewsItem[] {
  const seenUrls = new Set<string>();
  const seenTitles = new Set<string>();
  const result: NewsItem[] = [];

  for (const item of items) {
    // URL-based dedup
    const urlKey = item.url.toLowerCase().trim();
    if (seenUrls.has(urlKey)) continue;
    seenUrls.add(urlKey);

    // Fuzzy title dedup: normalize and check similarity
    const titleKey = normalizeTitle(item.title);
    if (seenTitles.has(titleKey)) continue;

    // Check similarity with existing titles
    let isDuplicate = false;
    for (const existing of seenTitles) {
      if (titleSimilarity(titleKey, existing) > 0.8) {
        isDuplicate = true;
        break;
      }
    }
    if (isDuplicate) continue;

    seenTitles.add(titleKey);
    result.push(item);
  }

  return result;
}

function normalizeTitle(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fff\s]/g, "")  // keep chinese chars
    .replace(/\s+/g, " ")
    .trim();
}

function titleSimilarity(a: string, b: string): number {
  if (a === b) return 1.0;
  if (a.includes(b) || b.includes(a)) return 0.9;

  // Simple word-overlap similarity
  const wordsA = new Set(a.split(" "));
  const wordsB = new Set(b.split(" "));
  const intersection = new Set([...wordsA].filter((w) => wordsB.has(w)));
  const union = new Set([...wordsA, ...wordsB]);

  return intersection.size / union.size;
}

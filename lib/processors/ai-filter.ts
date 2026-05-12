import type { NewsItem, EnrichedItem, TrendAnalysis } from "@/types";

export interface AIFilterConfig {
  apiKey: string;
  model?: string;
}

/**
 * AI filter & enrichment using DeepSeek API.
 * Sends items in batches to:
 * 1. Score relevance (0-1)
 * 2. Generate English title for non-EN items
 * 3. Generate insight ("why it matters")
 * 4. Classify into category
 * 5. Extract trend analysis
 */
export class AIFilter {
  private apiKey: string;
  private model: string;

  constructor(config: AIFilterConfig) {
    this.apiKey = config.apiKey;
    this.model = config.model || "deepseek-chat";
  }

  async process(items: NewsItem[]): Promise<{ items: EnrichedItem[]; analysis: TrendAnalysis | null }> {
    if (!this.apiKey || items.length === 0) {
      return {
        items: items.map((item) => this.defaultEnrich(item)),
        analysis: null,
      };
    }

    try {
      // Process in batches of 15 (to stay within token limits)
      const BATCH_SIZE = 15;
      const batches: NewsItem[][] = [];
      for (let i = 0; i < items.length; i += BATCH_SIZE) {
        batches.push(items.slice(i, i + BATCH_SIZE));
      }

      const allEnriched: EnrichedItem[] = [];
      let trendAnalysis: TrendAnalysis | null = null;

      for (const batch of batches) {
        const result = await this.processBatch(batch);
        allEnriched.push(...result.items);
        if (result.analysis) {
          trendAnalysis = result.analysis;
        }
      }

      // Sort by score descending
      allEnriched.sort((a, b) => b.score - a.score);

      return { items: allEnriched, analysis: trendAnalysis };
    } catch (err) {
      console.error(`[AI Filter] Batch processing failed: ${err}`);
      // Fallback: return items with default enrichment
      return {
        items: items.map((item) => this.defaultEnrich(item)),
        analysis: null,
      };
    }
  }

  private async processBatch(
    batch: NewsItem[]
  ): Promise<{ items: EnrichedItem[]; analysis: TrendAnalysis | null }> {
    const prompt = this.buildPrompt(batch);

    const resp = await fetch("https://api.deepseek.com/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        model: this.model,
        messages: [
          {
            role: "system",
            content: `You are a tech news curator. For each news item, provide:
1. A relevance score (0.0-1.0, higher = more relevant to IT professionals)
2. An English title (translate if needed)
3. A brief insight explaining why this matters
4. A category: ai, programming, tech, security, science, business, or general
5. Overall trend analysis: what's the top topic today?

Respond with valid JSON ONLY. No markdown. No code blocks.`,
          },
          { role: "user", content: prompt },
        ],
        temperature: 0.3,
        max_tokens: 4000,
      }),
    });

    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`DeepSeek API error (${resp.status}): ${text}`);
    }

    const data = (await resp.json()) as {
      choices: Array<{ message: { content: string } }>;
    };

    const content = data.choices?.[0]?.message?.content;
    if (!content) throw new Error("Empty response from DeepSeek");

    return this.parseResponse(content, batch);
  }

  private buildPrompt(items: NewsItem[]): string {
    return items
      .map(
        (item, i) =>
          `${i + 1}. Title: ${item.title}\n   Source: ${item.source_name}\n   Language: ${item.language}\n   Summary: ${item.summary}\n`
      )
      .join("\n");
  }

  private parseResponse(
    content: string,
    batch: NewsItem[]
  ): { items: EnrichedItem[]; analysis: TrendAnalysis | null } {
    try {
      const parsed = JSON.parse(content);

      const enriched: EnrichedItem[] = batch.map((item, i) => {
        const result = parsed[`item_${i + 1}`] || parsed[i] || {};
        return {
          ...item,
          english_title:
            result.english_title || result.title || item.title,
          insight: result.insight || "",
          score: typeof result.score === "number" ? result.score : 0.5,
          source_display:
            result.category === "ai"
              ? item.source_name
              : item.source_name,
        };
      });

      const analysis: TrendAnalysis | null = parsed.analysis
        ? {
            top_topic: parsed.analysis.top_topic || "",
            top_stories: parsed.analysis.top_stories || [],
            trend_data: parsed.analysis.trend_data || {},
          }
        : null;

      return { items: enriched, analysis };
    } catch {
      // If JSON parsing fails, return default enrichment
      return {
        items: batch.map((item) => this.defaultEnrich(item)),
        analysis: null,
      };
    }
  }

  private defaultEnrich(item: NewsItem): EnrichedItem {
    return {
      ...item,
      english_title: item.title,
      insight: "",
      score: 0.5,
      source_display: item.source_name,
    };
  }
}

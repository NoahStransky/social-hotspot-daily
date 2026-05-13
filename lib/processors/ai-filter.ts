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
            content: `You are a tech news curator. Analyze the news items below and respond with a JSON object.

For each item (numbered 1, 2, 3...), provide:
- "score": relevance to IT professionals (0.0-1.0)
- "english_title": English translation if not EN, or original title
- "insight": brief "why this matters" (1-2 sentences)
- "category": one of "ai", "programming", "tech", "security", "science", "business", "general"

Also provide an "analysis" object with:
- "top_topic": single overarching topic of the day
- "top_stories": array of the 3 most important story titles
- "trend_data": object mapping category names to counts

RESPOND WITH VALID JSON ONLY — NO markdown, no code blocks, no backticks. Use this exact structure:
{"item_1":{"score":0.95,"english_title":"...","insight":"...","category":"ai"},"item_2":{...},"analysis":{"top_topic":"...","top_stories":["..."],"trend_data":{"ai":3,"tech":2}}}`
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

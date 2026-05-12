// ─── Data Types ──────────────────────────────────────────────────────

export interface NewsItem {
  id?: string;
  title: string;
  url: string;
  source: string;         // e.g. "hackernews", "reddit"
  source_name: string;    // e.g. "Hacker News", "r/technology"
  hot_score: number;
  category: string;
  language: string;
  summary: string;
  collected_at: string;
  raw_data: Record<string, unknown>;
}

// Enriched by AI filter
export interface EnrichedItem extends NewsItem {
  english_title: string;
  insight: string;
  score: number;
  source_display: string;
}

// Stored in DB
export interface DailyItemRow {
  id: number;
  date: string;
  title: string;
  english_title: string | null;
  url: string;
  summary: string | null;
  insight: string | null;
  source_name: string;
  source_display: string | null;
  category: string;
  score: number;
  language: string;
  raw_data: string | null;  // JSON string
  created_at: string;
}

export interface TrendAnalysis {
  top_topic: string;
  top_stories?: string[];
  trend_data?: Record<string, unknown>;
}

export interface DailyAnalysisRow {
  id: number;
  date: string;
  top_topic: string | null;
  top_stories: string | null;  // JSON
  trend_data: string | null;   // JSON
  created_at: string;
}

// ─── API Types ───────────────────────────────────────────────────────

export interface SubmitItemsBody {
  date: string;
  items: EnrichedItem[];
  analysis?: TrendAnalysis;
}

export interface TodayResponse {
  date: string;
  items: DailyItemRow[];
  analysis: DailyAnalysisRow | null;
}

export interface DatesResponse {
  dates: { date: string; item_count: number }[];
}

export interface SubscriberRow {
  id: number;
  email: string;
  verified: number;
  verification_token: string | null;
  created_at: string;
  verified_at: string | null;
  unsubscribed: number;
  preferences: string;
}

export interface ApiError {
  error: string;
}

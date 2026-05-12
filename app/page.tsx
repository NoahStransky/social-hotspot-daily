"use client";

import { useState, useEffect, useCallback } from "react";
import type { DailyItemRow, DailyAnalysisRow } from "@/types";

interface TodayData {
  date: string;
  items: DailyItemRow[];
  analysis: DailyAnalysisRow | null;
}

interface DateEntry {
  date: string;
  item_count: number;
}

export default function HomePage() {
  const [data, setData] = useState<TodayData | null>(null);
  const [availableDates, setAvailableDates] = useState<DateEntry[]>([]);
  const [currentDate, setCurrentDate] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async (date: string) => {
    setLoading(true);
    setError(null);
    try {
      const url = date
        ? `/api/archive?date=${date}`
        : "/api/today";
      const resp = await fetch(url);
      if (!resp.ok) {
        if (resp.status === 404) {
          setData(null);
          setLoading(false);
          return;
        }
        throw new Error(`HTTP ${resp.status}`);
      }
      const result = (await resp.json()) as TodayData;
      setData(result);
      setCurrentDate(result.date);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchDates = useCallback(async () => {
    try {
      const resp = await fetch("/api/dates");
      if (resp.ok) {
        const result = await resp.json() as { dates: DateEntry[] };
        setAvailableDates(result.dates);
      }
    } catch {
      // Non-critical
    }
  }, []);

  useEffect(() => {
    fetchData("");
    fetchDates();
  }, [fetchData, fetchDates]);

  const goToDate = (date: string) => {
    fetchData(date);
  };

  const goToday = () => {
    fetchData("");
  };

  const currentIndex = availableDates.findIndex((d) => d.date === currentDate);

  const navigate = (direction: "prev" | "next") => {
    const idx = currentIndex + (direction === "prev" ? 1 : -1);
    if (idx >= 0 && idx < availableDates.length) {
      goToDate(availableDates[idx].date);
    }
  };

  // Group items by category
  const grouped = data?.items.reduce(
    (acc, item) => {
      const cat = item.category || "general";
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(item);
      return acc;
    },
    {} as Record<string, DailyItemRow[]>
  );

  const categoryLabels: Record<string, string> = {
    ai: "🤖 AI & Machine Learning",
    programming: "💻 Programming",
    tech: "🔧 Technology",
    security: "🔒 Security",
    science: "🔬 Science",
    business: "💼 Business",
    general: "📌 General",
  };

  const categoryOrder = ["ai", "programming", "tech", "security", "science", "business", "general"];

  return (
    <div className="container">
      {/* Header */}
      <header className="header">
        <h1>📰 Tech Hotspot Daily</h1>
        <p className="date">
          {currentDate
            ? new Date(currentDate + "T00:00:00").toLocaleDateString("en-US", {
                weekday: "long",
                year: "numeric",
                month: "long",
                day: "numeric",
              })
            : "Loading..."}
        </p>
        {data?.analysis?.top_topic && (
          <span className="topic">{data.analysis.top_topic}</span>
        )}
      </header>

      {/* Navigation */}
      <nav className="nav">
        <button
          onClick={() => navigate("prev")}
          disabled={currentIndex >= availableDates.length - 1}
        >
          ← Previous Day
        </button>
        <button onClick={goToday} disabled={!currentDate}>
          📍 Today
        </button>
        <button onClick={() => navigate("next")} disabled={currentIndex <= 0}>
          Next Day →
        </button>
      </nav>

      {/* Loading */}
      {loading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>Loading today&apos;s news...</p>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="error">
          <h2>⚠️ Something went wrong</h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>{error}</p>
          <button
            onClick={goToday}
            style={{
              marginTop: "16px",
              padding: "10px 24px",
              background: "var(--accent)",
              color: "white",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer",
              fontSize: "14px",
            }}
          >
            Try Again
          </button>
        </div>
      )}

      {/* No Data */}
      {!loading && !error && !data && (
        <div className="empty-state">
          <div className="icon">📭</div>
          <h2>No news for today yet</h2>
          <p>Today&apos;s collection may not have run yet.</p>
          <p style={{ marginTop: "8px", fontSize: "13px" }}>
            Check back later or browse the archive.
          </p>
        </div>
      )}

      {/* Items */}
      {!loading && data && grouped && (
        <>
          {categoryOrder.map((cat) => {
            const items = grouped[cat];
            if (!items || items.length === 0) return null;
            return (
              <div key={cat}>
                <h2 className="section-title">
                  {categoryLabels[cat] || cat}
                </h2>
                {items.map((item) => (
                  <article key={item.id} className="item">
                    <div className="item-meta">
                      <span className="category">{item.source_display || item.source_name}</span>
                      <span
                        className="score-dot"
                        style={{
                          background:
                            item.score >= 0.8
                              ? "var(--success)"
                              : item.score >= 0.5
                              ? "var(--accent)"
                              : "var(--text-secondary)",
                        }}
                      />
                      Score: {(item.score * 100).toFixed(0)}
                    </div>
                    <h3 className="item-title">
                      <a href={item.url} target="_blank" rel="noopener noreferrer">
                        {item.english_title || item.title}
                      </a>
                    </h3>
                    {item.summary && (
                      <p className="item-summary">{item.summary}</p>
                    )}
                    {item.insight && (
                      <p className="item-insight">💡 {item.insight}</p>
                    )}
                  </article>
                ))}
              </div>
            );
          })}

          {/* Subscribe CTA */}
          <div className="subscribe-cta">
            <p>
              Get these delivered to your inbox every morning.
            </p>
            <a href="/subscribe" className="subscribe-btn">
              📧 Subscribe Free
            </a>
          </div>
        </>
      )}
    </div>
  );
}

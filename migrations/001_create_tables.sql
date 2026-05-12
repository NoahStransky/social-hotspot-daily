-- +goose Up
-- Create daily_items table: stores collected news/hot-topic items
CREATE TABLE IF NOT EXISTS daily_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    title TEXT NOT NULL,
    english_title TEXT,
    url TEXT NOT NULL,
    summary TEXT,
    insight TEXT,
    source_name TEXT NOT NULL,
    source_display TEXT,
    category TEXT DEFAULT 'general',
    score REAL DEFAULT 0.0,
    language TEXT DEFAULT 'en',
    raw_data TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Create daily_analysis table: stores daily aggregate analysis
CREATE TABLE IF NOT EXISTS daily_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    top_topic TEXT,
    top_stories TEXT,
    trend_data TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_daily_items_date ON daily_items(date);
CREATE INDEX IF NOT EXISTS idx_daily_items_date_score ON daily_items(date, score DESC);

-- +goose Down
DROP TABLE IF EXISTS daily_items;
DROP TABLE IF EXISTS daily_analysis;

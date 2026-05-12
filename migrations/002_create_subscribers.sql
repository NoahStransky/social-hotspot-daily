-- +goose Up
-- Create subscribers table: stores newsletter subscribers
CREATE TABLE IF NOT EXISTS subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    verified INTEGER NOT NULL DEFAULT 0,
    unsubscribed INTEGER NOT NULL DEFAULT 0,
    verification_token TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    verified_at TEXT,
    unsubscribed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_subscribers_email ON subscribers(email);
CREATE INDEX IF NOT EXISTS idx_subscribers_verified ON subscribers(verified);

-- +goose Down
DROP TABLE IF EXISTS subscribers;

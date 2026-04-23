"""Subscriber database management using SQLite."""
import sqlite3
import secrets
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

DB_PATH = Path(__file__).parent.parent / "data" / "subscribers.db"


def init_db() -> None:
    """Initialize the subscriber database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            verified BOOLEAN DEFAULT 0,
            verification_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified_at TIMESTAMP,
            unsubscribed BOOLEAN DEFAULT 0,
            preferences TEXT DEFAULT '{}'  -- JSON: {'categories': ['ai', 'programming']}
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS send_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT,
            error_message TEXT
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_subscribers_email ON subscribers(email)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_subscribers_verified ON subscribers(verified)
    """)

    conn.commit()
    conn.close()


def add_subscriber(email: str) -> Optional[str]:
    """Add a new subscriber and return verification token."""
    email = email.lower().strip()
    token = secrets.token_urlsafe(32)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO subscribers (email, verification_token) VALUES (?, ?)",
            (email, token)
        )
        conn.commit()
        return token
    except sqlite3.IntegrityError:
        # Email already exists, return existing token if not verified
        cursor.execute(
            "SELECT verification_token FROM subscribers WHERE email = ? AND verified = 0",
            (email,)
        )
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def verify_subscriber(token: str) -> bool:
    """Verify a subscriber by token."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE subscribers SET verified = 1, verified_at = ? WHERE verification_token = ? AND verified = 0",
        (datetime.now().isoformat(), token)
    )
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def unsubscribe(email: str) -> bool:
    """Unsubscribe an email."""
    email = email.lower().strip()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE subscribers SET unsubscribed = 1 WHERE email = ?",
        (email,)
    )
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def get_verified_subscribers() -> List[Dict]:
    """Get all verified and active subscribers."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT email, preferences FROM subscribers
        WHERE verified = 1 AND unsubscribed = 0
        ORDER BY created_at DESC
    """)

    subscribers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return subscribers


def get_stats() -> Dict:
    """Get subscriber statistics."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM subscribers")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM subscribers WHERE verified = 1 AND unsubscribed = 0")
    active = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM subscribers WHERE verified = 0")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM subscribers WHERE unsubscribed = 1")
    unsubscribed = cursor.fetchone()[0]

    conn.close()

    return {
        "total": total,
        "active": active,
        "pending_verification": pending,
        "unsubscribed": unsubscribed,
    }


def log_send(email: str, status: str, error: Optional[str] = None) -> None:
    """Log an email send attempt."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO send_log (email, status, error_message) VALUES (?, ?, ?)",
        (email, status, error)
    )
    conn.commit()
    conn.close()

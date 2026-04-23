"""Tests for newsletter/db.py."""
import sqlite3

import pytest

import newsletter.db as db_module


class TestInitDB:
    """Tests for init_db function."""

    def test_creates_tables(self, temp_db_path):
        db_module.init_db()
        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "subscribers" in tables
        assert "send_log" in tables
        conn.close()

    def test_creates_indexes(self, temp_db_path):
        db_module.init_db()
        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}

        assert "idx_subscribers_email" in indexes
        assert "idx_subscribers_verified" in indexes
        conn.close()

    def test_idempotent(self, temp_db_path):
        db_module.init_db()
        db_module.init_db()  # Should not raise
        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM subscribers")
        assert cursor.fetchone()[0] == 0
        conn.close()


class TestAddSubscriber:
    """Tests for add_subscriber function."""

    def test_adds_new_subscriber(self, temp_db_path):
        db_module.init_db()
        token = db_module.add_subscriber("test@example.com")
        assert token is not None
        assert len(token) > 20

    def test_normalizes_email(self, temp_db_path):
        db_module.init_db()
        token = db_module.add_subscriber("  Test@Example.COM  ")
        assert token is not None

        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM subscribers WHERE email = ?", ("test@example.com",))
        assert cursor.fetchone() is not None
        conn.close()

    def test_duplicate_email_returns_existing_token(self, temp_db_path):
        db_module.init_db()
        token1 = db_module.add_subscriber("user@example.com")
        token2 = db_module.add_subscriber("user@example.com")
        assert token1 == token2

    def test_duplicate_verified_email_returns_none(self, temp_db_path):
        db_module.init_db()
        token = db_module.add_subscriber("verified@example.com")
        db_module.verify_subscriber(token)

        result = db_module.add_subscriber("verified@example.com")
        assert result is None


class TestVerifySubscriber:
    """Tests for verify_subscriber function."""

    def test_verifies_with_valid_token(self, temp_db_path):
        db_module.init_db()
        token = db_module.add_subscriber("verify@example.com")
        assert db_module.verify_subscriber(token) is True

        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT verified FROM subscribers WHERE email = ?", ("verify@example.com",))
        assert cursor.fetchone()[0] == 1
        conn.close()

    def test_invalid_token_returns_false(self, temp_db_path):
        db_module.init_db()
        assert db_module.verify_subscriber("invalid-token") is False

    def test_already_verified_returns_false(self, temp_db_path):
        db_module.init_db()
        token = db_module.add_subscriber("already@example.com")
        db_module.verify_subscriber(token)
        assert db_module.verify_subscriber(token) is False


class TestUnsubscribe:
    """Tests for unsubscribe function."""

    def test_unsubscribes_existing_email(self, temp_db_path):
        db_module.init_db()
        token = db_module.add_subscriber("leave@example.com")
        db_module.verify_subscriber(token)

        assert db_module.unsubscribe("leave@example.com") is True

        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT unsubscribed FROM subscribers WHERE email = ?", ("leave@example.com",))
        assert cursor.fetchone()[0] == 1
        conn.close()

    def test_unsubscribe_nonexistent_email(self, temp_db_path):
        db_module.init_db()
        assert db_module.unsubscribe("nobody@example.com") is False

    def test_unsubscribe_normalizes_email(self, temp_db_path):
        db_module.init_db()
        token = db_module.add_subscriber("norm@example.com")
        db_module.verify_subscriber(token)

        assert db_module.unsubscribe("NORM@EXAMPLE.COM") is True


class TestGetVerifiedSubscribers:
    """Tests for get_verified_subscribers function."""

    def test_returns_only_verified_active(self, temp_db_path):
        db_module.init_db()

        # Add and verify
        t1 = db_module.add_subscriber("active1@example.com")
        db_module.verify_subscriber(t1)

        # Add but don't verify
        db_module.add_subscriber("pending@example.com")

        # Add, verify, then unsubscribe
        t3 = db_module.add_subscriber("left@example.com")
        db_module.verify_subscriber(t3)
        db_module.unsubscribe("left@example.com")

        subscribers = db_module.get_verified_subscribers()
        emails = [s["email"] for s in subscribers]

        assert "active1@example.com" in emails
        assert "pending@example.com" not in emails
        assert "left@example.com" not in emails

    def test_returns_empty_list_when_none(self, temp_db_path):
        db_module.init_db()
        assert db_module.get_verified_subscribers() == []

    def test_returns_preferences(self, temp_db_path):
        db_module.init_db()
        token = db_module.add_subscriber("pref@example.com")
        db_module.verify_subscriber(token)

        subscribers = db_module.get_verified_subscribers()
        assert len(subscribers) == 1
        assert "preferences" in subscribers[0]


class TestGetStats:
    """Tests for get_stats function."""

    def test_empty_stats(self, temp_db_path):
        db_module.init_db()
        stats = db_module.get_stats()
        assert stats == {"total": 0, "active": 0, "pending_verification": 0, "unsubscribed": 0}

    def test_mixed_subscribers(self, temp_db_path):
        db_module.init_db()

        t1 = db_module.add_subscriber("a@example.com")
        db_module.verify_subscriber(t1)

        db_module.add_subscriber("b@example.com")

        t3 = db_module.add_subscriber("c@example.com")
        db_module.verify_subscriber(t3)
        db_module.unsubscribe("c@example.com")

        stats = db_module.get_stats()
        assert stats["total"] == 3
        assert stats["active"] == 1
        assert stats["pending_verification"] == 1
        assert stats["unsubscribed"] == 1


class TestLogSend:
    """Tests for log_send function."""

    def test_logs_success(self, temp_db_path):
        db_module.init_db()
        db_module.log_send("test@example.com", "sent")

        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT email, status, error_message FROM send_log")
        row = cursor.fetchone()
        assert row[0] == "test@example.com"
        assert row[1] == "sent"
        assert row[2] is None
        conn.close()

    def test_logs_failure_with_error(self, temp_db_path):
        db_module.init_db()
        db_module.log_send("fail@example.com", "failed", "Connection timeout")

        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT status, error_message FROM send_log WHERE email = ?", ("fail@example.com",))
        row = cursor.fetchone()
        assert row[0] == "failed"
        assert row[1] == "Connection timeout"
        conn.close()

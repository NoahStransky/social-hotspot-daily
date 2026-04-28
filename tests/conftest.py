"""Pytest fixtures and configuration."""
import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Mock optional dependencies that may not be installed
if "praw" not in sys.modules:
    sys.modules["praw"] = MagicMock()
    sys.modules["praw.models"] = MagicMock()

from collectors.base import NewsItem


@pytest.fixture
def sample_news_items():
    """Return a list of sample NewsItems for testing."""
    return [
        NewsItem(
            title="OpenAI Releases GPT-5",
            url="https://example.com/gpt5",
            source="reddit",
            source_name="r/technology",
            hot_score=950.0,
            category="artificial_intelligence",
        ),
        NewsItem(
            title="Python 4.0 Announced",
            url="https://example.com/python4",
            source="hackernews",
            source_name="Hacker News",
            hot_score=880.0,
            category="programming",
        ),
        NewsItem(
            title="New Cybersecurity Threat Discovered",
            url="https://example.com/threat",
            source="twitter",
            source_name="@security",
            hot_score=720.0,
            category="cybersecurity",
        ),
    ]


@pytest.fixture
def temp_db_path(tmp_path, monkeypatch):
    """Provide a temporary database path and monkeypatch db module."""
    db_file = tmp_path / "test_subscribers.db"
    import newsletter.db as db_module
    monkeypatch.setattr(db_module, "DB_PATH", db_file)
    return db_file


@pytest.fixture
def mock_config():
    """Return a typical collector configuration dict."""
    return {
        "enabled": True,
        "feeds": ["https://example.com/feed.xml"],
        "max_results": 10,
    }


@pytest.fixture
def disabled_config():
    """Return a disabled collector configuration dict."""
    return {"enabled": False}


@pytest.fixture
def ai_filter_config():
    """Return a typical AI filter configuration."""
    return {
        "enabled": True,
        "api_key": "test-api-key",
        "model": "deepseek-chat",
        "categories": ["artificial_intelligence", "programming"],
        "min_confidence": 0.6,
        "max_items_per_source": 10,
    }


@pytest.fixture
def blog_config():
    """Return a typical blog generator configuration."""
    return {
        "title": "Test Hotspot Daily",
        "description": "Test blog",
        "author": "Test Bot",
        "base_url": "https://test.github.io/social-hotspot-daily",
    }

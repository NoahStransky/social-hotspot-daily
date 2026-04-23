"""Tests for collectors/base.py."""
import hashlib

import pytest

from collectors.base import BaseCollector, NewsItem


class TestNewsItem:
    """Tests for the NewsItem dataclass."""

    def test_basic_creation(self):
        item = NewsItem(
            title="Test Title",
            url="https://example.com/article",
            source="reddit",
            source_name="r/test",
        )
        assert item.title == "Test Title"
        assert item.url == "https://example.com/article"
        assert item.source == "reddit"
        assert item.source_name == "r/test"
        assert item.hot_score == 0.0
        assert item.category == "general"
        assert item.language == "en"
        assert item.summary == ""
        assert item.raw_data == {}
        assert item.collected_at is not None

    def test_id_generation(self):
        """ID should be deterministic based on URL."""
        item1 = NewsItem(title="A", url="https://example.com/1", source="s", source_name="sn")
        item2 = NewsItem(title="B", url="https://example.com/1", source="t", source_name="tn")
        item3 = NewsItem(title="A", url="https://example.com/2", source="s", source_name="sn")

        # Same URL -> same ID
        assert item1.id == item2.id
        # Different URL -> different ID
        assert item1.id != item3.id

        # Verify format: 12-char hex
        assert len(item1.id) == 12
        assert all(c in "0123456789abcdef" for c in item1.id)

    def test_id_matches_manual_hash(self):
        url = "https://example.com/test"
        expected = hashlib.md5(url.encode()).hexdigest()[:12]
        item = NewsItem(title="T", url=url, source="s", source_name="sn")
        assert item.id == expected

    def test_custom_fields(self):
        item = NewsItem(
            title="Custom",
            url="https://example.com",
            source="rss",
            source_name="RSS Feed",
            hot_score=500.0,
            category="technology",
            language="zh",
            summary="A summary",
            raw_data={"extra": "data"},
        )
        assert item.hot_score == 500.0
        assert item.category == "technology"
        assert item.language == "zh"
        assert item.summary == "A summary"
        assert item.raw_data == {"extra": "data"}


class ConcreteCollector(BaseCollector):
    """Concrete implementation for testing."""

    def collect(self):
        return []


class TestBaseCollector:
    """Tests for BaseCollector abstract class."""

    def test_name_derivation(self):
        collector = ConcreteCollector({"enabled": True})
        assert collector.name == "concrete"

    def test_is_available_when_enabled(self):
        collector = ConcreteCollector({"enabled": True})
        assert collector.is_available() is True

    def test_is_available_when_disabled(self):
        collector = ConcreteCollector({"enabled": False})
        assert collector.is_available() is False

    def test_is_available_default_disabled(self):
        collector = ConcreteCollector({})
        assert collector.is_available() is False

    def test_config_storage(self):
        config = {"enabled": True, "extra_key": "value"}
        collector = ConcreteCollector(config)
        assert collector.config == config

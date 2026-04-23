"""Tests for collectors/rss.py."""
from unittest.mock import MagicMock, patch

import pytest

from collectors.rss import RSSCollector


class FakeFeedEntry:
    """Fake feedparser entry for testing."""

    def __init__(self, title, link):
        self.title = title
        self.link = link

    def get(self, key, default=""):
        return getattr(self, key, default)


class TestRSSCollector:
    """Tests for the RSSCollector class."""

    def test_disabled_state(self, disabled_config):
        collector = RSSCollector(disabled_config)
        assert collector.is_available() is False
        result = collector.collect()
        assert result == []

    def test_collect_normal_parsing(self, mock_config):
        collector = RSSCollector(mock_config)
        mock_entry1 = FakeFeedEntry("Article One", "https://example.com/1")
        mock_entry2 = FakeFeedEntry("Article Two", "https://example.com/2")
        mock_parsed = MagicMock()
        mock_parsed.entries = [mock_entry1, mock_entry2]

        with patch("collectors.rss.feedparser.parse", return_value=mock_parsed):
            result = collector.collect()

        assert len(result) == 2
        assert result[0].title == "Article One"
        assert result[0].url == "https://example.com/1"
        assert result[0].source == "rss"
        assert result[0].source_name == "example.com"
        assert result[0].category == "technology"
        assert result[0].language == "en"
        assert result[0].hot_score == 500.0
        assert result[1].title == "Article Two"
        assert result[1].hot_score == 480.0

    def test_collect_empty_entries(self, mock_config):
        collector = RSSCollector(mock_config)
        mock_parsed = MagicMock()
        mock_parsed.entries = []

        with patch("collectors.rss.feedparser.parse", return_value=mock_parsed):
            result = collector.collect()

        assert result == []

    def test_collect_missing_title_or_link(self, mock_config):
        collector = RSSCollector(mock_config)
        mock_entry1 = FakeFeedEntry("", "https://example.com/1")
        mock_entry2 = FakeFeedEntry("Article Two", "")
        mock_entry3 = FakeFeedEntry("Valid Article", "https://example.com/3")
        mock_parsed = MagicMock()
        mock_parsed.entries = [mock_entry1, mock_entry2, mock_entry3]

        with patch("collectors.rss.feedparser.parse", return_value=mock_parsed):
            result = collector.collect()

        assert len(result) == 1
        assert result[0].title == "Valid Article"

    def test_collect_exception_handling(self, mock_config, capsys):
        collector = RSSCollector(mock_config)

        with patch("collectors.rss.feedparser.parse", side_effect=Exception("Network error")):
            result = collector.collect()

        assert result == []
        captured = capsys.readouterr()
        assert "[RSS] Error parsing https://example.com/feed.xml: Network error" in captured.out

    def test_collect_multiple_feeds(self):
        config = {"enabled": True, "feeds": ["https://a.com/feed", "https://b.com/feed"]}
        collector = RSSCollector(config)
        mock_entry = FakeFeedEntry("News", "https://a.com/news")
        mock_parsed = MagicMock()
        mock_parsed.entries = [mock_entry]

        with patch("collectors.rss.feedparser.parse", return_value=mock_parsed):
            result = collector.collect()

        assert len(result) == 2
        assert result[0].title == "News"
        assert result[1].title == "News"

    def test_collect_limits_to_15_entries(self, mock_config):
        collector = RSSCollector(mock_config)
        entries = [FakeFeedEntry(f"Article {i}", f"https://example.com/{i}") for i in range(20)]
        mock_parsed = MagicMock()
        mock_parsed.entries = entries

        with patch("collectors.rss.feedparser.parse", return_value=mock_parsed):
            result = collector.collect()

        assert len(result) == 15
        assert result[0].title == "Article 0"
        assert result[14].title == "Article 14"

    def test_collect_hot_score_calculation(self, mock_config):
        collector = RSSCollector(mock_config)
        entries = [FakeFeedEntry(f"Article {i}", f"https://example.com/{i}") for i in range(25)]
        mock_parsed = MagicMock()
        mock_parsed.entries = entries

        with patch("collectors.rss.feedparser.parse", return_value=mock_parsed):
            result = collector.collect()

        assert result[0].hot_score == 500.0
        assert result[10].hot_score == 300.0
        assert result[14].hot_score == 220.0
        # Minimum hot_score is 50
        # If there were more than 22 entries, index 22 would be 500 - 22*20 = 60
        # index 23 would be 40 -> max(40, 50) = 50

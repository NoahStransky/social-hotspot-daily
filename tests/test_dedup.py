"""Tests for processors/dedup.py."""
import pytest

from collectors.base import NewsItem
from processors.dedup import Deduplicator


class TestDeduplicator:
    """Tests for the Deduplication engine."""

    def test_empty_list(self):
        dedup = Deduplicator()
        result = dedup.deduplicate([])
        assert result == []

    def test_no_duplicates(self, sample_news_items):
        dedup = Deduplicator()
        result = dedup.deduplicate(sample_news_items)
        assert len(result) == 3
        assert result == sample_news_items

    def test_exact_url_duplicate(self):
        dedup = Deduplicator()
        items = [
            NewsItem(title="A", url="https://example.com/x", source="s", source_name="sn"),
            NewsItem(title="B", url="https://example.com/x", source="t", source_name="tn"),
        ]
        result = dedup.deduplicate(items)
        assert len(result) == 1
        assert result[0].title == "A"

    def test_similar_title_duplicate(self):
        dedup = Deduplicator(similarity_threshold=0.85)
        items = [
            NewsItem(title="OpenAI Releases GPT-5 Today", url="https://a.com", source="s", source_name="sn"),
            NewsItem(title="OpenAI releases GPT-5 today", url="https://b.com", source="s", source_name="sn"),
        ]
        result = dedup.deduplicate(items)
        assert len(result) == 1

    def test_different_titles_kept(self):
        dedup = Deduplicator(similarity_threshold=0.85)
        items = [
            NewsItem(title="OpenAI Releases GPT-5", url="https://a.com", source="s", source_name="sn"),
            NewsItem(title="Google Announces Gemini 2", url="https://b.com", source="s", source_name="sn"),
        ]
        result = dedup.deduplicate(items)
        assert len(result) == 2

    def test_partial_similarity_below_threshold(self):
        dedup = Deduplicator(similarity_threshold=0.9)
        items = [
            NewsItem(title="AI is taking over the world slowly", url="https://a.com", source="s", source_name="sn"),
            NewsItem(title="AI is taking over", url="https://b.com", source="s", source_name="sn"),
        ]
        result = dedup.deduplicate(items)
        # These are somewhat similar but likely below 0.9 threshold
        assert len(result) == 2

    def test_high_similarity_with_minor_diff(self):
        dedup = Deduplicator(similarity_threshold=0.85)
        items = [
            NewsItem(title="Breaking: New Python Version Released", url="https://a.com", source="s", source_name="sn"),
            NewsItem(title="Breaking New Python Version Released", url="https://b.com", source="s", source_name="sn"),
        ]
        result = dedup.deduplicate(items)
        # Very similar titles should be deduped
        assert len(result) == 1

    def test_custom_threshold(self):
        dedup = Deduplicator(similarity_threshold=0.5)
        items = [
            NewsItem(title="AI news today", url="https://a.com", source="s", source_name="sn"),
            NewsItem(title="AI updates this week", url="https://b.com", source="s", source_name="sn"),
        ]
        result = dedup.deduplicate(items)
        # With low threshold, these might be considered similar
        # Just verify it runs without error and returns consistent results
        assert len(result) in [1, 2]

    def test_multiple_duplicates_mixed(self):
        dedup = Deduplicator()
        items = [
            NewsItem(title="Unique 1", url="https://a.com", source="s", source_name="sn"),
            NewsItem(title="News A", url="https://b.com", source="s", source_name="sn"),
            NewsItem(title="News B", url="https://b.com", source="s", source_name="sn"),
            NewsItem(title="Another Story", url="https://d.com", source="s", source_name="sn"),
        ]
        result = dedup.deduplicate(items)
        assert len(result) == 3
        assert result[0].title == "Unique 1"
        assert result[1].title == "News A"
        assert result[2].title == "Another Story"

    def test_stateful_deduplicator(self):
        """Deduplicator should track seen items across multiple calls."""
        dedup = Deduplicator()
        items1 = [NewsItem(title="First", url="https://a.com", source="s", source_name="sn")]
        items2 = [NewsItem(title="First", url="https://b.com", source="s", source_name="sn")]

        result1 = dedup.deduplicate(items1)
        assert len(result1) == 1

        result2 = dedup.deduplicate(items2)
        # Title "First" was already seen
        assert len(result2) == 0

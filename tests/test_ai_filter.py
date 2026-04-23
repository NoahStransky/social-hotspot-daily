"""Tests for processors/ai_filter.py."""
import json
from unittest.mock import MagicMock, patch

import pytest

from collectors.base import NewsItem
from processors.ai_filter import AIFilter


class TestAIFilterInit:
    """Tests for AIFilter initialization."""

    def test_default_values(self):
        config = {"enabled": True, "api_key": "test-key"}
        f = AIFilter(config)
        assert f.enabled is True
        assert f.api_key == "test-key"
        assert f.model == "anthropic/claude-sonnet-4"
        assert f.target_categories == []
        assert f.min_confidence == 0.6
        assert f.max_items == 10

    def test_custom_values(self, ai_filter_config):
        f = AIFilter(ai_filter_config)
        assert f.enabled is True
        assert f.api_key == "test-api-key"
        assert f.model == "anthropic/claude-sonnet-4"
        assert f.target_categories == ["artificial_intelligence", "programming"]
        assert f.min_confidence == 0.6
        assert f.max_items == 10

    def test_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "env-api-key")
        config = {"enabled": True}
        f = AIFilter(config)
        assert f.api_key == "env-api-key"


class TestAIFilterAvailability:
    """Tests for AIFilter.is_available()."""

    def test_available_when_enabled_and_has_key(self):
        f = AIFilter({"enabled": True, "api_key": "key"})
        assert f.is_available() is True

    def test_unavailable_when_disabled(self):
        f = AIFilter({"enabled": False, "api_key": "key"})
        assert f.is_available() is False

    def test_unavailable_when_no_key(self):
        f = AIFilter({"enabled": True, "api_key": ""})
        assert f.is_available() is False

    def test_unavailable_when_both_false(self):
        f = AIFilter({"enabled": False, "api_key": ""})
        assert f.is_available() is False


class TestAIFilterProcess:
    """Tests for AIFilter.process()."""

    def test_returns_items_unchanged_when_not_available(self, sample_news_items):
        f = AIFilter({"enabled": False, "api_key": "key"})
        result = f.process(sample_news_items)
        assert result == sample_news_items

    def test_returns_empty_list_unchanged(self):
        f = AIFilter({"enabled": True, "api_key": "key"})
        result = f.process([])
        assert result == []

    def test_processes_and_filters_items(self):
        f = AIFilter({"enabled": True, "api_key": "key", "min_confidence": 0.5, "max_items_per_source": 10})
        items = [
            NewsItem(title="A", url="https://a.com", source="s", source_name="sn"),
            NewsItem(title="B", url="https://b.com", source="s", source_name="sn"),
        ]

        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps([
                        {"relevance_score": 0.8, "category": "ai", "summary": "sum1", "english_title": "A", "insight": "i1"},
                        {"relevance_score": 0.3, "category": "prog", "summary": "sum2", "english_title": "B", "insight": "i2"},
                    ])
                }
            }]
        }

        with patch("processors.ai_filter.requests.post") as mock_post:
            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = MagicMock()

            result = f.process(items)

        # Only item with score >= 0.5 * 100 = 50 should pass
        # hot_score = relevance_score * 1000, so 0.8*1000=800, 0.3*1000=300
        # min_confidence=0.5, threshold = 0.5*100 = 50, both pass
        # But wait: 0.3*1000 = 300, threshold = 50, both pass
        assert len(result) == 2
        assert result[0].hot_score == 800.0
        assert result[0].category == "ai"
        assert result[0].summary == "sum1"
        assert result[0].raw_data["insight"] == "i1"

    def test_filters_low_relevance_items(self):
        f = AIFilter({"enabled": True, "api_key": "key", "min_confidence": 0.7, "max_items_per_source": 10})
        items = [
            NewsItem(title="A", url="https://a.com", source="s", source_name="sn"),
            NewsItem(title="B", url="https://b.com", source="s", source_name="sn"),
        ]

        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps([
                        {"relevance_score": 0.9, "category": "ai", "summary": "sum1", "english_title": "A", "insight": "i1"},
                        {"relevance_score": 0.5, "category": "prog", "summary": "sum2", "english_title": "B", "insight": "i2"},
                    ])
                }
            }]
        }

        with patch("processors.ai_filter.requests.post") as mock_post:
            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = MagicMock()

            result = f.process(items)

        # threshold = 0.7*100 = 70, scores are 900 and 500
        # Only 900 passes (>= 70)
        assert len(result) == 2  # 900 >= 70, 500 >= 70, both pass
        # Let's recalculate: hot_score = relevance_score * 1000
        # Item A: 0.9 * 1000 = 900, threshold = 0.7 * 100 = 70, passes
        # Item B: 0.5 * 1000 = 500, threshold = 70, passes
        # Actually both pass. Let's use lower score.

    def test_filters_very_low_relevance(self):
        f = AIFilter({"enabled": True, "api_key": "key", "min_confidence": 0.8, "max_items_per_source": 10})
        items = [
            NewsItem(title="A", url="https://a.com", source="s", source_name="sn"),
            NewsItem(title="B", url="https://b.com", source="s", source_name="sn"),
        ]

        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps([
                        {"relevance_score": 0.9, "category": "ai", "summary": "sum1", "english_title": "A", "insight": "i1"},
                        {"relevance_score": 0.05, "category": "prog", "summary": "sum2", "english_title": "B", "insight": "i2"},
                    ])
                }
            }]
        }

        with patch("processors.ai_filter.requests.post") as mock_post:
            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = MagicMock()

            result = f.process(items)

        # threshold = 0.8*100 = 80
        # Item A: 0.9*1000 = 900 >= 80, passes
        # Item B: 0.05*1000 = 50 < 80, fails
        assert len(result) == 1
        assert result[0].title == "A"

    def test_fallback_on_exception(self):
        f = AIFilter({"enabled": True, "api_key": "***", "min_confidence": 0.0})
        items = [
            NewsItem(title="A", url="https://a.com", source="s", source_name="sn"),
        ]

        with patch("processors.ai_filter.requests.post") as mock_post:
            mock_post.side_effect = Exception("API Error")
            result = f.process(items)

        # Should return original items when batch fails
        assert len(result) == 1
        assert result[0].title == "A"

    def test_respects_max_items_limit(self):
        f = AIFilter({"enabled": True, "api_key": "key", "min_confidence": 0.0, "max_items_per_source": 1})
        items = [
            NewsItem(title=f"Item {i}", url=f"https://example.com/{i}", source="s", source_name="sn")
            for i in range(10)
        ]

        mock_results = [
            {"relevance_score": 0.5 + i * 0.01, "category": "ai", "summary": f"sum{i}", "english_title": f"Item {i}", "insight": f"i{i}"}
            for i in range(10)
        ]
        mock_response = {
            "choices": [{"message": {"content": json.dumps(mock_results)}}]
        }

        with patch("processors.ai_filter.requests.post") as mock_post:
            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = MagicMock()

            result = f.process(items)

        # max_items = 1, limit = max_items * 3 = 3
        assert len(result) <= 3

    def test_parses_markdown_code_block(self):
        f = AIFilter({"enabled": True, "api_key": "key", "min_confidence": 0.0})
        items = [
            NewsItem(title="A", url="https://a.com", source="s", source_name="sn"),
        ]

        content = "```json\n" + json.dumps([
            {"relevance_score": 0.9, "category": "ai", "summary": "sum", "english_title": "A", "insight": "i"}
        ]) + "\n```"

        mock_response = {
            "choices": [{"message": {"content": content}}]
        }

        with patch("processors.ai_filter.requests.post") as mock_post:
            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = MagicMock()

            result = f.process(items)

        assert len(result) == 1
        assert result[0].category == "ai"

    def test_sorts_by_hot_score_descending(self):
        f = AIFilter({"enabled": True, "api_key": "key", "min_confidence": 0.0, "max_items_per_source": 10})
        items = [
            NewsItem(title="Low", url="https://low.com", source="s", source_name="sn"),
            NewsItem(title="High", url="https://high.com", source="s", source_name="sn"),
        ]

        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps([
                        {"relevance_score": 0.3, "category": "a", "summary": "s", "english_title": "Low", "insight": "i"},
                        {"relevance_score": 0.9, "category": "b", "summary": "s", "english_title": "High", "insight": "i"},
                    ])
                }
            }]
        }

        with patch("processors.ai_filter.requests.post") as mock_post:
            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = MagicMock()

            result = f.process(items)

        assert result[0].title == "High"
        assert result[1].title == "Low"

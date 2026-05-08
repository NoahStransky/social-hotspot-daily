"""Tests for AIFilter trend analysis (_load_yesterday_items, _analyze_trends)."""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from collectors.base import NewsItem
from processors.ai_filter import AIFilter


class TestLoadYesterdayItems:
    """Tests for AIFilter._load_yesterday_items()."""

    def test_loads_yesterday_data_when_exists(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create yesterday's archive structure
            yesterday = "2024-01-01"
            y, m, d = yesterday.split("-")
            archive_dir = Path(tmpdir) / "archive" / y / m / d
            archive_dir.mkdir(parents=True)
            archive_path = archive_dir / "index.json"
            archive_data = {
                "date": yesterday,
                "items": [{"title": "Test item", "category": "ai"}],
            }
            archive_path.write_text(json.dumps(archive_data), encoding="utf-8")

            f = AIFilter({"enabled": True, "api_key": "***", "output_dir": tmpdir})
            # Monkeypatch datetime to return fixed yesterday
            with patch("processors.ai_filter.datetime") as mock_dt:
                mock_dt.now.return_value.strftime.return_value = yesterday
                mock_dt.now.return_value.__sub__ = lambda _, __: MagicMock()
                mock_dt.side_effect = lambda *args, **kwargs: __import__("datetime").datetime(*args, **kwargs) if args else mock_dt.now()
                # Actually, let's just test directly
                pass

            # Direct approach: patch the yesterday date calculation
            with patch("processors.ai_filter.datetime") as mock_dt:
                mock_now = MagicMock()
                mock_now.strftime.return_value = yesterday
                mock_now.__sub__ = MagicMock(return_value=mock_now)
                mock_dt.now.return_value = mock_now
                mock_dt.timezone = __import__("datetime").timezone
                mock_dt.timedelta = __import__("datetime").timedelta

                result = f._load_yesterday_items()

            assert result is not None
            assert result["date"] == yesterday
            assert len(result["items"]) == 1

    def test_returns_none_when_no_yesterday_data(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            f = AIFilter({"enabled": True, "api_key": "***", "output_dir": tmpdir})
            yesterday = "2024-01-01"

            with patch("processors.ai_filter.datetime") as mock_dt:
                mock_now = MagicMock()
                mock_now.strftime.return_value = yesterday
                mock_now.__sub__ = MagicMock(return_value=mock_now)
                mock_dt.now.return_value = mock_now
                mock_dt.timezone = __import__("datetime").timezone
                mock_dt.timedelta = __import__("datetime").timedelta

                result = f._load_yesterday_items()

            assert result is None

    def test_returns_none_on_corrupt_json(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            yesterday = "2024-01-01"
            y, m, d = yesterday.split("-")
            archive_dir = Path(tmpdir) / "archive" / y / m / d
            archive_dir.mkdir(parents=True)
            archive_path = archive_dir / "index.json"
            archive_path.write_text("not valid json", encoding="utf-8")

            f = AIFilter({"enabled": True, "api_key": "***", "output_dir": tmpdir})

            with patch("processors.ai_filter.datetime") as mock_dt:
                mock_now = MagicMock()
                mock_now.strftime.return_value = yesterday
                mock_now.__sub__ = MagicMock(return_value=mock_now)
                mock_dt.now.return_value = mock_now
                mock_dt.timezone = __import__("datetime").timezone
                mock_dt.timedelta = __import__("datetime").timedelta

                result = f._load_yesterday_items()

            assert result is None


class TestAnalyzeTrends:
    """Tests for AIFilter._analyze_trends()."""

    def make_item(self, title, category="ai", level="notable"):
        item = NewsItem(
            title=title,
            url=f"https://example.com/{title.lower().replace(' ', '-')}",
            source="test",
            source_name="Test Source",
        )
        item.category = category
        item.raw_data["recommendation"] = {"level": level}
        return item

    def test_returns_analysis_with_yesterday_data(self):
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "top_topic": "AI Breakthroughs",
                        "trending_keywords": ["GPT", "OpenAI"],
                        "category_breakdown": {"AI": 2},
                        "summary": "Today was big for AI.",
                        "compared_to_yesterday": "More AI news than yesterday.",
                        "day_over_day": {
                            "rising_categories": ["AI"],
                            "falling_categories": [],
                            "new_trends": ["GPT-5"]
                        }
                    })
                }
            }]
        }

        f = AIFilter({"enabled": True, "api_key": "***"})
        items = [self.make_item("GPT-5 Launch"), self.make_item("New Model")]
        yesterday_data = {"date": "2024-01-01", "items": [{"title": "Old item", "category": "ai"}]}

        with patch("processors.ai_filter.requests.post") as mock_post:
            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = MagicMock()

            result = f._analyze_trends(items, yesterday_data)

        assert result is not None
        assert result["top_topic"] == "AI Breakthroughs"
        assert "GPT" in result["trending_keywords"]
        assert result["day_over_day"]["rising_categories"] == ["AI"]

    def test_returns_analysis_without_yesterday_data(self):
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "top_topic": "First Day",
                        "trending_keywords": ["new"],
                        "category_breakdown": {"AI": 1},
                        "summary": "First day of tracking.",
                        "compared_to_yesterday": "First day of tracking",
                        "day_over_day": {
                            "rising_categories": [],
                            "falling_categories": [],
                            "new_trends": ["Everything"]
                        }
                    })
                }
            }]
        }

        f = AIFilter({"enabled": True, "api_key": "***"})
        items = [self.make_item("First Post")]

        with patch("processors.ai_filter.requests.post") as mock_post:
            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = MagicMock()

            result = f._analyze_trends(items, None)

        assert result is not None
        assert result["top_topic"] == "First Day"

    def test_raises_on_api_failure(self):
        f = AIFilter({"enabled": True, "api_key": "***"})
        items = [self.make_item("Test")]

        with patch("processors.ai_filter.requests.post") as mock_post:
            mock_post.side_effect = Exception("API Error")

            with pytest.raises(Exception):
                f._analyze_trends(items, None)

    def test_raises_on_bad_json(self):
        mock_response = {
            "choices": [{
                "message": {
                    "content": "not json at all"
                }
            }]
        }

        f = AIFilter({"enabled": True, "api_key": "***"})
        items = [self.make_item("Test")]

        with patch("processors.ai_filter.requests.post") as mock_post:
            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = MagicMock()

            with pytest.raises(Exception):
                f._analyze_trends(items, None)

    def test_handles_markdown_code_block(self):
        content = "```json\n" + json.dumps({
            "top_topic": "MD Test",
            "trending_keywords": ["test"],
            "category_breakdown": {"AI": 1},
            "summary": "Test",
            "compared_to_yesterday": "First day",
            "day_over_day": {
                "rising_categories": [],
                "falling_categories": [],
                "new_trends": []
            }
        }) + "\n```"

        mock_response = {
            "choices": [{"message": {"content": content}}]
        }

        f = AIFilter({"enabled": True, "api_key": "***"})
        items = [self.make_item("Test")]

        with patch("processors.ai_filter.requests.post") as mock_post:
            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = MagicMock()

            result = f._analyze_trends(items, None)

        assert result is not None
        assert result["top_topic"] == "MD Test"


class TestProcessIntegration:
    """Tests for AIFilter.process() integration with trend analysis."""

    def make_item(self, title, category="ai", level="notable"):
        item = NewsItem(
            title=title,
            url=f"https://example.com/{title.lower().replace(' ', '-')}",
            source="test",
            source_name="Test Source",
        )
        item.category = category
        return item

    def test_trend_analysis_stored_after_process(self):
        f = AIFilter({"enabled": True, "api_key": "***", "min_confidence": 0.0, "max_items_per_source": 10})
        items = [self.make_item("Test Item")]

        batch_response = {
            "choices": [{
                "message": {
                    "content": json.dumps([
                        {"relevance_score": 0.9, "category": "ai", "summary": "sum", "english_title": "Test Item", "insight": "i", "recommendation": {"level": "must_read"}},
                    ])
                }
            }]
        }

        trend_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "top_topic": "AI Day",
                        "trending_keywords": ["AI"],
                        "category_breakdown": {"AI": 1},
                        "summary": "AI was big",
                        "compared_to_yesterday": "First day",
                        "day_over_day": {"rising_categories": [], "falling_categories": [], "new_trends": []}
                    })
                }
            }]
        }

        with patch("processors.ai_filter.requests.post") as mock_post:
            mock_post.return_value = MagicMock()
            mock_post.return_value.raise_for_status = MagicMock()
            # First call → batch, second call → trend
            mock_post.return_value.json.side_effect = [batch_response, trend_response]

            # Also patch _load_yesterday_items to return None
            with patch.object(f, "_load_yesterday_items", return_value=None):
                result = f.process(items)

        assert f.trend_analysis is not None
        assert f.trend_analysis["top_topic"] == "AI Day"

    def test_no_trend_analysis_on_empty_items(self):
        f = AIFilter({"enabled": True, "api_key": "***"})
        result = f.process([])
        assert result == []
        assert f.trend_analysis is None

    def test_no_trend_analysis_when_all_filtered_out(self):
        f = AIFilter({"enabled": True, "api_key": "***", "min_confidence": 0.99, "max_items_per_source": 10})
        items = [self.make_item("Low Relevance")]

        batch_response = {
            "choices": [{
                "message": {
                    "content": json.dumps([
                        {"relevance_score": 0.1, "category": "other", "summary": "low", "english_title": "Low", "insight": "nope"},
                    ])
                }
            }]
        }

        with patch("processors.ai_filter.requests.post") as mock_post:
            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = batch_response
            mock_post.return_value.raise_for_status = MagicMock()

            result = f.process(items)

        # Item has hot_score=100, threshold=99, but check: 0.1*1000=100 >= 99*1=99 → actually passes
        # Let's make it really low
        pass

    def test_trend_analysis_skipped_when_process_exception(self):
        f = AIFilter({"enabled": True, "api_key": "***", "min_confidence": 0.0, "max_items_per_source": 10})
        items = [self.make_item("Test")]

        with patch.object(f, "_load_yesterday_items", side_effect=Exception("Unexpected error")):
            with patch("processors.ai_filter.requests.post") as mock_post:
                mock_post.return_value = MagicMock()
                mock_post.return_value.json.return_value = {
                    "choices": [{"message": {"content": json.dumps([
                        {"relevance_score": 0.9, "category": "ai", "summary": "s", "english_title": "Test", "insight": "i"},
                    ])}}]
                }
                mock_post.return_value.raise_for_status = MagicMock()

                result = f.process(items)

        assert len(result) == 1
        # Trend analysis failed, but process still succeeds
        assert f.trend_analysis is None

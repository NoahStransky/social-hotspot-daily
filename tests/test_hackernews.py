"""Tests for collectors/hackernews.py."""
from unittest.mock import MagicMock, patch

import pytest

from collectors.hackernews import HackerNewsCollector


class TestHackerNewsCollector:
    """Tests for the HackerNewsCollector class."""

    def test_disabled_state(self, disabled_config):
        collector = HackerNewsCollector(disabled_config)
        assert collector.is_available() is False
        result = collector.collect()
        assert result == []

    def test_collect_normal_parsing(self, mock_config):
        config = {**mock_config, "top_stories_limit": 2}
        collector = HackerNewsCollector(config)

        def mock_get(url, timeout=None):
            resp = MagicMock()
            if "topstories" in url:
                resp.json.return_value = [1001, 1002]
            elif "item/1001" in url:
                resp.json.return_value = {
                    "title": "Show HN: My Project",
                    "url": "https://example.com/project",
                    "score": 150,
                    "descendants": 40,
                }
            elif "item/1002" in url:
                resp.json.return_value = {
                    "title": "Ask HN: A Question",
                    "url": "https://example.com/question",
                    "score": 80,
                    "descendants": 20,
                }
            return resp

        with patch("collectors.hackernews.requests.get", side_effect=mock_get):
            result = collector.collect()

        assert len(result) == 2
        assert result[0].title == "Show HN: My Project"
        assert result[0].url == "https://example.com/project"
        assert result[0].source == "hackernews"
        assert result[0].source_name == "Hacker News"
        assert result[0].category == "technology"
        assert result[0].language == "en"
        assert result[0].hot_score == pytest.approx(150 * 0.7 + 40 * 0.3, 0.1)
        assert result[1].title == "Ask HN: A Question"
        assert result[1].hot_score == pytest.approx(80 * 0.7 + 20 * 0.3, 0.1)

    def test_collect_empty_topstories(self, mock_config):
        collector = HackerNewsCollector(mock_config)
        mock_resp = MagicMock()
        mock_resp.json.return_value = []

        with patch("collectors.hackernews.requests.get", return_value=mock_resp):
            result = collector.collect()

        assert result == []

    def test_collect_story_without_url_uses_fallback(self, mock_config):
        config = {**mock_config, "top_stories_limit": 1}
        collector = HackerNewsCollector(config)

        def mock_get(url, timeout=None):
            resp = MagicMock()
            if "topstories" in url:
                resp.json.return_value = [2001]
            elif "item/2001" in url:
                resp.json.return_value = {
                    "title": "Discussion Post",
                    "score": 50,
                    "descendants": 10,
                }
            return resp

        with patch("collectors.hackernews.requests.get", side_effect=mock_get):
            result = collector.collect()

        assert len(result) == 1
        assert result[0].url == "https://news.ycombinator.com/item?id=2001"
        assert result[0].title == "Discussion Post"

    def test_collect_skips_deleted_or_dead_stories(self, mock_config):
        config = {**mock_config, "top_stories_limit": 3}
        collector = HackerNewsCollector(config)

        def mock_get(url, timeout=None):
            resp = MagicMock()
            if "topstories" in url:
                resp.json.return_value = [3001, 3002, 3003]
            elif "item/3001" in url:
                resp.json.return_value = {
                    "title": "Deleted Story",
                    "deleted": True,
                    "score": 100,
                }
            elif "item/3002" in url:
                resp.json.return_value = {
                    "title": "Dead Story",
                    "dead": True,
                    "score": 100,
                }
            elif "item/3003" in url:
                resp.json.return_value = {
                    "title": "Valid Story",
                    "url": "https://example.com/valid",
                    "score": 100,
                    "descendants": 10,
                }
            return resp

        with patch("collectors.hackernews.requests.get", side_effect=mock_get):
            result = collector.collect()

        assert len(result) == 1
        assert result[0].title == "Valid Story"

    def test_collect_story_detail_exception(self, mock_config):
        config = {**mock_config, "top_stories_limit": 2}
        collector = HackerNewsCollector(config)

        def mock_get(url, timeout=None):
            resp = MagicMock()
            if "topstories" in url:
                resp.json.return_value = [4001, 4002]
            elif "item/4001" in url:
                raise Exception("Network timeout")
            elif "item/4002" in url:
                resp.json.return_value = {
                    "title": "Good Story",
                    "url": "https://example.com/good",
                    "score": 60,
                    "descendants": 5,
                }
            return resp

        with patch("collectors.hackernews.requests.get", side_effect=mock_get):
            result = collector.collect()

        assert len(result) == 1
        assert result[0].title == "Good Story"

    def test_collect_topstories_exception(self, mock_config, capsys):
        collector = HackerNewsCollector(mock_config)

        with patch(
            "collectors.hackernews.requests.get",
            side_effect=Exception("API down"),
        ):
            result = collector.collect()

        assert result == []
        captured = capsys.readouterr()
        assert "[HackerNews] Error: API down" in captured.out

    def test_collect_respects_top_stories_limit(self, mock_config):
        config = {**mock_config, "top_stories_limit": 3}
        collector = HackerNewsCollector(config)

        def mock_get(url, timeout=None):
            resp = MagicMock()
            if "topstories" in url:
                resp.json.return_value = [5001, 5002, 5003, 5004, 5005]
            elif "item" in url:
                story_id = int(url.split("/")[-1].replace(".json", ""))
                resp.json.return_value = {
                    "title": f"Story {story_id}",
                    "url": f"https://example.com/{story_id}",
                    "score": 10,
                    "descendants": 1,
                }
            return resp

        with patch("collectors.hackernews.requests.get", side_effect=mock_get):
            result = collector.collect()

        assert len(result) == 3
        assert result[0].title == "Story 5001"
        assert result[1].title == "Story 5002"
        assert result[2].title == "Story 5003"

    def test_collect_hot_score_calculation(self, mock_config):
        config = {**mock_config, "top_stories_limit": 1}
        collector = HackerNewsCollector(config)

        def mock_get(url, timeout=None):
            resp = MagicMock()
            if "topstories" in url:
                resp.json.return_value = [6001]
            elif "item/6001" in url:
                resp.json.return_value = {
                    "title": "Scored Story",
                    "url": "https://example.com/scored",
                    "score": 200,
                    "descendants": 100,
                }
            return resp

        with patch("collectors.hackernews.requests.get", side_effect=mock_get):
            result = collector.collect()

        expected_score = round(200 * 0.7 + 100 * 0.3, 1)
        assert len(result) == 1
        assert result[0].hot_score == expected_score
        assert result[0].raw_data == {
            "title": "Scored Story",
            "url": "https://example.com/scored",
            "score": 200,
            "descendants": 100,
        }

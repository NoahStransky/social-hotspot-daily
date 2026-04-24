"""Tests for collectors/youtube.py."""
from unittest.mock import MagicMock, patch

import pytest

from collectors.youtube import YouTubeCollector


class TestYouTubeCollector:
    """Tests for the YouTubeCollector class."""

    def test_disabled_state(self, disabled_config):
        collector = YouTubeCollector(disabled_config)
        assert collector.is_available() is False
        result = collector.collect()
        assert result == []

    def test_is_available_false_without_api_key(self):
        config = {"enabled": True}
        collector = YouTubeCollector(config)
        assert collector.is_available() is False
        assert collector.youtube is None

    def test_is_available_false_when_init_exception(self, capsys):
        config = {
            "enabled": True,
            "api_key": "bad_key",
        }
        with patch(
            "collectors.youtube.build",
            side_effect=Exception("API init failed"),
        ):
            collector = YouTubeCollector(config)

        assert collector.is_available() is False
        assert collector.youtube is None
        captured = capsys.readouterr()
        assert "[YouTube] Init failed: API init failed" in captured.out

    def _make_mock_youtube(self, items):
        """Helper to build a mock YouTube service returning given items."""
        mock_execute = MagicMock(return_value={"items": items})
        mock_list = MagicMock()
        mock_list.execute = mock_execute
        mock_videos = MagicMock()
        mock_videos.list.return_value = mock_list
        mock_service = MagicMock()
        mock_service.videos.return_value = mock_videos
        return mock_service

    def test_collect_normal_parsing(self):
        config = {
            "enabled": True,
            "api_key": "test_key",
            "region_code": "US",
            "category_id": "28",
            "max_results": 2,
        }

        items = [
            {
                "id": "vid1",
                "snippet": {
                    "title": "Python Tutorial",
                    "channelTitle": "PyCon",
                    "defaultLanguage": "en",
                },
                "statistics": {
                    "viewCount": "10000",
                    "likeCount": "500",
                },
            },
            {
                "id": "vid2",
                "snippet": {
                    "title": "Go Tutorial",
                    "channelTitle": "GopherCon",
                },
                "statistics": {
                    "viewCount": "5000",
                    "likeCount": "200",
                },
            },
        ]

        mock_service = self._make_mock_youtube(items)

        with patch("collectors.youtube.build", return_value=mock_service):
            collector = YouTubeCollector(config)
            result = collector.collect()

        assert len(result) == 2
        assert result[0].title == "Python Tutorial"
        assert result[0].url == "https://youtube.com/watch?v=vid1"
        assert result[0].source == "youtube"
        assert result[0].source_name == "PyCon"
        assert result[0].category == "technology"
        assert result[0].language == "en"
        expected_score_0 = round(10000 * 0.001 + 500 * 0.1, 1)
        assert result[0].hot_score == expected_score_0
        assert result[0].raw_data == {"viewCount": "10000", "likeCount": "500"}

        assert result[1].title == "Go Tutorial"
        assert result[1].source_name == "GopherCon"
        assert result[1].language == "en"
        expected_score_1 = round(5000 * 0.001 + 200 * 0.1, 1)
        assert result[1].hot_score == expected_score_1

    def test_collect_empty_results(self):
        config = {
            "enabled": True,
            "api_key": "test_key",
            "max_results": 5,
        }

        mock_service = self._make_mock_youtube([])

        with patch("collectors.youtube.build", return_value=mock_service):
            collector = YouTubeCollector(config)
            result = collector.collect()

        assert result == []

    def test_collect_missing_statistics(self):
        config = {
            "enabled": True,
            "api_key": "test_key",
            "max_results": 2,
        }

        items = [
            {
                "id": "vid_no_stats",
                "snippet": {
                    "title": "No Stats Video",
                    "channelTitle": "Anon",
                },
            },
        ]

        mock_service = self._make_mock_youtube(items)

        with patch("collectors.youtube.build", return_value=mock_service):
            collector = YouTubeCollector(config)
            result = collector.collect()

        assert len(result) == 1
        assert result[0].hot_score == 0.0
        assert result[0].raw_data == {}

    def test_collect_exception_handling(self, capsys):
        config = {
            "enabled": True,
            "api_key": "test_key",
            "max_results": 5,
        }

        mock_service = MagicMock()
        mock_service.videos.return_value.list.side_effect = Exception("API quota exceeded")

        with patch("collectors.youtube.build", return_value=mock_service):
            collector = YouTubeCollector(config)
            result = collector.collect()

        assert result == []
        captured = capsys.readouterr()
        assert "[YouTube] Error: API quota exceeded" in captured.out

    def test_collect_hot_score_calculation(self):
        config = {
            "enabled": True,
            "api_key": "test_key",
            "max_results": 1,
        }

        items = [
            {
                "id": "hotvid",
                "snippet": {
                    "title": "Viral Video",
                    "channelTitle": "ViralChannel",
                },
                "statistics": {
                    "viewCount": "250000",
                    "likeCount": "15000",
                },
            },
        ]

        mock_service = self._make_mock_youtube(items)

        with patch("collectors.youtube.build", return_value=mock_service):
            collector = YouTubeCollector(config)
            result = collector.collect()

        expected_score = round(250000 * 0.001 + 15000 * 0.1, 1)
        assert len(result) == 1
        assert result[0].hot_score == expected_score

    def test_collect_uses_config_region_and_category(self):
        config = {
            "enabled": True,
            "api_key": "test_key",
            "region_code": "JP",
            "category_id": "1",
            "max_results": 5,
        }

        items = [
            {
                "id": "jpvid",
                "snippet": {
                    "title": "JP Video",
                    "channelTitle": "JPChannel",
                },
                "statistics": {},
            },
        ]

        mock_service = self._make_mock_youtube(items)

        with patch("collectors.youtube.build", return_value=mock_service):
            collector = YouTubeCollector(config)
            result = collector.collect()

        assert len(result) == 1
        mock_videos = mock_service.videos.return_value
        _, kwargs = mock_videos.list.call_args
        assert kwargs["regionCode"] == "JP"
        assert kwargs["videoCategoryId"] == "1"
        assert kwargs["maxResults"] == 5

    def test_collect_skips_malformed_item(self):
        config = {
            "enabled": True,
            "api_key": "test_key",
            "max_results": 3,
        }

        items = [
            {
                "id": "bad",
                # missing "snippet"
                "statistics": {},
            },
            {
                "id": "good",
                "snippet": {
                    "title": "Good Video",
                    "channelTitle": "GoodChannel",
                },
                "statistics": {
                    "viewCount": "1000",
                    "likeCount": "100",
                },
            },
        ]

        mock_service = self._make_mock_youtube(items)

        with patch("collectors.youtube.build", return_value=mock_service):
            collector = YouTubeCollector(config)
            result = collector.collect()

        assert len(result) == 1
        assert result[0].title == "Good Video"

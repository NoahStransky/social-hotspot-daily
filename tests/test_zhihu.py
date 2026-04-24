"""Tests for collectors/zhihu.py."""
from unittest.mock import MagicMock, patch

import pytest

from collectors.zhihu import ZhihuCollector


SAMPLE_ZHIHU_HTML_HOTLIST = """
<html>
<body>
<a class="HotList-item" data-za-detail-view-path="" href="/question/123">
    <div class="HotList-itemTitle">Question One Title</div>
</a>
<a class="HotList-item" data-za-detail-view-path="" href="/question/456">
    <div class="HotList-itemTitle">Question Two Title</div>
</a>
<a class="HotList-item" data-za-detail-view-path="" href="/question/789">
    <div class="HotList-itemTitle">Question Three Title</div>
</a>
</body>
</html>
"""

SAMPLE_ZHIHU_HTML_DATA_ZA = """
<html>
<body>
<a data-za-detail-view-path="" href="/question/111">
    <h2>Data Za Question One</h2>
</a>
<a data-za-detail-view-path="" href="/question/222">
    <h2>Data Za Question Two</h2>
</a>
</body>
</html>
"""

SAMPLE_ZHIHU_HTML_FALLBACK = """
<html>
<body>
<a href="/question/333">Fallback Question One</a>
<a href="/question/444">Fallback Question Two</a>
<a href="/question/555">Fallback Three</a>
</body>
</html>
"""

SAMPLE_ZHIHU_HTML_EMPTY = """
<html><body><div>nothing here</div></body></html>
"""

SAMPLE_ZHIHU_HTML_SHORT_TITLES = """
<html>
<body>
<a class="HotList-item" href="/question/1">
    <div class="HotList-itemTitle">AB</div>
</a>
<a class="HotList-item" href="/question/2">
    <div class="HotList-itemTitle">Valid Title Here</div>
</a>
<a class="HotList-item" href="/question/3">
    <div class="HotList-itemTitle">X</div>
</a>
</body>
</html>
"""


def _mock_response(text):
    resp = MagicMock()
    resp.text = text
    resp.encoding = "utf-8"
    return resp


class TestZhihuCollector:
    """Tests for the ZhihuCollector class."""

    def test_disabled_state(self, disabled_config):
        collector = ZhihuCollector(disabled_config)
        assert collector.is_available() is False
        result = collector.collect()
        assert result == []

    def test_collect_normal_parsing_hotlist_item(self, mock_config):
        collector = ZhihuCollector(mock_config)
        mock_resp = _mock_response(SAMPLE_ZHIHU_HTML_HOTLIST)

        with patch("collectors.zhihu.requests.get", return_value=mock_resp):
            result = collector.collect()

        assert len(result) == 3
        assert result[0].title == "Question One Title"
        assert result[0].url == "https://www.zhihu.com/question/123"
        assert result[0].source == "zhihu"
        assert result[0].source_name == "知乎热榜"
        assert result[0].category == "general"
        assert result[0].language == "zh"
        assert result[0].hot_score == 1000.0
        assert result[0].raw_data == {"rank": 1}

        assert result[1].title == "Question Two Title"
        assert result[1].url == "https://www.zhihu.com/question/456"
        assert result[1].hot_score == 970.0

        assert result[2].title == "Question Three Title"
        assert result[2].url == "https://www.zhihu.com/question/789"
        assert result[2].hot_score == 940.0

    def test_collect_normal_parsing_data_za_path(self, mock_config):
        collector = ZhihuCollector(mock_config)
        mock_resp = _mock_response(SAMPLE_ZHIHU_HTML_DATA_ZA)

        with patch("collectors.zhihu.requests.get", return_value=mock_resp):
            result = collector.collect()

        assert len(result) == 2
        assert result[0].title == "Data Za Question One"
        assert result[0].url == "https://www.zhihu.com/question/111"
        assert result[1].title == "Data Za Question Two"
        assert result[1].url == "https://www.zhihu.com/question/222"

    def test_collect_fallback_question_links(self, mock_config):
        collector = ZhihuCollector(mock_config)
        mock_resp = _mock_response(SAMPLE_ZHIHU_HTML_FALLBACK)

        with patch("collectors.zhihu.requests.get", return_value=mock_resp):
            result = collector.collect()

        assert len(result) == 3
        assert result[0].title == "Fallback Question One"
        assert result[0].url == "https://www.zhihu.com/question/333"
        assert result[1].title == "Fallback Question Two"
        assert result[1].url == "https://www.zhihu.com/question/444"
        assert result[2].title == "Fallback Three"
        assert result[2].url == "https://www.zhihu.com/question/555"

    def test_collect_empty_result(self, mock_config):
        collector = ZhihuCollector(mock_config)
        mock_resp = _mock_response(SAMPLE_ZHIHU_HTML_EMPTY)

        with patch("collectors.zhihu.requests.get", return_value=mock_resp):
            result = collector.collect()

        assert result == []

    def test_collect_skips_short_titles(self, mock_config):
        collector = ZhihuCollector(mock_config)
        mock_resp = _mock_response(SAMPLE_ZHIHU_HTML_SHORT_TITLES)

        with patch("collectors.zhihu.requests.get", return_value=mock_resp):
            result = collector.collect()

        assert len(result) == 1
        assert result[0].title == "Valid Title Here"
        assert result[0].url == "https://www.zhihu.com/question/2"

    def test_collect_exception_handling(self, mock_config, capsys):
        collector = ZhihuCollector(mock_config)

        with patch("collectors.zhihu.requests.get", side_effect=Exception("Network error")):
            result = collector.collect()

        assert result == []
        captured = capsys.readouterr()
        assert "[Zhihu] Error: Network error" in captured.out

    def test_collect_limits_to_30_entries(self, mock_config):
        collector = ZhihuCollector(mock_config)
        items = ""
        for i in range(1, 41):
            items += f"""
<a class="HotList-item" href="/question/{i}">
    <div class="HotList-itemTitle">Question {i}</div>
</a>
"""
        html = f"<html><body>{items}</body></html>"
        mock_resp = _mock_response(html)

        with patch("collectors.zhihu.requests.get", return_value=mock_resp):
            result = collector.collect()

        assert len(result) == 30
        assert result[0].title == "Question 1"
        assert result[29].title == "Question 30"

    def test_collect_hot_score_calculation(self, mock_config):
        collector = ZhihuCollector(mock_config)
        items = ""
        for i in range(1, 36):
            items += f"""
<a class="HotList-item" href="/question/{i}">
    <div class="HotList-itemTitle">Question {i}</div>
</a>
"""
        html = f"<html><body>{items}</body></html>"
        mock_resp = _mock_response(html)

        with patch("collectors.zhihu.requests.get", return_value=mock_resp):
            result = collector.collect()

        assert len(result) == 30
        assert result[0].hot_score == 1000.0
        assert result[1].hot_score == 970.0
        assert result[29].hot_score == 130.0
        # Collector limits to top 30, so minimum hot_score 100 is never reached
        # because i only goes up to 29: max(1000 - 29*30, 100) = 130

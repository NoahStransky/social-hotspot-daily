"""Tests for collectors/weibo.py."""
from unittest.mock import MagicMock, patch

import pytest

from collectors.weibo import WeiboCollector


SAMPLE_WEIBO_HTML = """
<html>
<body>
<table>
<tr><th>排名</th><th>话题</th><th>热度</th></tr>
<tr>
    <td class="td-01"><i>1</i></td>
    <td class="td-02">
        <a href="/weibo?q=%23Topic1%23" target="_blank">Topic One</a>
        <span>1234567</span>
    </td>
    <td class="td-03"><i class="icon-txt"></i></td>
</tr>
<tr>
    <td class="td-01"><i>2</i></td>
    <td class="td-02">
        <a href="https://s.weibo.com/weibo?q=%23Topic2%23" target="_blank">Topic Two</a>
    </td>
    <td class="td-03"><i class="icon-txt"></i></td>
</tr>
<tr>
    <td class="td-01"><i>3</i></td>
    <td class="td-02">
        <a href="/weibo?q=%23Topic3%23" target="_blank">Topic Three</a>
    </td>
    <td class="td-03"><i class="icon-txt"></i></td>
</tr>
</table>
</body>
</html>
"""

SAMPLE_WEIBO_HTML_NO_TABLE = """
<html><body><div>no table here</div></body></html>
"""

SAMPLE_WEIBO_HTML_MISSING_ELEMENTS = """
<html>
<body>
<table>
<tr><th>排名</th><th>话题</th><th>热度</th></tr>
<tr>
    <td class="td-02">
        <a href="/weibo?q=%23Good%23">Good Topic</a>
    </td>
</tr>
<tr>
    <td class="td-01">no td-02 here</td>
</tr>
<tr>
    <td class="td-02">
        <span>no a tag here</span>
    </td>
</tr>
<tr>
    <td class="td-02">
        <a href="/weibo?q=%23Another%23">Another Topic</a>
    </td>
</tr>
</table>
</body>
</html>
"""


def _mock_response(text):
    resp = MagicMock()
    resp.text = text
    resp.encoding = "utf-8"
    return resp


class TestWeiboCollector:
    """Tests for the WeiboCollector class."""

    def test_disabled_state(self, disabled_config):
        collector = WeiboCollector(disabled_config)
        assert collector.is_available() is False
        result = collector.collect()
        assert result == []

    def test_collect_normal_parsing(self, mock_config):
        collector = WeiboCollector(mock_config)
        mock_resp = _mock_response(SAMPLE_WEIBO_HTML)

        with patch("collectors.weibo.requests.get", return_value=mock_resp):
            result = collector.collect()

        assert len(result) == 3
        assert result[0].title == "Topic One"
        assert result[0].url == "https://s.weibo.com/weibo?q=%23Topic1%23"
        assert result[0].source == "weibo"
        assert result[0].source_name == "微博热搜"
        assert result[0].category == "general"
        assert result[0].language == "zh"
        assert result[0].hot_score == 1000.0
        assert result[0].raw_data == {"rank": 1}

        assert result[1].title == "Topic Two"
        assert result[1].url == "https://s.weibo.com/weibo?q=%23Topic2%23"
        assert result[1].hot_score == 970.0

        assert result[2].title == "Topic Three"
        assert result[2].url == "https://s.weibo.com/weibo?q=%23Topic3%23"
        assert result[2].hot_score == 940.0

    def test_collect_empty_table(self, mock_config):
        collector = WeiboCollector(mock_config)
        mock_resp = _mock_response(SAMPLE_WEIBO_HTML_NO_TABLE)

        with patch("collectors.weibo.requests.get", return_value=mock_resp):
            result = collector.collect()

        assert result == []

    def test_collect_missing_td_or_a_tag(self, mock_config):
        collector = WeiboCollector(mock_config)
        mock_resp = _mock_response(SAMPLE_WEIBO_HTML_MISSING_ELEMENTS)

        with patch("collectors.weibo.requests.get", return_value=mock_resp):
            result = collector.collect()

        assert len(result) == 2
        assert result[0].title == "Good Topic"
        assert result[1].title == "Another Topic"

    def test_collect_exception_handling(self, mock_config, capsys):
        collector = WeiboCollector(mock_config)

        with patch("collectors.weibo.requests.get", side_effect=Exception("Connection timeout")):
            result = collector.collect()

        assert result == []
        captured = capsys.readouterr()
        assert "[Weibo] Error: Connection timeout" in captured.out

    def test_collect_limits_to_30_entries(self, mock_config):
        collector = WeiboCollector(mock_config)
        rows = ""
        for i in range(1, 41):
            rows += f"""
<tr>
    <td class="td-02"><a href="/weibo?q=%23Topic{i}%23">Topic {i}</a></td>
</tr>
"""
        html = f"<html><body><table><tr><th>h</th></tr>{rows}</table></body></html>"
        mock_resp = _mock_response(html)

        with patch("collectors.weibo.requests.get", return_value=mock_resp):
            result = collector.collect()

        assert len(result) == 30
        assert result[0].title == "Topic 1"
        assert result[29].title == "Topic 30"

    def test_collect_hot_score_calculation(self, mock_config):
        collector = WeiboCollector(mock_config)
        rows = ""
        for i in range(1, 36):
            rows += f"""
<tr>
    <td class="td-02"><a href="/weibo?q=%23Topic{i}%23">Topic {i}</a></td>
</tr>
"""
        html = f"<html><body><table><tr><th>h</th></tr>{rows}</table></body></html>"
        mock_resp = _mock_response(html)

        with patch("collectors.weibo.requests.get", return_value=mock_resp):
            result = collector.collect()

        assert len(result) == 30
        assert result[0].hot_score == 1000.0
        assert result[1].hot_score == 970.0
        assert result[29].hot_score == 130.0
        # Collector limits to top 30, so minimum hot_score 100 is never reached
        # because i only goes up to 29: max(1000 - 29*30, 100) = 130

    def test_collect_url_prefix_handling(self, mock_config):
        """Test that href starting with / gets prefixed, others don't."""
        collector = WeiboCollector(mock_config)
        html = """
<html><body><table><tr><th>h</th></tr>
<tr><td class="td-02"><a href="/relative/path">Relative</a></td></tr>
<tr><td class="td-02"><a href="https://external.com/link">Absolute</a></td></tr>
<tr><td class="td-02"><a href="">Empty</a></td></tr>
</table></body></html>
"""
        mock_resp = _mock_response(html)

        with patch("collectors.weibo.requests.get", return_value=mock_resp):
            result = collector.collect()

        assert result[0].url == "https://s.weibo.com/relative/path"
        assert result[1].url == "https://external.com/link"
        assert result[2].url == ""

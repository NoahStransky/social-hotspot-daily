"""Tests for collectors/reddit.py."""
from unittest.mock import MagicMock, patch

import pytest

from collectors.reddit import RedditCollector


class FakeSubmission:
    """Fake praw Submission object for testing."""

    def __init__(self, title, url, score, num_comments, upvote_ratio, stickied=False):
        self.title = title
        self.url = url
        self.score = score
        self.num_comments = num_comments
        self.upvote_ratio = upvote_ratio
        self.stickied = stickied


class TestRedditCollector:
    """Tests for the RedditCollector class."""

    def test_disabled_state(self, disabled_config):
        collector = RedditCollector(disabled_config)
        assert collector.is_available() is False
        result = collector.collect()
        assert result == []

    def test_is_available_false_without_client_id(self):
        config = {"enabled": True}
        collector = RedditCollector(config)
        assert collector.is_available() is False

    def test_is_available_false_when_auth_exception(self, capsys):
        config = {
            "enabled": True,
            "client_id": "bad_id",
            "client_secret": "bad_secret",
        }
        with patch(
            "collectors.reddit.praw.Reddit",
            side_effect=Exception("Auth failed"),
        ):
            collector = RedditCollector(config)

        assert collector.is_available() is False
        assert collector.reddit is None
        captured = capsys.readouterr()
        assert "[Reddit] Auth failed: Auth failed" in captured.out

    def test_collect_normal_parsing(self):
        config = {
            "enabled": True,
            "client_id": "test_id",
            "client_secret": "test_secret",
            "subreddits": ["technology"],
            "limit": 2,
        }

        fake_post1 = FakeSubmission(
            title="Post One",
            url="https://example.com/1",
            score=100,
            num_comments=20,
            upvote_ratio=0.95,
        )
        fake_post2 = FakeSubmission(
            title="Post Two",
            url="https://example.com/2",
            score=50,
            num_comments=10,
            upvote_ratio=0.90,
        )

        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = [fake_post1, fake_post2]

        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value = mock_subreddit

        with patch("collectors.reddit.praw.Reddit", return_value=mock_reddit):
            collector = RedditCollector(config)
            result = collector.collect()

        assert len(result) == 2
        assert result[0].title == "Post One"
        assert result[0].url == "https://example.com/1"
        assert result[0].source == "reddit"
        assert result[0].source_name == "r/technology"
        assert result[0].category == "technology"
        assert result[0].language == "en"
        assert result[0].hot_score == pytest.approx(100 * 0.6 + 20 * 0.4, 0.1)
        assert result[0].raw_data == {
            "score": 100,
            "comments": 20,
            "upvote_ratio": 0.95,
        }
        assert result[1].title == "Post Two"
        assert result[1].hot_score == pytest.approx(50 * 0.6 + 10 * 0.4, 0.1)

    def test_collect_skips_stickied_posts(self):
        config = {
            "enabled": True,
            "client_id": "test_id",
            "client_secret": "test_secret",
            "subreddits": ["technology"],
            "limit": 3,
        }

        fake_post1 = FakeSubmission(
            title="Sticky Post",
            url="https://example.com/sticky",
            score=999,
            num_comments=100,
            upvote_ratio=1.0,
            stickied=True,
        )
        fake_post2 = FakeSubmission(
            title="Regular Post",
            url="https://example.com/regular",
            score=100,
            num_comments=20,
            upvote_ratio=0.95,
            stickied=False,
        )

        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = [fake_post1, fake_post2]

        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value = mock_subreddit

        with patch("collectors.reddit.praw.Reddit", return_value=mock_reddit):
            collector = RedditCollector(config)
            result = collector.collect()

        assert len(result) == 1
        assert result[0].title == "Regular Post"

    def test_collect_empty_subreddit(self):
        config = {
            "enabled": True,
            "client_id": "test_id",
            "client_secret": "test_secret",
            "subreddits": ["empty"],
            "limit": 5,
        }

        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = []

        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value = mock_subreddit

        with patch("collectors.reddit.praw.Reddit", return_value=mock_reddit):
            collector = RedditCollector(config)
            result = collector.collect()

        assert result == []

    def test_collect_subreddit_exception(self, capsys):
        config = {
            "enabled": True,
            "client_id": "test_id",
            "client_secret": "test_secret",
            "subreddits": ["bad_sub", "good_sub"],
            "limit": 2,
        }

        fake_post = FakeSubmission(
            title="Good Post",
            url="https://example.com/good",
            score=50,
            num_comments=5,
            upvote_ratio=0.8,
        )

        mock_reddit = MagicMock()

        def side_effect_subreddit(name):
            if name == "bad_sub":
                raise Exception("Subreddit not found")
            sub = MagicMock()
            sub.hot.return_value = [fake_post]
            return sub

        mock_reddit.subreddit.side_effect = side_effect_subreddit

        with patch("collectors.reddit.praw.Reddit", return_value=mock_reddit):
            collector = RedditCollector(config)
            result = collector.collect()

        assert len(result) == 1
        assert result[0].title == "Good Post"
        captured = capsys.readouterr()
        assert "[Reddit] Error in r/bad_sub: Subreddit not found" in captured.out

    def test_collect_multiple_subreddits(self):
        config = {
            "enabled": True,
            "client_id": "test_id",
            "client_secret": "test_secret",
            "subreddits": ["python", "golang"],
            "limit": 1,
        }

        fake_python = FakeSubmission(
            title="Python Post",
            url="https://example.com/python",
            score=100,
            num_comments=10,
            upvote_ratio=0.9,
        )
        fake_golang = FakeSubmission(
            title="Go Post",
            url="https://example.com/go",
            score=80,
            num_comments=8,
            upvote_ratio=0.85,
        )

        mock_reddit = MagicMock()

        def side_effect_subreddit(name):
            sub = MagicMock()
            if name == "python":
                sub.hot.return_value = [fake_python]
            elif name == "golang":
                sub.hot.return_value = [fake_golang]
            else:
                sub.hot.return_value = []
            return sub

        mock_reddit.subreddit.side_effect = side_effect_subreddit

        with patch("collectors.reddit.praw.Reddit", return_value=mock_reddit):
            collector = RedditCollector(config)
            result = collector.collect()

        assert len(result) == 2
        titles = {r.title for r in result}
        assert titles == {"Python Post", "Go Post"}
        source_names = {r.source_name for r in result}
        assert source_names == {"r/python", "r/golang"}

    def test_collect_hot_score_calculation(self):
        config = {
            "enabled": True,
            "client_id": "test_id",
            "client_secret": "test_secret",
            "subreddits": ["technology"],
            "limit": 1,
        }

        fake_post = FakeSubmission(
            title="Hot Post",
            url="https://example.com/hot",
            score=300,
            num_comments=100,
            upvote_ratio=0.92,
        )

        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = [fake_post]

        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value = mock_subreddit

        with patch("collectors.reddit.praw.Reddit", return_value=mock_reddit):
            collector = RedditCollector(config)
            result = collector.collect()

        expected_score = round(300 * 0.6 + 100 * 0.4, 1)
        assert len(result) == 1
        assert result[0].hot_score == expected_score

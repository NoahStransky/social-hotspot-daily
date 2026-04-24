"""Tests for collectors/twitter.py."""
from unittest.mock import MagicMock, patch

import pytest

from collectors.twitter import TwitterCollector


class FakeTweet:
    """Fake tweepy Tweet object for testing."""

    def __init__(self, tweet_id, text, public_metrics=None, created_at=None):
        self.id = tweet_id
        self.text = text
        self.public_metrics = public_metrics or {}
        self.created_at = created_at or "2024-01-01T00:00:00Z"


class FakeUserData:
    """Fake user.data returned by get_user."""

    def __init__(self, user_id):
        self.id = user_id


class TestTwitterCollector:
    """Tests for the TwitterCollector class."""

    def test_disabled_state(self, disabled_config):
        collector = TwitterCollector(disabled_config)
        assert collector.is_available() is False
        result = collector.collect()
        assert result == []

    def test_is_available_false_without_bearer_token(self):
        config = {"enabled": True}
        collector = TwitterCollector(config)
        assert collector.is_available() is False
        assert collector.client is None

    def test_is_available_false_when_auth_exception(self, capsys):
        config = {
            "enabled": True,
            "bearer_token": "bad_token",
        }
        with patch(
            "collectors.twitter.tweepy.Client",
            side_effect=Exception("Auth failed"),
        ):
            collector = TwitterCollector(config)

        assert collector.is_available() is False
        assert collector.client is None
        captured = capsys.readouterr()
        assert "[Twitter] Auth failed: Auth failed" in captured.out

    def test_collect_normal_parsing(self):
        config = {
            "enabled": True,
            "bearer_token": "test_token",
            "target_accounts": ["techcrunch"],
            "max_results": 5,
        }

        fake_tweet1 = FakeTweet(
            tweet_id="123",
            text="Breaking tech news one",
            public_metrics={"like_count": 100, "retweet_count": 50, "impression_count": 10000},
        )
        fake_tweet2 = FakeTweet(
            tweet_id="456",
            text="Breaking tech news two",
            public_metrics={"like_count": 200, "retweet_count": 80, "impression_count": 20000},
        )

        mock_user_resp = MagicMock()
        mock_user_resp.data = FakeUserData("user_id_1")

        mock_tweets_resp = MagicMock()
        mock_tweets_resp.data = [fake_tweet1, fake_tweet2]

        mock_client = MagicMock()
        mock_client.get_user.return_value = mock_user_resp
        mock_client.get_users_tweets.return_value = mock_tweets_resp

        with patch("collectors.twitter.tweepy.Client", return_value=mock_client):
            collector = TwitterCollector(config)
            result = collector.collect()

        assert len(result) == 2
        assert result[0].title == "Breaking tech news one"
        assert result[0].url == "https://twitter.com/techcrunch/status/123"
        assert result[0].source == "twitter"
        assert result[0].source_name == "@techcrunch"
        assert result[0].category == "technology"
        assert result[0].language == "en"
        expected_score_0 = round(100 * 1.0 + 50 * 2.0 + 10000 * 0.001, 1)
        assert result[0].hot_score == expected_score_0
        assert result[0].raw_data == {"like_count": 100, "retweet_count": 50, "impression_count": 10000}

        assert result[1].title == "Breaking tech news two"
        expected_score_1 = round(200 * 1.0 + 80 * 2.0 + 20000 * 0.001, 1)
        assert result[1].hot_score == expected_score_1

    def test_collect_empty_tweets(self):
        config = {
            "enabled": True,
            "bearer_token": "test_token",
            "target_accounts": ["empty_user"],
            "max_results": 5,
        }

        mock_user_resp = MagicMock()
        mock_user_resp.data = FakeUserData("user_id_empty")

        mock_tweets_resp = MagicMock()
        mock_tweets_resp.data = []

        mock_client = MagicMock()
        mock_client.get_user.return_value = mock_user_resp
        mock_client.get_users_tweets.return_value = mock_tweets_resp

        with patch("collectors.twitter.tweepy.Client", return_value=mock_client):
            collector = TwitterCollector(config)
            result = collector.collect()

        assert result == []

    def test_collect_user_not_found(self):
        config = {
            "enabled": True,
            "bearer_token": "test_token",
            "target_accounts": ["ghost_user"],
            "max_results": 5,
        }

        mock_user_resp = MagicMock()
        mock_user_resp.data = None

        mock_client = MagicMock()
        mock_client.get_user.return_value = mock_user_resp

        with patch("collectors.twitter.tweepy.Client", return_value=mock_client):
            collector = TwitterCollector(config)
            result = collector.collect()

        assert result == []
        mock_client.get_users_tweets.assert_not_called()

    def test_collect_exception_per_account(self, capsys):
        config = {
            "enabled": True,
            "bearer_token": "test_token",
            "target_accounts": ["bad_user", "good_user"],
            "max_results": 5,
        }

        fake_tweet = FakeTweet(
            tweet_id="789",
            text="Good tweet",
            public_metrics={"like_count": 10, "retweet_count": 5},
        )

        mock_user_resp_good = MagicMock()
        mock_user_resp_good.data = FakeUserData("user_id_good")

        mock_tweets_resp_good = MagicMock()
        mock_tweets_resp_good.data = [fake_tweet]

        mock_client = MagicMock()

        def side_effect_get_user(username=None, **kwargs):
            if username == "bad_user":
                raise Exception("User suspended")
            return mock_user_resp_good

        mock_client.get_user.side_effect = side_effect_get_user
        mock_client.get_users_tweets.return_value = mock_tweets_resp_good

        with patch("collectors.twitter.tweepy.Client", return_value=mock_client):
            collector = TwitterCollector(config)
            result = collector.collect()

        assert len(result) == 1
        assert result[0].title == "Good tweet"
        captured = capsys.readouterr()
        assert "[Twitter] Error fetching @bad_user: User suspended" in captured.out

    def test_collect_multiple_accounts(self):
        config = {
            "enabled": True,
            "bearer_token": "test_token",
            "target_accounts": ["account_a", "account_b"],
            "max_results": 3,
        }

        fake_tweet_a = FakeTweet(
            tweet_id="111",
            text="Tweet A",
            public_metrics={"like_count": 10},
        )
        fake_tweet_b = FakeTweet(
            tweet_id="222",
            text="Tweet B",
            public_metrics={"like_count": 20},
        )

        mock_user_resp_a = MagicMock()
        mock_user_resp_a.data = FakeUserData("id_a")

        mock_user_resp_b = MagicMock()
        mock_user_resp_b.data = FakeUserData("id_b")

        mock_tweets_resp_a = MagicMock()
        mock_tweets_resp_a.data = [fake_tweet_a]

        mock_tweets_resp_b = MagicMock()
        mock_tweets_resp_b.data = [fake_tweet_b]

        mock_client = MagicMock()

        def side_effect_get_user(username=None, **kwargs):
            if username == "account_a":
                return mock_user_resp_a
            return mock_user_resp_b

        def side_effect_get_users_tweets(id=None, **kwargs):
            if id == "id_a":
                return mock_tweets_resp_a
            return mock_tweets_resp_b

        mock_client.get_user.side_effect = side_effect_get_user
        mock_client.get_users_tweets.side_effect = side_effect_get_users_tweets

        with patch("collectors.twitter.tweepy.Client", return_value=mock_client):
            collector = TwitterCollector(config)
            result = collector.collect()

        assert len(result) == 2
        titles = {r.title for r in result}
        assert titles == {"Tweet A", "Tweet B"}
        source_names = {r.source_name for r in result}
        assert source_names == {"@account_a", "@account_b"}

    def test_collect_hot_score_calculation(self):
        config = {
            "enabled": True,
            "bearer_token": "test_token",
            "target_accounts": ["tech"],
            "max_results": 1,
        }

        fake_tweet = FakeTweet(
            tweet_id="999",
            text="Viral tweet",
            public_metrics={
                "like_count": 500,
                "retweet_count": 200,
                "impression_count": 50000,
            },
        )

        mock_user_resp = MagicMock()
        mock_user_resp.data = FakeUserData("id_tech")

        mock_tweets_resp = MagicMock()
        mock_tweets_resp.data = [fake_tweet]

        mock_client = MagicMock()
        mock_client.get_user.return_value = mock_user_resp
        mock_client.get_users_tweets.return_value = mock_tweets_resp

        with patch("collectors.twitter.tweepy.Client", return_value=mock_client):
            collector = TwitterCollector(config)
            result = collector.collect()

        expected_score = round(500 * 1.0 + 200 * 2.0 + 50000 * 0.001, 1)
        assert len(result) == 1
        assert result[0].hot_score == expected_score

    def test_collect_tweet_text_truncation(self):
        config = {
            "enabled": True,
            "bearer_token": "test_token",
            "target_accounts": ["longtweet"],
            "max_results": 1,
        }

        long_text = "A" * 300
        fake_tweet = FakeTweet(
            tweet_id="777",
            text=long_text,
            public_metrics={},
        )

        mock_user_resp = MagicMock()
        mock_user_resp.data = FakeUserData("id_long")

        mock_tweets_resp = MagicMock()
        mock_tweets_resp.data = [fake_tweet]

        mock_client = MagicMock()
        mock_client.get_user.return_value = mock_user_resp
        mock_client.get_users_tweets.return_value = mock_tweets_resp

        with patch("collectors.twitter.tweepy.Client", return_value=mock_client):
            collector = TwitterCollector(config)
            result = collector.collect()

        assert len(result) == 1
        assert result[0].title == "A" * 200
        assert len(result[0].title) == 200

    def test_collect_max_results_capped_at_20(self):
        config = {
            "enabled": True,
            "bearer_token": "test_token",
            "target_accounts": ["captest"],
            "max_results": 100,
        }

        fake_tweet = FakeTweet(
            tweet_id="888",
            text="Cap test",
            public_metrics={},
        )

        mock_user_resp = MagicMock()
        mock_user_resp.data = FakeUserData("id_cap")

        mock_tweets_resp = MagicMock()
        mock_tweets_resp.data = [fake_tweet]

        mock_client = MagicMock()
        mock_client.get_user.return_value = mock_user_resp
        mock_client.get_users_tweets.return_value = mock_tweets_resp

        with patch("collectors.twitter.tweepy.Client", return_value=mock_client):
            collector = TwitterCollector(config)
            collector.collect()

        _, kwargs = mock_client.get_users_tweets.call_args
        assert kwargs["max_results"] == 20

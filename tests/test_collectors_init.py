"""Tests for collectors/__init__.py."""
import pytest

from collectors import COLLECTORS, load_collectors
from collectors.hackernews import HackerNewsCollector
from collectors.reddit import RedditCollector
from collectors.twitter import TwitterCollector
from collectors.youtube import YouTubeCollector
from collectors.weibo import WeiboCollector
from collectors.zhihu import ZhihuCollector
from collectors.rss import RSSCollector


class TestLoadCollectors:
    """Tests for load_collectors function."""

    def test_returns_all_instances(self):
        """Verify load_collectors returns an instance for every registered collector."""
        config = {"sources": {}}
        instances = load_collectors(config)
        assert len(instances) == len(COLLECTORS)
        for instance in instances:
            assert type(instance) in COLLECTORS.values()

    def test_config_passed_correctly(self):
        """Verify each collector receives the correct source-specific config."""
        config = {
            "sources": {
                "hackernews": {"enabled": True, "top_stories_limit": 5},
                "reddit": {"enabled": False, "subreddits": ["r/test"]},
                "twitter": {"enabled": True, "bearer_token": "test_token"},
            }
        }
        instances = load_collectors(config)
        by_class = {type(inst): inst for inst in instances}

        assert by_class[HackerNewsCollector].config == {"enabled": True, "top_stories_limit": 5}
        assert by_class[RedditCollector].config == {"enabled": False, "subreddits": ["r/test"]}
        assert by_class[TwitterCollector].config == {"enabled": True, "bearer_token": "test_token"}
        # Sources not present in config should receive an empty dict
        assert by_class[YouTubeCollector].config == {}
        assert by_class[WeiboCollector].config == {}
        assert by_class[ZhihuCollector].config == {}
        assert by_class[RSSCollector].config == {}

    def test_collectors_dict_contains_expected_keys(self):
        """Verify COLLECTORS dictionary contains all expected collector names."""
        expected_keys = {
            "hackernews",
            "reddit",
            "twitter",
            "youtube",
            "weibo",
            "zhihu",
            "rss",
        }
        assert set(COLLECTORS.keys()) == expected_keys

    def test_collectors_dict_values_are_classes(self):
        """Verify all values in COLLECTORS are collector classes."""
        for name, cls in COLLECTORS.items():
            assert isinstance(cls, type)
            # Each class should be instantiable with an empty dict (default disabled)
            instance = cls({})
            assert instance.is_available() is False

    def test_instance_names(self):
        """Verify derived instance names match COLLECTORS keys."""
        config = {"sources": {}}
        instances = load_collectors(config)
        for instance in instances:
            expected_name = type(instance).__name__.replace("Collector", "").lower()
            assert instance.name == expected_name

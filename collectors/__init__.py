"""Collectors registry."""
from .hackernews import HackerNewsCollector
from .reddit import RedditCollector
from .twitter import TwitterCollector
from .youtube import YouTubeCollector
from .weibo import WeiboCollector
from .zhihu import ZhihuCollector
from .rss import RSSCollector


COLLECTORS = {
    "hackernews": HackerNewsCollector,
    "reddit": RedditCollector,
    "twitter": TwitterCollector,
    "youtube": YouTubeCollector,
    "weibo": WeiboCollector,
    "zhihu": ZhihuCollector,
    "rss": RSSCollector,
}


def load_collectors(config: dict):
    """Instantiate all enabled collectors."""
    instances = []
    for name, cls in COLLECTORS.items():
        source_config = config.get("sources", {}).get(name, {})
        instances.append(cls(source_config))
    return instances

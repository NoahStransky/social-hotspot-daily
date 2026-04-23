"""Reddit collector using PRAW."""
from typing import List
import praw
from .base import BaseCollector, NewsItem


class RedditCollector(BaseCollector):
    """Fetch hot posts from tech subreddits."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.reddit = None
        if self.enabled and config.get("client_id"):
            try:
                self.reddit = praw.Reddit(
                    client_id=config["client_id"],
                    client_secret=config["client_secret"],
                    user_agent=config.get("user_agent", "SocialHotspotBot/1.0"),
                )
            except Exception as e:
                print(f"[Reddit] Auth failed: {e}")
    
    def is_available(self) -> bool:
        return self.enabled and self.reddit is not None
    
    def collect(self) -> List[NewsItem]:
        if not self.is_available():
            return []
        
        items = []
        subreddits = self.config.get("subreddits", ["technology"])
        limit = self.config.get("limit", 15)
        
        for sub_name in subreddits:
            try:
                sub = self.reddit.subreddit(sub_name)
                for post in sub.hot(limit=limit):
                    if post.stickied:
                        continue
                    
                    hot_score = post.score * 0.6 + post.num_comments * 0.4
                    
                    items.append(NewsItem(
                        title=post.title,
                        url=post.url,
                        source="reddit",
                        source_name=f"r/{sub_name}",
                        hot_score=round(hot_score, 1),
                        category="technology",
                        language="en",
                        raw_data={
                            "score": post.score,
                            "comments": post.num_comments,
                            "upvote_ratio": post.upvote_ratio,
                        }
                    ))
            except Exception as e:
                print(f"[Reddit] Error in r/{sub_name}: {e}")
        
        return items

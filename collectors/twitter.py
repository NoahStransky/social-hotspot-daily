"""X/Twitter collector using Tweepy."""
from typing import List
import tweepy
from .base import BaseCollector, NewsItem


class TwitterCollector(BaseCollector):
    """Fetch recent tweets from key tech accounts."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.client = None
        if self.enabled and config.get("bearer_token"):
            try:
                self.client = tweepy.Client(
                    bearer_token=config["bearer_token"],
                    wait_on_rate_limit=True
                )
            except Exception as e:
                print(f"[Twitter] Auth failed: {e}")
    
    def is_available(self) -> bool:
        return self.enabled and self.client is not None
    
    def collect(self) -> List[NewsItem]:
        if not self.is_available():
            return []
        
        items = []
        accounts = self.config.get("target_accounts", [])
        max_results = self.config.get("max_results", 20)
        
        for username in accounts:
            try:
                # Get user ID
                user = self.client.get_user(username=username.lstrip("@"))
                if not user or not user.data:
                    continue
                
                # Get recent tweets
                tweets = self.client.get_users_tweets(
                    id=user.data.id,
                    max_results=min(max_results, 20),
                    tweet_fields=["public_metrics", "created_at", "context_annotations"],
                    exclude=["retweets", "replies"]
                )
                
                if not tweets or not tweets.data:
                    continue
                
                for tweet in tweets.data:
                    metrics = tweet.public_metrics or {}
                    hot_score = (
                        metrics.get("like_count", 0) * 1.0 +
                        metrics.get("retweet_count", 0) * 2.0 +
                        metrics.get("impression_count", 0) * 0.001
                    )
                    
                    url = f"https://twitter.com/{username}/status/{tweet.id}"
                    
                    items.append(NewsItem(
                        title=tweet.text[:200],
                        url=url,
                        source="twitter",
                        source_name=f"@{username}",
                        hot_score=round(hot_score, 1),
                        category="technology",
                        language="en",
                        raw_data=metrics
                    ))
                    
            except Exception as e:
                print(f"[Twitter] Error fetching @{username}: {e}")
        
        return items

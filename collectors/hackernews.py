"""Hacker News collector - official API, no auth required."""
import requests
from typing import List
from .base import BaseCollector, NewsItem


class HackerNewsCollector(BaseCollector):
    """Fetch top stories from Hacker News."""
    
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    
    def collect(self) -> List[NewsItem]:
        if not self.is_available():
            return []
        
        items = []
        limit = self.config.get("top_stories_limit", 20)
        
        try:
            # Get top story IDs
            resp = requests.get(f"{self.BASE_URL}/topstories.json", timeout=30)
            story_ids = resp.json()[:limit]
            
            for story_id in story_ids:
                try:
                    story_resp = requests.get(
                        f"{self.BASE_URL}/item/{story_id}.json", 
                        timeout=10
                    )
                    story = story_resp.json()
                    
                    if not story or story.get("deleted") or story.get("dead"):
                        continue
                    
                    title = story.get("title", "")
                    url = story.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
                    score = story.get("score", 0)
                    descendants = story.get("descendants", 0)
                    
                    # HN hot score: weighted combination
                    hot_score = score * 0.7 + descendants * 0.3
                    
                    items.append(NewsItem(
                        title=title,
                        url=url,
                        source="hackernews",
                        source_name="Hacker News",
                        hot_score=round(hot_score, 1),
                        category="technology",
                        language="en",
                        raw_data=story
                    ))
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"[HackerNews] Error: {e}")
        
        return items

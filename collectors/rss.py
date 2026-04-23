"""RSS/Atom feed collector."""
import feedparser
from typing import List
from .base import BaseCollector, NewsItem


class RSSCollector(BaseCollector):
    """Fetch news from RSS feeds."""
    
    def collect(self) -> List[NewsItem]:
        if not self.is_available():
            return []
        
        items = []
        feeds = self.config.get("feeds", [])
        
        for feed_url in feeds:
            try:
                parsed = feedparser.parse(feed_url)
                
                for i, entry in enumerate(parsed.entries[:15]):
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    
                    if not title or not link:
                        continue
                    
                    # Extract domain as source name
                    domain = feed_url.split("/")[2] if "//" in feed_url else "RSS"
                    
                    items.append(NewsItem(
                        title=title,
                        url=link,
                        source="rss",
                        source_name=domain,
                        hot_score=round(max(500 - i * 20, 50), 1),
                        category="technology",
                        language="en",
                        raw_data={"feed": feed_url}
                    ))
                    
            except Exception as e:
                print(f"[RSS] Error parsing {feed_url}: {e}")
        
        return items

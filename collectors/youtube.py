"""YouTube trending collector using Data API v3."""
from typing import List
from googleapiclient.discovery import build
from .base import BaseCollector, NewsItem


class YouTubeCollector(BaseCollector):
    """Fetch trending tech videos."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.youtube = None
        if self.enabled and config.get("api_key"):
            try:
                self.youtube = build("youtube", "v3", developerKey=config["api_key"], static_discovery=False)
            except Exception as e:
                print(f"[YouTube] Init failed: {e}")
    
    def is_available(self) -> bool:
        return self.enabled and self.youtube is not None
    
    def collect(self) -> List[NewsItem]:
        if not self.is_available():
            return []
        
        items = []
        region = self.config.get("region_code", "US")
        category = self.config.get("category_id", "28")  # Science & Tech
        max_results = self.config.get("max_results", 10)
        
        try:
            resp = self.youtube.videos().list(
                part="snippet,statistics",
                chart="mostPopular",
                regionCode=region,
                videoCategoryId=category,
                maxResults=max_results
            ).execute()
            
            for item in resp.get("items", []):
                try:
                    snippet = item["snippet"]
                    stats = item.get("statistics", {})
                    video_id = item["id"]
                    
                    title = snippet.get("title", "")
                    url = f"https://youtube.com/watch?v={video_id}"
                    
                    views = int(stats.get("viewCount", 0))
                    likes = int(stats.get("likeCount", 0))
                    hot_score = views * 0.001 + likes * 0.1
                    
                    items.append(NewsItem(
                        title=title,
                        url=url,
                        source="youtube",
                        source_name=snippet.get("channelTitle", "YouTube"),
                        hot_score=round(hot_score, 1),
                        category="technology",
                        language=snippet.get("defaultLanguage", "en"),
                        raw_data=stats
                    ))
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"[YouTube] Error: {e}")
        
        return items

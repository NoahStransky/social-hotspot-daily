"""Zhihu hot list collector - web scraping."""
import requests
from bs4 import BeautifulSoup
from typing import List
from .base import BaseCollector, NewsItem


class ZhihuCollector(BaseCollector):
    """Fetch Zhihu hot list topics."""
    
    HOT_URL = "https://www.zhihu.com/hot"
    
    def collect(self) -> List[NewsItem]:
        if not self.is_available():
            return []
        
        items = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "cookie": '_zap=1; d_c0=1;',  # minimal cookie to pass basic check
        }
        
        try:
            resp = requests.get(self.HOT_URL, headers=headers, timeout=20)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Zhihu hot list uses script tag with JSON data or direct DOM
            # Try direct DOM parsing first
            hot_items = soup.select(".HotList-item") or soup.select("[data-za-detail-view-path]")
            
            if not hot_items:
                # Fallback: parse all link cards
                hot_items = soup.select("a[href^='/question/']")[:30]
            
            for i, item in enumerate(hot_items[:30]):
                try:
                    title_elem = item.select_one(".HotList-itemTitle") or item.select_one("h2") or item
                    title = title_elem.get_text(strip=True) if hasattr(title_elem, 'get_text') else item.get_text(strip=True)
                    
                    if not title or len(title) < 3:
                        continue
                    
                    # Find link
                    link = item.get("href", "")
                    if not link.startswith("http"):
                        link = f"https://www.zhihu.com{link}"
                    
                    hot_score = max(1000 - i * 30, 100)
                    
                    items.append(NewsItem(
                        title=title,
                        url=link,
                        source="zhihu",
                        source_name="知乎热榜",
                        hot_score=round(hot_score, 1),
                        category="general",
                        language="zh",
                        raw_data={"rank": i + 1}
                    ))
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"[Zhihu] Error: {e}")
        
        return items

"""Weibo hot search collector - web scraping."""
import requests
from bs4 import BeautifulSoup
from typing import List
from .base import BaseCollector, NewsItem


class WeiboCollector(BaseCollector):
    """Fetch Weibo hot search topics."""
    
    HOT_URL = "https://s.weibo.com/top/summary?cate=realtimehot"
    
    def collect(self) -> List[NewsItem]:
        if not self.is_available():
            return []
        
        items = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        
        try:
            resp = requests.get(self.HOT_URL, headers=headers, timeout=20)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Find the hot search table
            table = soup.find("table")
            if not table:
                return items
            
            rows = table.find_all("tr")[1:]  # Skip header
            for i, row in enumerate(rows[:30]):  # Top 30
                try:
                    td = row.find("td", class_="td-02")
                    if not td:
                        continue
                    
                    a_tag = td.find("a")
                    if not a_tag:
                        continue
                    
                    title = a_tag.get_text(strip=True)
                    href = a_tag.get("href", "")
                    if href.startswith("/"):
                        url = f"https://s.weibo.com{href}"
                    else:
                        url = href
                    
                    # Hot score based on rank
                    hot_score = max(1000 - i * 30, 100)
                    
                    items.append(NewsItem(
                        title=title,
                        url=url,
                        source="weibo",
                        source_name="微博热搜",
                        hot_score=round(hot_score, 1),
                        category="general",
                        language="zh",
                        raw_data={"rank": i + 1}
                    ))
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"[Weibo] Error: {e}")
        
        return items

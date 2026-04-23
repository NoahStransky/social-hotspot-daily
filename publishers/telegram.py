"""Telegram publisher for notifications."""
import os
import requests
from typing import List
from collectors.base import NewsItem


class TelegramPublisher:
    """Send daily digest link to Telegram."""
    
    def __init__(self, config: dict):
        self.enabled = config.get("enabled", False)
        self.bot_token = config.get("bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = config.get("chat_id") or os.environ.get("TELEGRAM_CHAT_ID", "")
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"
    
    def is_available(self) -> bool:
        return self.enabled and bool(self.bot_token) and bool(self.chat_id)
    
    def publish(self, items: List[NewsItem], blog_url: str) -> bool:
        if not self.is_available():
            print("[Telegram] Not configured, skipping")
            return False
        
        today = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        date_str = today.strftime("%Y-%m-%d")
        
        # Build message
        categories = {}
        for item in items[:10]:
            cat = item.category.replace("_", " ").title()
            categories.setdefault(cat, []).append(item)
        
        lines = [
            f"📰 <b>Tech Hotspot Daily — {date_str}</b>",
            f"",
            f"🌍 {len(items)} tech stories curated from global platforms",
            f"",
        ]
        
        for cat, cat_items in list(categories.items())[:4]:
            lines.append(f"<b>{cat}</b>")
            for item in cat_items[:2]:
                title = item.raw_data.get("english_title", item.title)[:60]
                lines.append(f"• <a href='{item.url}'>{title}</a>")
            lines.append("")
        
        lines.append(f"📎 <a href='{blog_url}'>Read full report →</a>")
        
        text = "\n".join(lines)
        
        try:
            resp = requests.post(
                f"{self.api_base}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                },
                timeout=30
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("ok"):
                print("[Telegram] Message sent successfully")
                return True
            else:
                print(f"[Telegram] API error: {result}")
                return False
        except Exception as e:
            print(f"[Telegram] Error: {e}")
            return False

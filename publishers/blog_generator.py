"""Generate static blog pages for GitHub Pages with date-based navigation."""
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from collectors.base import NewsItem


ARCHIVE_DIR = "archive"
FEED_FILE = "feed.json"


class BlogGenerator:
    """Generate a beautiful static tech daily blog with date history."""

    def __init__(self, config: dict, output_dir: str = "docs"):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / ARCHIVE_DIR).mkdir(parents=True, exist_ok=True)

        # Setup Jinja2
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"])
        )

    def _load_feed(self) -> Dict[str, list]:
        """Load existing feed.json for historical data."""
        feed_path = self.output_dir / FEED_FILE
        if feed_path.exists():
            try:
                return json.loads(feed_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, Exception):
                return {}
        return {}

    def _save_feed(self, feed: dict):
        """Save feed.json atomically."""
        feed_path = self.output_dir / FEED_FILE
        feed_path.write_text(
            json.dumps(feed, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def _save_archive(self, today: str, items: List[NewsItem]):
        """Save today's items as an archive JSON."""
        archive_data = {
            "date": today,
            "items": [
                {
                    "title": item.title,
                    "url": item.url,
                    "source": item.source_name,
                    "category": item.category,
                    "summary": item.summary,
                    "insight": item.raw_data.get("insight", ""),
                    "english_title": item.raw_data.get("english_title", item.title),
                }
                for item in items
            ]
        }
        archive_path = self.output_dir / ARCHIVE_DIR / f"{today}.json"
        archive_path.write_text(
            json.dumps(archive_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def generate(self, items: List[NewsItem], date_str: Optional[str] = None) -> str:
        """Generate blog page and return the URL path."""
        today = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        date_display = datetime.now(timezone.utc).strftime("%B %d, %Y")

        # Group today's items by category (sorted by count descending)
        categories_ordered = {}
        for item in items:
            cat = item.category.replace("_", " ").title()
            categories_ordered.setdefault(cat, []).append(item)
        categories_ordered = dict(sorted(categories_ordered.items(), key=lambda x: -len(x[1])))

        # Flatten to list of dicts for template
        categories_list = []
        for cat_name, cat_items in categories_ordered.items():
            categories_list.append({
                "name": cat_name,
                "category_slug": cat_items[0].category if cat_items else "general",
                "article_list": [
                    {
                        "title": item.title,
                        "url": item.url,
                        "source_name": item.source_name,
                        "category": item.category,
                        "summary": item.summary,
                        "insight": item.raw_data.get("insight", ""),
                        "english_title": item.raw_data.get("english_title", item.title),
                    }
                    for item in cat_items
                ]
            })

        # Save today's archive
        self._save_archive(today, items)

        # Load and update feed
        feed = self._load_feed()
        feed[today] = {
            "title": self.config.get("title", "Tech Hotspot Daily"),
            "total_items": len(items),
        }
        self._save_feed(feed)

        # Available dates (sorted, for navigation)
        available_dates = sorted(feed.keys(), reverse=True)
        prev_date = None
        next_date = None
        if today in available_dates:
            idx = available_dates.index(today)
            if idx > 0:
                prev_date = available_dates[idx - 1]
            if idx < len(available_dates) - 1:
                next_date = available_dates[idx + 1]

        base_url = self.config.get("base_url", "")

        # Render index.html (today's page)
        data = {
            "title": self.config.get("title", "Tech Hotspot Daily"),
            "description": self.config.get("description", ""),
            "author": self.config.get("author", "Bot"),
            "date": date_display,
            "iso_date": today,
            "categories": categories_list,
            "total_items": len(items),
            "base_url": base_url,
            "available_dates": available_dates,
            "current_date": today,
            "prev_date": prev_date,
            "next_date": next_date,
            "has_content": len(items) > 0,
        }
        template = self.env.get_template("blog.html")
        html = template.render(**data)

        index_path = self.output_dir / "index.html"
        index_path.write_text(html, encoding="utf-8")

        # Copy static pages
        template_dir = Path(__file__).parent.parent / "templates"
        for page in ["subscribe.html", "verify.html", "unsubscribe.html"]:
            src = template_dir / page
            if src.exists():
                dst = self.output_dir / page
                dst.write_text(src.read_text(), encoding="utf-8")

        return str(index_path)

    def get_page_url(self) -> str:
        base = self.config.get("base_url", "")
        return f"{base}/" if base else ""

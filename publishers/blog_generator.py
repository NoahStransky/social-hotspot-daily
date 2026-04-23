"""Generate static blog pages for GitHub Pages."""
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from jinja2 import Environment, FileSystemLoader, select_autoescape
from collectors.base import NewsItem


class BlogGenerator:
    """Generate a beautiful static tech daily blog."""
    
    def __init__(self, config: dict, output_dir: str = "docs"):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Jinja2
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"])
        )
    
    def generate(self, items: List[NewsItem]) -> str:
        """Generate blog page and return the URL path."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        date_display = datetime.now(timezone.utc).strftime("%B %d, %Y")
        
        # Group by category
        categories = {}
        for item in items:
            cat = item.category.replace("_", " ").title()
            categories.setdefault(cat, []).append(item)
        
        # Sort categories by item count
        categories = dict(sorted(categories.items(), key=lambda x: -len(x[1])))
        
        # Prepare template data
        data = {
            "title": self.config.get("title", "Tech Hotspot Daily"),
            "description": self.config.get("description", ""),
            "author": self.config.get("author", "Bot"),
            "date": date_display,
            "iso_date": today,
            "categories": categories,
            "total_items": len(items),
            "base_url": self.config.get("base_url", ""),
        }
        
        # Render HTML
        template = self.env.get_template("blog.html")
        html = template.render(**data)
        
        # Write index.html
        index_path = self.output_dir / "index.html"
        index_path.write_text(html, encoding="utf-8")
        
        # Write JSON feed for programmatic access
        feed_path = self.output_dir / "feed.json"
        feed_data = {
            "date": today,
            "items": [
                {
                    "title": item.title,
                    "url": item.url,
                    "source": item.source,
                    "category": item.category,
                    "summary": item.summary,
                    "insight": item.raw_data.get("insight", ""),
                }
                for item in items
            ]
        }
        feed_path.write_text(json.dumps(feed_data, ensure_ascii=False, indent=2), encoding="utf-8")
        
        return str(index_path)
    
    def get_page_url(self) -> str:
        base = self.config.get("base_url", "")
        return f"{base}/" if base else ""

#!/usr/bin/env python3
"""Regenerate all blog pages with correct date metadata."""
import sys
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from publishers.blog_generator import BlogGenerator

config = {
    "title": "Tech Hotspot Daily",
    "description": "每日全球科技热点聚合",
    "author": "Social Hotspot Bot",
    "base_url": "https://YOUR_USERNAME.github.io/social-hotspot-daily",
}

generator = BlogGenerator(config, output_dir="docs")

# Load feed
feed_path = Path("docs/feed.json")
feed = json.loads(feed_path.read_text(encoding="utf-8"))

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
dates = sorted([k for k in feed.keys() if DATE_PATTERN.match(k)], reverse=True)

print(f"Found {len(dates)} dates: {dates}")

from collectors.base import NewsItem

for i, date in enumerate(dates):
    y, m, d = date.split("-")
    
    new_path = Path(f"docs/archive/{y}/{m}/{d}/index.json")
    old_path = Path(f"docs/archive/{y}/{m}/{d}.json")
    legacy_path = Path(f"docs/archive/{date}.json")
    archive_path = new_path if new_path.exists() else (old_path if old_path.exists() else legacy_path)
    
    if not archive_path.exists():
        print(f"  Skip {date}: no archive data")
        continue
    
    archive_data = json.loads(archive_path.read_text(encoding="utf-8"))
    raw_items = archive_data.get("items", [])
    
    items = []
    for raw in raw_items:
        item = NewsItem(
            title=raw["title"],
            url=raw["url"],
            source=raw.get("source", ""),
            source_name=raw.get("source", ""),
            category=raw.get("category", "general"),
            summary=raw.get("summary", ""),
        )
        item.raw_data["insight"] = raw.get("insight", "")
        item.raw_data["english_title"] = raw.get("english_title", raw["title"])
        items.append(item)
    
    # Override generate to pass date_str — this makes the template render
    # correct title/date/TODAY for each archive page
    generator.generate(items, date_str=date)
    print(f"  ✓ {date} ({len(items)} items)")
    
    # The last iteration writes docs/index.html, which is fine as long as
    # the last date is the LATEST (since dates are sorted reverse=True)
    
# Final assertion: check index.html has TODAY as latest date
latest = dates[0]
index_html = Path("docs/index.html").read_text()
if f"TODAY = '{latest}'" in index_html:
    print(f"\n✅ Index page correctly set to latest date: {latest}")
else:
    # Re-generate index.html with the latest date
    print(f"\n⚠️  Re-generating index.html for latest date: {latest}")
    y2, m2, d2 = latest.split("-")
    latest_path = Path(f"docs/archive/{y2}/{m2}/{d2}/index.json")
    if not latest_path.exists():
        latest_path = Path(f"docs/archive/{y2}/{m2}/{d2}.json")
    if not latest_path.exists():
        latest_path = Path(f"docs/archive/{latest}.json")
    latest_data = json.loads(latest_path.read_text(encoding="utf-8"))
    latest_raw = latest_data.get("items", [])
    latest_items = []
    for raw in latest_raw:
        item = NewsItem(title=raw["title"], url=raw["url"], source=raw.get("source",""), source_name=raw.get("source",""), category=raw.get("category","general"), summary=raw.get("summary",""))
        item.raw_data["insight"] = raw.get("insight","")
        item.raw_data["english_title"] = raw.get("english_title",raw["title"])
        latest_items.append(item)
    generator.generate(latest_items, date_str=latest)
    print(f"  ✓ Index.html set to {latest}")

print("\n✅ All pages regenerated!")

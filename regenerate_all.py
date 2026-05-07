#!/usr/bin/env python3
"""Regenerate all blog pages from existing archive data."""
import sys, json, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from publishers.blog_generator import BlogGenerator
from collectors.base import NewsItem

config = {
    "title": "Tech Hotspot Daily",
    "description": "每日全球科技热点聚合",
    "author": "Social Hotspot Bot",
    "base_url": "https://YOUR_USERNAME.github.io/social-hotspot-daily",
}

generator = BlogGenerator(config, output_dir="docs")

feed = json.loads(Path("docs/feed.json").read_text(encoding="utf-8"))
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
dates = sorted([k for k in feed if DATE_PATTERN.match(k)], reverse=True)
print(f"Found {len(dates)} dates: {dates}")

for i, date in enumerate(dates):
    y, m, d = date.split("-")
    path = Path(f"docs/archive/{y}/{m}/{d}/index.json")
    if not path.exists():
        path = Path(f"docs/archive/{date}.json")
    if not path.exists():
        print(f"  Skip {date}: no archive")
        continue
    
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_items = data.get("items", [])
    items = []
    for raw in raw_items:
        item = NewsItem(title=raw["title"], url=raw["url"], source=raw.get("source",""), source_name=raw.get("source",""), category=raw.get("category","general"), summary=raw.get("summary",""))
        item.raw_data["insight"] = raw.get("insight","")
        item.raw_data["english_title"] = raw.get("english_title", raw["title"])
        items.append(item)
    
    generator.generate(items, date_str=date)
    print(f"  ✓ {date} ({len(items)} items)")

# Ensure index.html is latest date
latest = dates[0]
idx = Path("docs/index.html").read_text().find(f"TODAY = '{latest}'")
if idx == -1:
    y2, m2, d2 = latest.split("-")
    p = Path(f"docs/archive/{y2}/{m2}/{d2}/index.json")
    if not p.exists():
        p = Path(f"docs/archive/{latest}.json")
    d = json.loads(p.read_text())
    items = []
    for raw in d["items"]:
        item = NewsItem(title=raw["title"], url=raw["url"], source=raw.get("source",""), source_name=raw.get("source",""), category=raw.get("category","general"), summary=raw.get("summary",""))
        item.raw_data["insight"] = raw.get("insight","")
        item.raw_data["english_title"] = raw.get("english_title", raw["title"])
        items.append(item)
    generator.generate(items, date_str=latest)
    print(f"  → Index set to {latest}")

print("\n✅ Done!")

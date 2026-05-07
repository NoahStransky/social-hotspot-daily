#!/usr/bin/env python3
"""Migrate archive data to standard archive/YYYY/MM/DD/index.html + index.json structure.

Operations:
a. Move docs/archive/YYYY/MM/DD.json → docs/archive/YYYY/MM/DD/index.json
b. Copy docs/YYYY-MM-DD/index.html → docs/archive/YYYY/MM/DD/index.html
c. For all 9 days (2026-04-28 to 2026-05-06)
"""
import json
import shutil
from pathlib import Path

BASE = Path(__file__).parent / "docs"

# Dates to migrate
dates = [
    "2026-04-28", "2026-04-29", "2026-04-30",
    "2026-05-01", "2026-05-02", "2026-05-03",
    "2026-05-04", "2026-05-05", "2026-05-06",
]

archive_dir = BASE / "archive"

for date_str in dates:
    y, m, d = date_str.split("-")
    target_dir = archive_dir / y / m / d
    target_dir.mkdir(parents=True, exist_ok=True)

    # a. Move flat JSON → index.json (copy, don't delete old yet)
    old_json = archive_dir / f"{date_str}.json"
    new_json = target_dir / "index.json"
    if old_json.exists() and not new_json.exists():
        data = json.loads(old_json.read_text(encoding="utf-8"))
        new_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✓ Copied archive/{date_str}.json → archive/{y}/{m}/{d}/index.json")
    elif new_json.exists():
        print(f"  • archive/{y}/{m}/{d}/index.json already exists")
    else:
        print(f"  ✗ Missing source: archive/{date_str}.json")

    # b. Copy YYYY-MM-DD/index.html → archive/YYYY/MM/DD/index.html
    old_html = BASE / date_str / "index.html"
    new_html = target_dir / "index.html"
    if old_html.exists() and not new_html.exists():
        shutil.copy2(old_html, new_html)
        print(f"  ✓ Copied {date_str}/index.html → archive/{y}/{m}/{d}/index.html")
    elif new_html.exists():
        print(f"  • archive/{y}/{m}/{d}/index.html already exists")
    else:
        print(f"  ✗ Missing source: {date_str}/index.html")

print("\n✅ Migration complete!")

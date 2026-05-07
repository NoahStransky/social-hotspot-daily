#!/usr/bin/env python3
"""Migrate archive JSON files from flat to directory structure.
Old:  docs/archive/YYYY-MM-DD.json
New:  docs/archive/YYYY/MM/DD.json
"""
import json
from pathlib import Path

ARCHIVE_DIR = Path("/opt/data/home/social-hotspot-daily/docs/archive")

for f in sorted(ARCHIVE_DIR.glob("*.json")):
    name = f.stem  # e.g., "2026-04-28"
    parts = name.split("-")
    if len(parts) != 3:
        continue
    y, m, d = parts
    new_dir = ARCHIVE_DIR / y / m / d
    new_dir.mkdir(parents=True, exist_ok=True)
    new_path = new_dir / "index.json"
    if not new_path.exists():
        data = json.loads(f.read_text())
        new_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Copied: {f.name} -> {y}/{m}/{d}.json")
    else:
        print(f"Exists, skip: {y}/{m}/{d}.json")

print("\nDone migrating archive files.")

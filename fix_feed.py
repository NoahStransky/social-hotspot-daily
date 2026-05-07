import json

feed_path = "/opt/data/home/social-hotspot-daily/docs/feed.json"
with open(feed_path, "r") as f:
    data = json.load(f)

# Remove rogue keys that aren't date keys
data.pop("date", None)
data.pop("items", None)

with open(feed_path, "w") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Fixed! Keys:", list(data.keys()))

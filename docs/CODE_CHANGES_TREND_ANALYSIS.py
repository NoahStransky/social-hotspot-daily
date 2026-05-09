"""
Key code snippets for Trend Analysis + Recommendation.

These are the exact code changes needed in each file.
"""

# ===========================================================================
# processors/ai_filter.py — changes
# ===========================================================================

# 1. Line 14-15: Update BATCH_PROMPT_TEMPLATE field spec
# Change from:
# "For each item, output: {\"relevance_score\": float, \"category\": str, \"summary\": str, \"english_title\": str, \"insight\": str}"
# To:
# "For each item, output: {\"relevance_score\": float, \"category\": str, \"summary\": str, \"english_title\": str, \"insight\": str, \"recommendation\": {\"level\": \"must_read|recommended|notable\", \"read_time\": \"X min\", \"relevance_to_tech\": \"high|medium|low\"}}"

# 2. In __init__, after line 41:
# self.trend_analysis = None

# 3. In _process_batch(), after line 113:
# item.raw_data["recommendation"] = result.get("recommendation", {})

# 4. New method: analyze trends
"""
def _analyze_trends(self, items, yesterday_data=None):
    \"\"\"Single API call for global trend analysis.\"\"\"
    from datetime import datetime, timezone, timedelta
    
    if not self.is_available() or not items:
        return None
    
    # Build item list for prompt
    item_lines = []
    for i, item in enumerate(items[:30]):  # Cap at 30 items
        item_lines.append(f"Title: {item.title}\\nCategory: {item.category}")
    
    items_text = "\\n\\n".join(item_lines)
    
    yesterday_topic = "N/A"
    yesterday_breakdown = "N/A"
    if yesterday_data:
        yesterday_topic = yesterday_data.get("trend_analysis", {}).get("top_topic", "N/A")
        yesterday_breakdown = str(yesterday_data.get("trend_analysis", {}).get("category_breakdown", {}))
    
    prompt = f"""Analyze these {len(items)} news items and output a single JSON trend analysis:

{items_text}

Yesterday's top topic: {yesterday_topic}
Yesterday's category breakdown: {yesterday_breakdown}

Output ONLY a JSON object with fields:
- top_topic (string): The single most important topic/story today
- trending_keywords (string[]): 3-10 keywords
- category_breakdown (object): count of items per category
- summary (string): 2-3 sentence narrative
- compared_to_yesterday (string): what changed vs yesterday (or '' if N/A)
- day_over_day (object): {{rising_categories: [], falling_categories: [], new_trends: []}}
"""
    
    TREND_SYSTEM_PROMPT = """You are a tech news analyst. Given today's curated news items, produce a global trend analysis JSON. Output ONLY valid JSON, no markdown, no explanations."""
    
    resp = requests.post(
        DEEPSEEK_BASE_URL,
        headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": self.model,
            "messages": [
                {"role": "system", "content": TREND_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
        },
        timeout=120
    )
    resp.raise_for_status()
    
    content = resp.json()["choices"][0]["message"]["content"]
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()
    
    result = json.loads(content)
    print(f"[AI Trend] Top topic: {result.get('top_topic', 'N/A')}")
    return result

# 5. New helper: load yesterday's archive
"""   
def _load_yesterday_items(self):
    \"\"\"Load yesterday's archive JSON for comparison.\"\"\"
    from datetime import datetime, timezone, timedelta
    from pathlib import Path
    
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    y, m, d = yesterday.split("-")
    archive_path = Path("docs/archive") / y / m / d / "index.json"
    
    if archive_path.exists():
        try:
            data = json.loads(archive_path.read_text(encoding="utf-8"))
            return data
        except (json.JSONDecodeError, Exception):
            pass
    return None
"""

# 6. In process(), after line 65 and before return:
"""
# NEW: Global trend analysis
self.trend_analysis = None
if filtered_items and self.is_available():
    yesterday_data = self._load_yesterday_items()
    self.trend_analysis = self._analyze_trends(filtered_items, yesterday_data)

return filtered_items
"""


# ===========================================================================
# publishers/blog_generator.py — changes
# ===========================================================================

# 1. In _save_archive(), around line 57-78:
"""
def _save_archive(self, today: str, items: List[NewsItem], trend_analysis: dict = None):
    archive_data = {
        "date": today,
        "trend_analysis": trend_analysis or {},  # NEW
        "items": [
            {
                "title": item.title,
                "url": item.url,
                "source": item.source_name,
                "category": item.category,
                "summary": item.summary,
                "insight": item.raw_data.get("insight", ""),
                "english_title": item.raw_data.get("english_title", item.title),
                "recommendation": item.raw_data.get("recommendation", {}),  # NEW
            }
            for item in items
        ]
    }
    ...
"""

# 2. In generate(), around line 81-82:
"""
def generate(self, items: List[NewsItem], date_str: Optional[str] = None, trend_analysis: Optional[Dict] = None) -> str:
"""

# 3. Sort items within each category (after line 92-94):
"""
# Sort items within each category by recommendation level
REC_ORDER = {"must_read": 0, "recommended": 1, "notable": 2}
for cat_name, cat_items in categories_ordered.items():
    cat_items.sort(key=lambda x: (
        REC_ORDER.get(x.raw_data.get("recommendation", {}).get("level", "notable"), 2),
        -x.hot_score
    ))
"""

# 4. Pass trend_analysis to template data and archive (around line 142-156):
"""
# In template data dict:
"trend_analysis": trend_analysis,

# In _save_archive call:
self._save_archive(today, items, trend_analysis)
"""


# ===========================================================================
# templates/blog.html — key additions
# ===========================================================================

# After line 341 (</style>), add trend panel CSS:

"""
/* ===== Trend Panel ===== */
.trend-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
}
.trend-header {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--accent);
    margin-bottom: 16px;
}
.trend-topic {
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 12px;
    color: var(--text);
}
.trend-keywords {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 16px;
}
.keyword-chip {
    padding: 4px 12px;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 100px;
    font-size: 12px;
    color: var(--text-secondary);
}
.trend-summary {
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.6;
    margin-bottom: 16px;
}
.trend-compared {
    padding: 12px 16px;
    background: var(--surface-2);
    border-left: 3px solid var(--accent);
    border-radius: 0 8px 8px 0;
    font-size: 13px;
    color: var(--text-secondary);
}
.trend-category-bars {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 16px;
}
.cat-bar {
    flex: 1;
    min-width: 80px;
    padding: 8px 12px;
    background: var(--surface-2);
    border-radius: 8px;
    text-align: center;
    font-size: 12px;
}
.cat-bar .count {
    font-size: 18px;
    font-weight: 700;
    display: block;
    color: var(--cat-color, var(--text));
}
.cat-bar .label {
    color: var(--text-secondary);
}
/* ===== Recommendation Badge ===== */
.rec-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 10px;
    border-radius: 100px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}
.rec-must_read {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
}
.rec-recommended {
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.3);
}
.rec-notable {
    background: rgba(99, 102, 241, 0.1);
    color: #8b8ba7;
    border: 1px solid var(--border);
}
"""

# ===========================================================================
# publishers/telegram.py — changes
# ===========================================================================

"""
def publish(self, items: List[NewsItem], blog_url: str, trend_analysis: Optional[Dict] = None) -> bool:
    ...
    lines = [
        f"📰 <b>Tech Hotspot Daily — {date_str}</b>",
        f"",
        f"🌍 {len(items)} tech stories curated from global platforms",
        f"",
    ]
    
    # NEW: Add trend summary
    if trend_analysis:
        top_topic = trend_analysis.get('top_topic', '')
        keywords = trend_analysis.get('trending_keywords', [])
        lines.append(f"📊 <b>Today's Trend:</b> {top_topic}")
        if keywords:
            lines.append(f"🔑 <i>{', '.join(keywords[:5])}</i>")
        lines.append("")
    
    # ... rest of existing code ...
"""

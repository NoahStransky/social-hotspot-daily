"""AI-powered filtering, classification, summarization, trend analysis, and recommendations."""
import os
import json
from datetime import datetime, timezone, timedelta
import requests
from typing import List, Dict, Optional
from collectors.base import NewsItem
from pathlib import Path


DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1/chat/completions"

SYSTEM_PROMPT = """You are a tech news curator specializing in AI, software engineering, and technology.
Your job is to analyze news items and decide if they are highly relevant to IT professionals.

For each item, provide:
1. relevance_score (0-1): How relevant to AI/tech/IT?
2. category: MUST be exactly one of these: artificial_intelligence, programming, cybersecurity, hardware, startup, science, other. NEVER use "technology" — map it to the closest match from this list.
3. summary: A concise 1-2 sentence summary in the item's original language
4. english_title: An English translation of the title (if original is non-English)
5. insight: A brief "why it matters" insight for IT professionals (2-3 sentences, in English)
6. recommendation: {"level": "must_read|recommended|notable", "read_time": "X min", "relevance_to_tech": "high|medium|low"}

Output ONLY a JSON array. No markdown, no explanations.
"""

BATCH_PROMPT_TEMPLATE = """Analyze these {count} news items and return a JSON array:

{items}

For each item, output: {{"relevance_score": float, "category": str, "summary": str, "english_title": str, "insight": str, "recommendation": {{"level": "must_read|recommended|notable", "read_time": "X min", "relevance_to_tech": "high|medium|low"}}}}
"""

TREND_SYSTEM_PROMPT = """You are a tech news analyst. Given today's curated news items, produce a global trend analysis.
Output ONLY a valid JSON object. No markdown, no explanations.
"""

TREND_USER_PROMPT_TEMPLATE = """Analyze today's curated tech news items and produce a trend analysis.

Today's items ({count} total):
{items}

{friday_context}

Output JSON with this exact structure:
{{
  "top_topic": "The single most important topic today",
  "trending_keywords": ["keyword1", "keyword2", "keyword3"],
  "category_breakdown": {{"category_name": count}},
  "summary": "A concise 2-3 sentence summary of today's tech landscape",
  "compared_to_yesterday": "Brief comparison with yesterday's trends (if yesterday data available, otherwise say 'First day of tracking')",
  "day_over_day": {{
    "rising_categories": ["category1"],
    "falling_categories": ["category2"],
    "new_trends": ["trend1", "trend2"]
  }}
}}
"""


class AIFilter:
    """Filter and enrich news using LLM, with trend analysis and recommendations."""

    def __init__(self, config: dict):
        self.enabled = config.get("enabled", False)
        self.api_key = config.get("api_key") or os.environ.get("DEEPSEEK_API_KEY", "")
        self.model = config.get("model", "deepseek-chat")
        self.target_categories = config.get("categories", [])
        self.min_confidence = config.get("min_confidence", 0.6)
        self.max_items = config.get("max_items_per_source", 10)
        self.output_dir = config.get("output_dir", "docs")
        self.trend_analysis = None

    def is_available(self) -> bool:
        return self.enabled and bool(self.api_key)

    def process(self, items: List[NewsItem]) -> List[NewsItem]:
        if not self.is_available() or not items:
            return items

        # Batch process for efficiency
        batches = [items[i:i + 15] for i in range(0, len(items), 15)]
        enriched = []

        for batch in batches:
            try:
                enriched.extend(self._process_batch(batch))
            except Exception as e:
                print(f"[AI Filter] Batch failed: {e}")
                enriched.extend(batch)

        # Filter by relevance
        filtered = [item for item in enriched if item.hot_score >= self.min_confidence * 100]

        # Sort by hot_score descending
        filtered.sort(key=lambda x: x.hot_score, reverse=True)

        filtered = filtered[:self.max_items * 3]

        # Trend analysis after enrichment
        if filtered:
            try:
                yesterday_data = self._load_yesterday_items()
                self.trend_analysis = self._analyze_trends(filtered, yesterday_data)
                print("[AI Filter] Trend analysis completed")
            except Exception as e:
                print(f"[AI Filter] Trend analysis failed: {e}")
                self.trend_analysis = None

        return filtered

    def _process_batch(self, items: List[NewsItem]) -> List[NewsItem]:
        batch_text = "\n\n".join(
            f"[{i}] Title: {item.title}\nSource: {item.source}"
            for i, item in enumerate(items)
        )

        prompt = BATCH_PROMPT_TEMPLATE.format(count=len(items), items=batch_text)

        resp = requests.post(
            DEEPSEEK_BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 8192,
            },
            timeout=180
        )
        resp.raise_for_status()

        content = resp.json()["choices"][0]["message"]["content"]

        # Extract JSON
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        results = json.loads(content)

        for item, result in zip(items, results):
            item.hot_score = float(result.get("relevance_score", 0)) * 1000
            item.category = result.get("category", "general")
            item.summary = result.get("summary", "")
            item.raw_data["insight"] = result.get("insight", "")
            item.raw_data["english_title"] = result.get("english_title", item.title)
            item.raw_data["recommendation"] = result.get("recommendation", {})

        return items

    def _load_yesterday_items(self) -> Optional[Dict]:
        """Load yesterday's archive JSON if it exists."""
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        y, m, d = yesterday.split("-")
        archive_path = Path(self.output_dir) / "archive" / y / m / d / "index.json"
        if archive_path.exists():
            try:
                data = json.loads(archive_path.read_text(encoding="utf-8"))
                print(f"[AI Filter] Loaded yesterday's data ({yesterday}): {len(data.get('items', []))} items")
                return data
            except Exception as e:
                print(f"[AI Filter] Failed to load yesterday's archive: {e}")
                return None
        print(f"[AI Filter] No yesterday data found at {archive_path}")
        return None

    def _analyze_trends(self, items: List[NewsItem], yesterday_data: Optional[Dict] = None) -> Optional[Dict]:
        """Analyze trends across today's items, comparing with yesterday if available."""
        # Build today's items text
        items_text_parts = []
        for i, item in enumerate(items):
            cat = item.category.replace("_", " ").title()
            recommendation = item.raw_data.get("recommendation", {})
            level = recommendation.get("level", "notable")
            items_text_parts.append(f"[{i}] Title: {item.title} | Category: {cat} | Level: {level}")
        items_text = "\n".join(items_text_parts)

        # Build yesterday context if available
        yesterday_context = ""
        if yesterday_data:
            yesterday_items = yesterday_data.get("items", [])
            yesterday_titles = "\n".join(
                f"[{i}] {it.get('title', '')} (Category: {it.get('category', 'general')})"
                for i, it in enumerate(yesterday_items[:20])
            )
            yesterday_context = f"Yesterday's items ({len(yesterday_items)} total):\n{yesterday_titles}"
        else:
            yesterday_context = "No yesterday data available (first day or missing archive)."

        prompt = TREND_USER_PROMPT_TEMPLATE.format(
            count=len(items),
            items=items_text,
            friday_context=yesterday_context
        )

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

        # Extract JSON
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        result = json.loads(content)
        return result

"""AI-powered filtering, classification, and summarization."""
import os
import json
import requests
from typing import List
from collectors.base import NewsItem


DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1/chat/completions"

SYSTEM_PROMPT = """You are a tech news curator specializing in AI, software engineering, and technology.
Your job is to analyze news items and decide if they are highly relevant to IT professionals.

For each item, provide:
1. relevance_score (0-1): How relevant to AI/tech/IT?
2. category: one of [artificial_intelligence, programming, cybersecurity, hardware, startup, science, other]
3. summary: A concise 1-2 sentence summary in the item's original language
4. english_title: An English translation of the title (if original is non-English)
5. insight: A brief "why it matters" insight for IT professionals (2-3 sentences, in English)

Output ONLY a JSON array. No markdown, no explanations.
"""

BATCH_PROMPT_TEMPLATE = """Analyze these {count} news items and return a JSON array:

{items}

For each item, output: {{"relevance_score": float, "category": str, "summary": str, "english_title": str, "insight": str}}
"""


class AIFilter:
    """Filter and enrich news using LLM."""
    
    def __init__(self, config: dict):
        self.enabled = config.get("enabled", False)
        self.api_key = config.get("api_key") or os.environ.get("DEEPSEEK_API_KEY", "")
        self.model = config.get("model", "deepseek-chat")
        self.target_categories = config.get("categories", [])
        self.min_confidence = config.get("min_confidence", 0.6)
        self.max_items = config.get("max_items_per_source", 10)
    
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
        
        return filtered[:self.max_items * 3]
    
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
                "max_tokens": 4000,
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
        
        results = json.loads(content)
        
        for item, result in zip(items, results):
            item.hot_score = float(result.get("relevance_score", 0)) * 1000
            item.category = result.get("category", "general")
            item.summary = result.get("summary", "")
            item.raw_data["insight"] = result.get("insight", "")
            item.raw_data["english_title"] = result.get("english_title", item.title)
        
        return items

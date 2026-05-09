# AI Trend Analysis & Recommended Reading — Technical Design

## 1. Data Model Design

### 1.1 New Field: `recommendation` (per NewsItem)

Add `recommendation` to each item in the archive JSON:

```json
{
  "date": "2026-05-07",
  "trend_analysis": { ... },  // ← NEW: top-level field
  "items": [
    {
      "title": "...",
      "url": "...",
      "source": "techcrunch.com",
      "category": "artificial_intelligence",
      "summary": "...",
      "insight": "...",
      "english_title": "...",
      "recommendation": {           // ← NEW per-item field
        "level": "must_read",
        "read_time": "5 min",
        "relevance_to_tech": "high"
      }
    }
  ]
}
```

**Fields:**
- `level`: `"must_read" | "recommended" | "notable"` — AI-assigned reading priority
- `read_time`: string like `"3 min"`, `"5 min"`, `"15 min"` — estimated reading time
- `relevance_to_tech`: `"high" | "medium" | "low"` — how relevant to IT professionals

### 1.2 New Field: `trend_analysis` (top-level in archive JSON)

```json
{
  "trend_analysis": {
    "top_topic": "AI Safety & Governance",
    "trending_keywords": ["OpenAI", "lawsuit", "ransomware", "LLM", "voice AI"],
    "category_breakdown": {
      "artificial_intelligence": 14,
      "cybersecurity": 6,
      "hardware": 3,
      "startup": 2,
      "programming": 2
    },
    "summary": "Today's tech news is dominated by the OpenAI-Musk legal battle, with significant coverage of AI safety features. Cybersecurity remains high with ransomware attacks targeting educational platforms. Hardware news features SpaceX's AI chip investment and Apple's camera-equipped AirPods.",
    "compared_to_yesterday": "More AI governance legal news than yesterday; cybersecurity surge due to Canvas ransomware incident; hardware category grew with SpaceX chip announcement.",
    "day_over_day": {
      "rising_categories": ["cybersecurity", "hardware"],
      "falling_categories": ["startup"],
      "new_trends": ["AI safety features", "education platform security"]
    }
  }
}
```

**Fields:**
- `top_topic`: string — AI-generated summary of the single most important topic
- `trending_keywords`: string[] — top 3-10 keywords
- `category_breakdown`: { category_name: count } — counts per category
- `summary`: string — 2-3 sentence narrative summary of today's news landscape
- `compared_to_yesterday`: string — what's different from yesterday (optional, empty string if no yesterday data)
- `day_over_day`: optional dict with:
  - `rising_categories`: categories with more items than yesterday
  - `falling_categories`: categories with fewer items
  - `new_trends`: new/emerging themes not seen yesterday

---

## 2. AI Call Design

### 2.1 Modified Batch Prompt (includes recommendation)

Extend the existing `_process_batch` method's prompt to also request `recommendation`:

```python
# In BATCH_PROMPT_TEMPLATE, update the field spec:
"For each item, output: {\"relevance_score\": float, \"category\": str, \"summary\": str, \"english_title\": str, \"insight\": str, \"recommendation\": {\"level\": \"must_read|recommended|notable\", \"read_time\": \"X min\", \"relevance_to_tech\": \"high|medium|low\"}}"
```

**Recommendation level assignment rules (prompt instructions to AI):**
- `must_read`: High impact, broad relevance to IT professionals; changes how people think about a topic
- `recommended`: Important but niche; specific to a sub-field (e.g., cybersecurity, AI research)
- `notable`: Interesting but low urgency; peripheral tech news

### 2.2 New Method: `analyze_trends(items, yesterday_items?)`

Add a new method to `AIFilter` that makes ONE additional API call after all batches are processed:

```python
def analyze_trends(self, items: List[NewsItem], yesterday_items: Optional[List[Dict]] = None) -> Dict:
```

**Trend Analysis Prompt:**

```
SYSTEM: You are a tech news analyst. Given today's curated news items, produce a global trend analysis.

For each batch of items, analyze trends and output a single JSON with:
1. top_topic: The single most important topic/story today (1 sentence)
2. trending_keywords: 3-10 keywords capturing what's trending
3. category_breakdown: count of items per category (infer from titles)
4. summary: A 2-3 sentence narrative summary of today's tech landscape
5. compared_to_yesterday: If yesterday's top_topic is provided, what changed? (empty string if not available)
6. day_over_day: If yesterday data is available:
   - rising_categories: categories with more items today
   - falling_categories: categories with fewer items
   - new_trends: new themes emerging today

Output ONLY a JSON object. No markdown, no explanations.
```

**Prompt Template:**

```
USER: Analyze these {count} news items and output a single JSON trend analysis:

Title: {title1}
Category: {cat1}

Title: {title2}
Category: {cat2}
...

Yesterday's top topic: {yesterday_top_topic or "N/A"}
Yesterday's category breakdown: {yesterday_breakdown or "N/A"}
```

**Cost Analysis:** ~200-400 tokens for the trend analysis (much cheaper than batch processing). One additional API call per run.

### 2.3 Integration in AIFilter.process()

The `process()` method grows to return two things — the enriched items AND the trend analysis. Since Python methods can't easily return two things through the existing main.py pipeline, use the simplest approach: **store trend analysis as an attribute** on the AIFilter instance.

```python
class AIFilter:
    def process(self, items: List[NewsItem]) -> List[NewsItem]:
        # ... existing batch processing ...
        # After all batches:
        self.trend_analysis = self.analyze_trends(filtered_items, yesterday_items)
        return filtered_items
```

---

## 3. File Change Checklist

### 3.1 `collectors/base.py` — NO CHANGES NEEDED
NewsItem dataclass is fine as-is; `raw_data` dict stores `recommendation`.

### 3.2 `processors/ai_filter.py` — CHANGES NEEDED
1. Update `BATCH_PROMPT_TEMPLATE` to request `recommendation` field
2. Update `_process_batch()` to parse `recommendation` from response and store in `item.raw_data["recommendation"]`
3. Add new method `_load_yesterday_items()` to load previous day's archive for comparison
4. Add new method `analyze_trends()` with its own prompt and API call
5. Add `self.trend_analysis = None` in `__init__`
6. In `process()`, after batch enrichment, call `analyze_trends()`

### 3.3 `publishers/blog_generator.py` — CHANGES NEEDED
1. In `_save_archive()`, add `recommendation` field to each item and `trend_analysis` at top level
2. Accept `trend_analysis` as a parameter in `generate()`
3. Pass `trend_analysis` to template data
4. Sort items within each category by recommendation level (must_read first, then recommended, then notable)

### 3.4 `templates/blog.html` — CHANGES NEEDED
1. **Trend Panel** (top of page, below header, before date nav):
   - "📊 Today's Trend" section
   - Top topic badge/pill
   - Keyword chips
   - Category breakdown bar chart (simple colored bars with counts)
   - Summary text
   - "Compared to yesterday" callout (conditionally shown)
2. **Recommendation Badge on Cards:**
   - must_read: 🔴 "Must Read" badge
   - recommended: 🟡 "Recommended" badge
   - notable: 🔵 "Notable" badge
3. **Sort within categories:** must_read → recommended → notable (by recommendation level, then by relevance_score descending)
4. **JS SPA:** Update `renderItems()` to handle recommendation data and sort

### 3.5 `publishers/telegram.py` — CHANGES NEEDED
1. Accept `trend_analysis` parameter in `publish()`
2. Add trend summary block to the message (before category breakdown):
   ```
   📊 **Today's Trend:** {top_topic}
   🔑 Keywords: {keyword1}, {keyword2}, {keyword3}
   {compared_to_yesterday}
   ```

### 3.6 `main.py` — CHANGES NEEDED
1. After `ai_filter.process()`, extract `trend_analysis` from the filter object:
   ```python
   trend_analysis = getattr(ai_filter, 'trend_analysis', None)
   ```
2. Pass `trend_analysis` to `BlogGenerator.generate()` and `TelegramPublisher.publish()`

### 3.7 `newsletter/mailer.py` — OPTIONAL ENHANCEMENT
Optionally add trend summary to the email newsletter template.

### 3.8 `regenerate_all.py` — NO CHANGES NEEDED
Only regenerates pages; trend_analysis will be missing from old archives but handled gracefully.

---

## 4. Key API Design

### 4.1 AIFilter — New API Surface

```python
class AIFilter:
    def __init__(self, config: dict):
        # ... existing ...
        self.trend_analysis: Optional[Dict] = None  # NEW

    def process(self, items: List[NewsItem]) -> List[NewsItem]:
        """Existing process + post-process trend analysis."""
        # ... existing batch processing with RECOMMENDATION field ...
        
        # NEW: After all batches, run trend analysis
        if self.is_available() and items:
            yesterday_items = self._load_yesterday_items()
            self.trend_analysis = self._analyze_trends(items, yesterday_items)
        
        return filtered_items

    def _analyze_trends(self, items: List[NewsItem], 
                        yesterday_items: Optional[List[Dict]] = None) -> Dict:
        """Single API call for global trend analysis."""
        # Build prompt with item titles+categories
        # Include yesterday's data if available
        # Call DeepSeek API
        # Parse and return trend_analysis dict

    def _load_yesterday_items(self) -> Optional[Dict]:
        """Load previous day's archive JSON for comparison."""
        # Look in docs/archive/ for yesterday's date
        # Return {top_topic, category_breakdown} if found
```

### 4.2 BlogGenerator — New API Surface

```python
class BlogGenerator:
    def generate(self, items: List[NewsItem], 
                 date_str: Optional[str] = None,
                 trend_analysis: Optional[Dict] = None) -> str:
        # ... existing ...
        # Pass trend_analysis to template data
        # Sort items by recommendation level within categories
```

### 4.3 TelegramPublisher — New API Surface

```python
class TelegramPublisher:
    def publish(self, items: List[NewsItem], blog_url: str,
                trend_analysis: Optional[Dict] = None) -> bool:
        # ... existing with trend summary added ...
```

---

## 5. Backward Compatibility

### 5.1 Old archive JSON without trend_analysis
The `trend_analysis` field is optional at the top level of archive JSON. When loading old archives:

- **Python side:** `data.get("trend_analysis", None)` — default to None
- **Template side:** `{% if trend_analysis %}` — conditionally render the trend panel
- **JS SPA side:** In `loadDate()`, check if `data.trend_analysis` exists before rendering

### 5.2 Old archive JSON without recommendation per item
- **Python side:** `item.raw_data.get("recommendation", {}).get("level", "notable")`
- **Template/JS side:** default to "notable" level, no badge shown if recommendation is missing

### 5.3 SPA Client-Side Rendering
The JS `renderItems()` function needs to:
1. Check `item.recommendation` existence
2. Sort items within each category: must_read > recommended > notable
3. Render the recommendation badge if present

```javascript
function getRecommendationSortOrder(item) {
    const level = (item.recommendation && item.recommendation.level) || 'notable';
    const order = { must_read: 0, recommended: 1, notable: 2 };
    return order[level] || 2;
}

// In renderItems(), sort catItems:
catItems.sort((a, b) => {
    const orderA = getRecommendationSortOrder(a);
    const orderB = getRecommendationSortOrder(b);
    if (orderA !== orderB) return orderA - orderB;
    return (b.relevance_score || 0) - (a.relevance_score || 0);
});
```

For trend_analysis in SPA:
```javascript
function renderTrendPanel(analysis) {
    if (!analysis) return '';
    return `
        <div class="trend-panel">
            <div class="trend-header">📊 Today's Trend</div>
            <div class="trend-topic">${analysis.top_topic}</div>
            <div class="trend-keywords">
                ${analysis.trending_keywords.map(k => `<span class="keyword-chip">${k}</span>`).join('')}
            </div>
            <div class="trend-summary">${analysis.summary}</div>
            ${analysis.compared_to_yesterday ? `
                <div class="trend-compared">
                    <strong>📈 Compared to yesterday:</strong> ${analysis.compared_to_yesterday}
                </div>
            ` : ''}
        </div>
    `;
}
```

### 5.4 Server-rendered pages (SEO)
The Jinja2 template renders the trend panel server-side when `trend_analysis` is provided, so it's included in the initial HTML for crawlers.

---

## 6. Recommendation Sorting Algorithm

### 6.1 Two-Factor Sort

Items within each category are sorted by:

1. **Primary:** Recommendation level (must_read = 0, recommended = 1, notable = 2)
2. **Secondary:** `relevance_score` (descending) — already computed by AIFilter

```python
RECOMMENDATION_ORDER = {
    "must_read": 0,
    "recommended": 1,
    "notable": 2,
}

def sort_key(item: NewsItem) -> tuple:
    rec = item.raw_data.get("recommendation", {})
    level = rec.get("level", "notable")
    return (RECOMMENDATION_ORDER.get(level, 2), -item.hot_score)
```

### 6.2 UI Treatment
- **must_read:** Red/orange badge "🔴 Must Read" — bold card border
- **recommended:** Yellow badge "🟡 Recommended" — normal card style
- **notable:** Gray/blue badge "🔵 Notable" — slightly muted style

### 6.3 Relevance Score Consideration
The `relevance_score` (0-1) from AIFilter is already mapped to `hot_score` (0-1000). Items with high relevance_score but placed as "notable" by the AI are edge cases. The `recommendation.level` from the AI is the primary sort — but a "notable" with 0.95 relevance_score will still appear before a "must_read" with 0.1 relevance_score within different categories.

Within the same category, the rule is: recommendation level first, then relevance_score within same level.

---

## 7. Implementation Steps (Recommended Order)

1. **`processors/ai_filter.py`:**
   - Add `recommendation` to `BATCH_PROMPT_TEMPLATE`
   - Parse `recommendation` in `_process_batch()` → store in `item.raw_data["recommendation"]`
   - Add `_load_yesterday_items()` → loads previous day's archive JSON
   - Add `_analyze_trends()` → makes one API call for trend analysis
   - Wire into `process()`: set `self.trend_analysis`

2. **`publishers/blog_generator.py`:**
   - Accept `trend_analysis` in `generate()`
   - Pass to template data
   - Save in `_save_archive()` at top level
   - Add `recommendation` to each item in archive JSON
   - Sort items by recommendation level within `_group_categories()`

3. **`templates/blog.html`:**
   - Add trend panel CSS
   - Add trend panel HTML (conditional on `trend_analysis`)
   - Add recommendation badge to card template
   - Update JS `renderItems()` for recommendation sort and badge rendering
   - Add JS `renderTrendPanel()` for SPA trend data

4. **`publishers/telegram.py`:**
   - Accept `trend_analysis` parameter
   - Add trend summary to message

5. **`main.py`:**
   - Extract `trend_analysis` after AI filter
   - Pass to `generate()` and `publish()`

6. **`tests/test_ai_filter.py`:**
   - Add tests for recommendation parsing
   - Add tests for `_analyze_trends()`

---

## 8. Summary of Impact

| Metric | Impact |
|--------|--------|
| **API calls per run** | +1 (trend analysis) |
| **Tokens per run** | ~+400 (trend prompt + response) |
| **Archive JSON size** | ~+10% (recommendation per item + trend_analysis) |
| **Template complexity** | Medium (trend panel CSS, badges, JS sort) |
| **Backward compat** | Full (optional fields, graceful fallback) |

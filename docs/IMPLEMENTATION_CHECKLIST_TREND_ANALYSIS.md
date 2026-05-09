# Implementation Plan: Trend Analysis & Recommended Reading

## Overview
Add AI-powered trend analysis and per-article recommendation to social-hotspot-daily.
1 additional API call per run. ~400 extra tokens. Fully backward-compatible.

## Files to Modify (in order)

### 1. processors/ai_filter.py (~30 lines added)
- [ ] Add `recommendation` field to `BATCH_PROMPT_TEMPLATE` (line 28)
  ```
  "recommendation": {"level": "must_read|recommended|notable", "read_time": "X min", "relevance_to_tech": "high|medium|low"}
  ```
- [ ] Add `self.trend_analysis = None` to `__init__` (after line 41)
- [ ] Parse `recommendation` from API response in `_process_batch()` (after line 113):
  ```python
  item.raw_data["recommendation"] = result.get("recommendation", {})
  ```
- [ ] Add `_load_yesterday_items()` method
- [ ] Add `_analyze_trends()` method with prompt + API call
- [ ] Call `_analyze_trends()` at end of `process()` (before return, after sort)

### 2. publishers/blog_generator.py (~20 lines added)
- [ ] Add `trend_analysis` parameter to `generate()` (line 81)
- [ ] Pass `trend_analysis` into template data dict (around line 142)
- [ ] Add `recommendation` to archive JSON in `_save_archive()` (line 67)
- [ ] Add `trend_analysis` to archive JSON top level (line 71)
- [ ] Sort items within each category by recommendation level (in generate(), line 91-95)

### 3. templates/blog.html (~60 lines added)
- [ ] **CSS**: Add `.trend-panel`, `.keyword-chip`, `.rec-badge`, `.rec-must-read`, etc.
- [ ] **Template HTML**: Add trend panel between `<header>` and date-nav (conditional)
- [ ] **Template HTML**: Add recommendation badge to card (conditional)
- [ ] **JS**: Add `renderTrendPanel()` function
- [ ] **JS**: Update `renderItems()` to sort by recommendation + render badges
- [ ] **JS**: Update `loadDate()` to handle trend_analysis from archive JSON

### 4. publishers/telegram.py (~10 lines added)
- [ ] Accept `trend_analysis` parameter in `publish()` (line 20)
- [ ] Add trend summary block to message (before category list, around line 35)

### 5. main.py (~5 lines added)
- [ ] Extract `trend_analysis` after AI filter (after line 79):
  ```python
  trend_analysis = getattr(ai_filter, 'trend_analysis', None)
  ```
- [ ] Pass to `generator.generate(filtered_items, trend_analysis=trend_analysis)` (line 85)
- [ ] Pass to `tg.publish(filtered_items, blog_url, trend_analysis=trend_analysis)` (line 122)

### 6. newsletter/mailer.py (OPTIONAL, ~10 lines)
- [ ] Add trend summary to email newsletter if desired

## No Changes Needed
- `collectors/base.py` — NewsItem stores recommendation in `raw_data` dict
- `processors/dedup.py` — Unaffected
- `regenerate_all.py` — Gracefully handles missing trend_analysis
- `config.yaml` — No new config keys required

## Testing
- Unit test: recommendation parsing in ai_filter
- Unit test: trend_analysis prompt construction
- Unit test: recommendation sorting in blog_generator
- Manual: verify backward compat with old archive JSONs
- Manual: verify SPA loads trend_analysis correctly

## Rollback
- Remove `trend_analysis` and `recommendation` from archive JSON → old template renders fine
- Old archives without these fields render gracefully (conditional checks)

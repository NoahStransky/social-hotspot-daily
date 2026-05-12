"""Social Hotspot Daily - Main entry point."""
import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv

from collectors import load_collectors
from processors.dedup import Deduplicator
from processors.ai_filter import AIFilter
from publishers.blog_generator import BlogGenerator
from publishers.telegram import TelegramPublisher
from newsletter.db import init_db, get_stats
from newsletter.mailer import generate_newsletter_html, send_newsletter


def load_config():
    """Load config with environment variable substitution."""
    config_path = Path(__file__).parent / "config.yaml"
    
    if not config_path.exists():
        print("Error: config.yaml not found")
        sys.exit(1)
    
    raw = config_path.read_text()
    
    # Simple env var substitution: ${VAR} -> value
    # Supports ${VAR:-default} for optional vars with defaults
    import re
    def replace_env(match):
        var = match.group(1)
        if ":-" in var:
            name, default = var.split(":-", 1)
            return os.environ.get(name, default)
        return os.environ.get(var, "")
    
    raw = re.sub(r'\$\{([^}]+)\}', replace_env, raw)
    return yaml.safe_load(raw)


def main():
    load_dotenv()
    config = load_config()
    
    print("=" * 50)
    print("🚀 Social Hotspot Daily - Starting collection")
    print("=" * 50)
    
    # 1. Collect from all sources
    all_items = []
    collectors = load_collectors(config)
    
    for collector in collectors:
        if not collector.is_available():
            print(f"[Skip] {collector.name} (disabled or misconfigured)")
            continue
        
        print(f"[Collecting] {collector.name}...")
        try:
            items = collector.collect()
            print(f"  → {len(items)} items")
            all_items.extend(items)
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print(f"\n📊 Total raw items: {len(all_items)}")
    
    if not all_items:
        print("No items collected, exiting")
        sys.exit(0)
    
    # 2. Deduplicate
    dedup = Deduplicator()
    unique_items = dedup.deduplicate(all_items)
    print(f"🔍 After dedup: {len(unique_items)}")
    
    # 3. AI filtering & enrichment
    ai_config = config.get("ai_filter", {})
    ai_config["api_key"] = config.get("deepseek", {}).get("api_key", "")
    ai_config["model"] = config.get("deepseek", {}).get("model", "deepseek-chat")
    ai_config["output_dir"] = "docs"
    
    ai_filter = AIFilter(ai_config)
    filtered_items = ai_filter.process(unique_items)
    print(f"🤖 After AI filter: {len(filtered_items)}")

    # Get trend analysis from AI filter
    trend_analysis = getattr(ai_filter, 'trend_analysis', None)
    if trend_analysis:
        print(f"📊 Trend analysis: {trend_analysis.get('top_topic', 'N/A')}")

    # 4. Generate blog
    blog_config = config.get("output", {}).get("blog", {})
    blog_config["analytics"] = config.get("analytics", {})
    generator = BlogGenerator(blog_config, output_dir="docs")
    page_path = generator.generate(filtered_items, trend_analysis=trend_analysis)
    blog_url = generator.get_page_url()
    print(f"📝 Blog generated: {page_path}")
    
    # 5. Send Newsletter
    print("\n📧 Newsletter Service")
    print("-" * 30)
    init_db()
    stats = get_stats()
    print(f"📊 Local subscribers: {stats['active']} active, {stats['pending_verification']} pending")

    from datetime import datetime, timezone
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    subject = f"📰 Tech Hotspot Daily — {date_str}"

    # Prepare email items
    email_items = []
    for item in filtered_items[:15]:  # Top 15 for email
        email_items.append({
            "title": item.raw_data.get("english_title", item.title),
            "url": item.url,
            "summary": item.summary,
            "insight": item.raw_data.get("insight", ""),
            "source": item.source_name,
            "category": item.category.replace("_", " ").title(),
        })

    html = generate_newsletter_html(email_items, date_str)
    result = send_newsletter(subject, html, test_mode=False)
    print(f"📧 Newsletter: {result['sent']} sent, {result['failed']} failed")
    
    # 6. Send Telegram notification
    tg_config = config.get("output", {}).get("telegram", {})
    tg = TelegramPublisher(tg_config)
    tg.publish(filtered_items, blog_url or "https://yourdomain.github.io/social-hotspot-daily/", trend_analysis=trend_analysis)
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()

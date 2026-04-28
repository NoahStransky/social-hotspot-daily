"""Tests for publishers/blog_generator.py."""
import json
from pathlib import Path

import pytest

from collectors.base import NewsItem
from publishers.blog_generator import BlogGenerator


class TestBlogGeneratorInit:
    """Tests for BlogGenerator initialization."""

    def test_creates_output_dir(self, tmp_path):
        output_dir = tmp_path / "test_output"
        assert not output_dir.exists()
        BlogGenerator({}, output_dir=str(output_dir))
        assert output_dir.exists()

    def test_default_output_dir(self):
        # Should not raise even if docs/ exists
        bg = BlogGenerator({})
        assert bg.output_dir.name == "docs"


class TestBlogGeneratorGenerate:
    """Tests for BlogGenerator.generate()."""

    def test_generates_index_html(self, tmp_path, blog_config):
        bg = BlogGenerator(blog_config, output_dir=str(tmp_path))
        items = [
            NewsItem(title="AI News", url="https://a.com", source="s", source_name="sn", category="artificial_intelligence"),
            NewsItem(title="Code News", url="https://b.com", source="s", source_name="sn", category="programming"),
        ]

        result = bg.generate(items)

        assert Path(result).exists()
        assert Path(result).name == "index.html"

    def test_generates_feed_json(self, tmp_path, blog_config):
        bg = BlogGenerator(blog_config, output_dir=str(tmp_path))
        items = [
            NewsItem(title="Test", url="https://test.com", source="rss", source_name="RSS", category="technology", summary="A summary", raw_data={"insight": "Important"}),
        ]

        bg.generate(items)

        feed_path = tmp_path / "feed.json"
        assert feed_path.exists()

        data = json.loads(feed_path.read_text())
        # feed.json is now a dict of date -> metadata
        assert "2026-04-28" in data or any(key.startswith("202") for key in data)
        today_key = [k for k in data if k.startswith("202")][0]
        assert data[today_key]["title"] == "Test Hotspot Daily"
        assert data[today_key]["total_items"] == 1

    def test_groups_by_category(self, tmp_path, blog_config):
        bg = BlogGenerator(blog_config, output_dir=str(tmp_path))
        items = [
            NewsItem(title="AI 1", url="https://a1.com", source="s", source_name="sn", category="artificial_intelligence"),
            NewsItem(title="AI 2", url="https://a2.com", source="s", source_name="sn", category="artificial_intelligence"),
            NewsItem(title="Code 1", url="https://c1.com", source="s", source_name="sn", category="programming"),
        ]

        bg.generate(items)

        html = (tmp_path / "index.html").read_text()
        assert "AI 1" in html or "Ai 1" in html
        assert "AI 2" in html or "Ai 2" in html
        assert "Code 1" in html or "code 1" in html

    def test_empty_items(self, tmp_path, blog_config):
        bg = BlogGenerator(blog_config, output_dir=str(tmp_path))
        result = bg.generate([])
        assert Path(result).exists()

        feed_path = tmp_path / "feed.json"
        data = json.loads(feed_path.read_text())
        # feed.json: dict of date -> metadata, archive has the items
        today_key = [k for k in data if k.startswith("202")][0]
        assert data[today_key]["total_items"] == 0

        # Archive JSON should have items
        archive_path = tmp_path / "archive"
        archive_files = list(archive_path.glob("*.json"))
        assert len(archive_files) >= 1

    def test_copies_static_pages(self, tmp_path, blog_config):
        # Only test if templates exist
        template_dir = Path(__file__).parent.parent / "templates"
        expected_pages = ["subscribe.html", "verify.html", "unsubscribe.html"]
        existing = [p for p in expected_pages if (template_dir / p).exists()]

        bg = BlogGenerator(blog_config, output_dir=str(tmp_path))
        bg.generate([])

        for page in existing:
            assert (tmp_path / page).exists()


class TestGetPageUrl:
    """Tests for BlogGenerator.get_page_url()."""

    def test_with_base_url(self):
        bg = BlogGenerator({"base_url": "https://example.com"})
        assert bg.get_page_url() == "https://example.com/"

    def test_without_base_url(self):
        bg = BlogGenerator({})
        assert bg.get_page_url() == ""

    def test_empty_base_url(self):
        bg = BlogGenerator({"base_url": ""})
        assert bg.get_page_url() == ""

"""Tests for main.py."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

import main


class TestLoadConfig:
    """Tests for load_config function."""

    def test_basic_load(self, tmp_path, monkeypatch):
        """Test loading a basic config file."""
        config_data = {"sources": {"hackernews": {"enabled": True}}, "output": {"blog": {}}}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.safe_dump(config_data))
        monkeypatch.setattr(main, "__file__", str(tmp_path / "main.py"))

        result = main.load_config()
        assert result == config_data

    def test_env_substitution(self, tmp_path, monkeypatch):
        """Test environment variable substitution ${VAR} -> value."""
        monkeypatch.setenv("TEST_API_KEY", "secret123")
        monkeypatch.setenv("TEST_MODEL", "gpt-4")

        config_content = "api_key: ${TEST_API_KEY}\nmodel: ${TEST_MODEL}\nmissing: ${MISSING_VAR}\n"
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        monkeypatch.setattr(main, "__file__", str(tmp_path / "main.py"))

        result = main.load_config()
        assert result["api_key"] == "secret123"
        assert result["model"] == "gpt-4"
        assert result["missing"] is None

    def test_file_not_found(self, tmp_path, monkeypatch):
        """Test sys.exit(1) when config.yaml is missing."""
        monkeypatch.setattr(main, "__file__", str(tmp_path / "main.py"))

        with pytest.raises(SystemExit) as exc_info:
            main.load_config()
        assert exc_info.value.code == 1


class TestMainFlow:
    """Tests for main() execution flow."""

    def test_main_no_items_collected(self, tmp_path, monkeypatch):
        """Test main() exits cleanly when no items are collected."""
        config_data = {
            "sources": {},
            "output": {"blog": {}},
            "ai_filter": {},
            "deepseek": {},
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.safe_dump(config_data))
        monkeypatch.setattr(main, "__file__", str(tmp_path / "main.py"))

        mock_collector = MagicMock()
        mock_collector.is_available.return_value = False

        with patch("main.load_collectors", return_value=[mock_collector]):
            with pytest.raises(SystemExit) as exc_info:
                main.main()
            assert exc_info.value.code == 0

    def test_main_with_items(self, tmp_path, monkeypatch, sample_news_items):
        """Test main() full flow with mocked dependencies."""
        config_data = {
            "sources": {"hackernews": {"enabled": True}},
            "output": {"blog": {}, "telegram": {"bot_token": "test", "chat_id": "test"}},
            "ai_filter": {},
            "deepseek": {"api_key": "***", "model": "model"},
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.safe_dump(config_data))
        monkeypatch.setattr(main, "__file__", str(tmp_path / "main.py"))

        mock_collector = MagicMock()
        mock_collector.is_available.return_value = True
        mock_collector.name = "hackernews"
        mock_collector.collect.return_value = sample_news_items

        mock_dedup = MagicMock()
        mock_dedup.deduplicate.return_value = sample_news_items

        mock_ai_filter = MagicMock()
        mock_ai_filter.process.return_value = sample_news_items

        mock_blog_gen = MagicMock()
        mock_blog_gen.generate.return_value = "docs/index.html"
        mock_blog_gen.get_page_url.return_value = "https://example.com/blog"

        mock_tg = MagicMock()

        with patch("main.load_collectors", return_value=[mock_collector]):
            with patch("main.Deduplicator", return_value=mock_dedup):
                with patch("main.AIFilter", return_value=mock_ai_filter):
                    with patch("main.BlogGenerator", return_value=mock_blog_gen):
                        with patch("main.TelegramPublisher", return_value=mock_tg):
                            with patch("main.init_db"):
                                with patch("main.get_stats", return_value={"active": 0, "pending_verification": 0}):
                                    # Should complete without SystemExit since active subscribers = 0
                                    main.main()

        mock_collector.collect.assert_called_once()
        mock_dedup.deduplicate.assert_called_once_with(sample_news_items)
        mock_ai_filter.process.assert_called_once_with(sample_news_items)
        mock_blog_gen.generate.assert_called_once_with(sample_news_items)
        mock_tg.publish.assert_called_once()

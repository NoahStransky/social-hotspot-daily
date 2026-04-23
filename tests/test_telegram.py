"""Tests for publishers/telegram.py."""
from unittest.mock import MagicMock, patch

import pytest

from publishers.telegram import TelegramPublisher


class TestTelegramPublisher:
    """Tests for the TelegramPublisher class."""

    def test_is_available_all_configured(self):
        config = {"enabled": True, "bot_token": "token123", "chat_id": "chat456"}
        publisher = TelegramPublisher(config)
        assert publisher.is_available() is True

    def test_is_available_disabled(self):
        config = {"enabled": False, "bot_token": "token123", "chat_id": "chat456"}
        publisher = TelegramPublisher(config)
        assert publisher.is_available() is False

    def test_is_available_no_token(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        config = {"enabled": True, "bot_token": "", "chat_id": "chat456"}
        publisher = TelegramPublisher(config)
        assert publisher.is_available() is False

    def test_is_available_no_chat_id(self):
        config = {"enabled": True, "bot_token": "token123", "chat_id": ""}
        publisher = TelegramPublisher(config)
        assert publisher.is_available() is False

    def test_is_available_no_token_no_chat_id(self):
        config = {"enabled": True}
        publisher = TelegramPublisher(config)
        assert publisher.is_available() is False

    def test_is_available_from_env(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "env_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "env_chat")
        config = {"enabled": True}
        publisher = TelegramPublisher(config)
        assert publisher.is_available() is True
        assert publisher.bot_token == "env_token"
        assert publisher.chat_id == "env_chat"
        assert publisher.api_base == "https://api.telegram.org/botenv_token"

    def test_publish_not_available(self, capsys):
        config = {"enabled": False}
        publisher = TelegramPublisher(config)
        result = publisher.publish([], "https://example.com/blog")
        assert result is False
        captured = capsys.readouterr()
        assert "[Telegram] Not configured, skipping" in captured.out

    def test_publish_success(self, sample_news_items):
        config = {"enabled": True, "bot_token": "token123", "chat_id": "chat456"}
        publisher = TelegramPublisher(config)
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"ok": True}

        with patch("publishers.telegram.requests.post", return_value=mock_resp) as mock_post:
            result = publisher.publish(sample_news_items, "https://example.com/blog")

        assert result is True
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["chat_id"] == "chat456"
        assert kwargs["json"]["parse_mode"] == "HTML"
        assert kwargs["json"]["disable_web_page_preview"] is False
        assert "https://example.com/blog" in kwargs["json"]["text"]
        assert "sendMessage" in args[0]

    def test_publish_api_error(self, sample_news_items, capsys):
        config = {"enabled": True, "bot_token": "token123", "chat_id": "chat456"}
        publisher = TelegramPublisher(config)
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"ok": False, "description": "Bad Request"}

        with patch("publishers.telegram.requests.post", return_value=mock_resp) as mock_post:
            result = publisher.publish(sample_news_items, "https://example.com/blog")

        assert result is False
        captured = capsys.readouterr()
        assert "[Telegram] API error" in captured.out

    def test_publish_request_exception(self, sample_news_items, capsys):
        config = {"enabled": True, "bot_token": "token123", "chat_id": "chat456"}
        publisher = TelegramPublisher(config)

        with patch("publishers.telegram.requests.post", side_effect=Exception("Connection error")):
            result = publisher.publish(sample_news_items, "https://example.com/blog")

        assert result is False
        captured = capsys.readouterr()
        assert "[Telegram] Error: Connection error" in captured.out

    def test_publish_empty_items(self):
        config = {"enabled": True, "bot_token": "token123", "chat_id": "chat456"}
        publisher = TelegramPublisher(config)
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"ok": True}

        with patch("publishers.telegram.requests.post", return_value=mock_resp) as mock_post:
            result = publisher.publish([], "https://example.com/blog")

        assert result is True
        args, kwargs = mock_post.call_args
        assert "0 tech stories" in kwargs["json"]["text"]

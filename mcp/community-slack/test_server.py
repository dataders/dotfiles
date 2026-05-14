import os
import sys
from unittest.mock import MagicMock, patch
import pytest


def _load_server(monkeypatch, token="xoxb-fake"):
    """Load (or reload) server module with a given token, cleaning up after the test."""
    monkeypatch.setenv("COMMUNITY_SLACK_BOT_TOKEN", token)
    sys.modules.pop("server", None)
    import server
    return server


def test_missing_token_raises(monkeypatch):
    monkeypatch.delenv("COMMUNITY_SLACK_BOT_TOKEN", raising=False)
    sys.modules.pop("server", None)
    with pytest.raises(SystemExit, match="COMMUNITY_SLACK_BOT_TOKEN"):
        import server  # noqa: F401


def test_fetch_messages_returns_list(monkeypatch):
    fake_page = {
        "messages": [
            {"ts": "1000.0001", "user": "U123", "text": "hello", "reply_count": 2, "thread_ts": "1000.0001"},
            {"ts": "1001.0001", "user": "U456", "text": "world", "reply_count": 0},
        ],
        "has_more": False,
        "response_metadata": {"next_cursor": ""},
    }
    server = _load_server(monkeypatch)
    server._channel_cache["dbt-fusion-engine"] = "C999"
    with patch.object(server.client, "conversations_history", return_value=fake_page):
        result = server._fetch_messages_impl(days=1, channel="dbt-fusion-engine")
    assert len(result) == 2
    assert result[0]["text"] == "hello"
    assert result[0]["reply_count"] == 2

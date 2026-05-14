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

#!/usr/bin/env python3
import os
import sys
from mcp.server.fastmcp import FastMCP
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

token = os.environ.get("COMMUNITY_SLACK_BOT_TOKEN")
if not token:
    print("COMMUNITY_SLACK_BOT_TOKEN not set", file=sys.stderr)
    sys.exit("COMMUNITY_SLACK_BOT_TOKEN not set")

client = WebClient(token=token)
mcp = FastMCP("community-slack")

_channel_cache: dict[str, str] = {}


def resolve_channel(name: str) -> str:
    name = name.lstrip("#")
    if name in _channel_cache:
        return _channel_cache[name]
    for page in client.conversations_list(types="public_channel", limit=200):
        for ch in page["channels"]:
            _channel_cache[ch["name"]] = ch["id"]
        if name in _channel_cache:
            return _channel_cache[name]
    raise ValueError(f"Channel #{name} not found. Is the bot invited?")


import time
from datetime import datetime, timedelta, timezone
from typing import Any


def _fetch_messages_impl(days: int = 7, channel: str = "dbt-fusion-engine") -> list[dict[str, Any]]:
    channel_id = resolve_channel(channel)
    oldest = str((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    messages = []
    cursor = None
    while True:
        kwargs: dict[str, Any] = {"channel": channel_id, "oldest": oldest, "limit": 200}
        if cursor:
            kwargs["cursor"] = cursor
        resp = client.conversations_history(**kwargs)
        for msg in resp.get("messages", []):
            messages.append({
                "ts": msg["ts"],
                "user": msg.get("user", ""),
                "text": msg.get("text", ""),
                "thread_ts": msg.get("thread_ts"),
                "reply_count": msg.get("reply_count", 0),
            })
        meta = resp.get("response_metadata", {})
        cursor = meta.get("next_cursor") if resp.get("has_more") else None
        if not cursor:
            break
    return messages


@mcp.tool()
def fetch_messages(days: int = 7, channel: str = "dbt-fusion-engine") -> list[dict[str, Any]]:
    """Fetch all messages from a Slack channel for the past N days."""
    return _fetch_messages_impl(days=days, channel=channel)


if __name__ == "__main__":
    mcp.run(transport="stdio")

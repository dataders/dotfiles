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


if __name__ == "__main__":
    mcp.run(transport="stdio")

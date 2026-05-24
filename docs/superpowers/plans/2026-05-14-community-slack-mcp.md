# Community Slack MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local MCP server that exposes `fetch_messages` and `fetch_thread` tools for reading the #dbt-fusion-engine channel in getdbt.slack.com.

**Architecture:** Single-file Python MCP server (`server.py`) invoked via a `run.sh` wrapper that sources `dotfiles_env/secrets.zsh` to inject the bot token. The server uses stdio transport (standard for local MCP). Channel IDs are resolved by name at startup and cached. Registered in both Claude Desktop and Claude Code CLI configs.

**Tech Stack:** Python 3.12+, `slack-sdk`, `mcp` (Anthropic's Python MCP library), `uv run --with` (no pyproject.toml)

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `mcp/community-slack/server.py` | MCP server — tools, Slack API calls, channel ID cache |
| Create | `mcp/community-slack/run.sh` | Wrapper — sources secrets, execs uv run server.py |
| Modify | `.config/claude/claude_desktop_config.json` | Register `community-slack` MCP server |
| Modify | `.claude/settings.json` | Register `community-slack` MCP server |

---

## Prerequisites (manual, before running any task)

1. Ensure the Kapa Slack Bot token has scopes `channels:history` and `channels:read` on getdbt.slack.com
2. Invite the bot to #dbt-fusion-engine: `/invite @KapaSlackBot` in that channel
3. Add to `~/Developer/dotfiles_env/secrets.zsh`:
   ```bash
   export COMMUNITY_SLACK_BOT_TOKEN=xoxb-your-token-here
   ```
4. Reload secrets: `source ~/Developer/dotfiles_env/secrets.zsh`

---

## Task 1: Create the MCP server skeleton with token validation

**Files:**
- Create: `mcp/community-slack/server.py`

- [ ] **Step 1: Write a failing test for token validation**

  Create `mcp/community-slack/test_server.py`:
  ```python
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
  ```

- [ ] **Step 2: Run test to verify it fails**

  ```bash
  cd mcp/community-slack
  uv run --with mcp --with slack-sdk --with pytest pytest test_server.py::test_missing_token_raises -v
  ```
  Expected: `ModuleNotFoundError` or `ImportError` — server.py doesn't exist yet.

- [ ] **Step 3: Write the server skeleton**

  Create `mcp/community-slack/server.py`:
  ```python
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

  # channel name → id cache
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
  ```

- [ ] **Step 4: Run test to verify it passes**

  ```bash
  uv run --with mcp --with slack-sdk --with pytest pytest test_server.py::test_missing_token_raises -v
  ```
  Expected: `PASSED`

- [ ] **Step 5: Commit**

  ```bash
  git add mcp/community-slack/server.py mcp/community-slack/test_server.py
  git commit -m "feat: add community-slack MCP server skeleton with token validation"
  ```

---

## Task 2: Implement `fetch_messages` tool

**Files:**
- Modify: `mcp/community-slack/server.py`
- Modify: `mcp/community-slack/test_server.py`

- [ ] **Step 1: Write a failing test**

  Add to `test_server.py` (note: `_load_server`, `sys`, `MagicMock`, `patch` are already imported from Task 1):
  ```python
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
  ```

- [ ] **Step 2: Run test to verify it fails**

  ```bash
  uv run --with mcp --with slack-sdk --with pytest pytest test_server.py::test_fetch_messages_returns_list -v
  ```
  Expected: `AttributeError: module 'server' has no attribute '_fetch_messages_impl'`

- [ ] **Step 3: Implement `fetch_messages`**

  Add to `server.py` (before `if __name__ == "__main__":`):
  ```python
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
  ```

- [ ] **Step 4: Run test to verify it passes**

  ```bash
  uv run --with mcp --with slack-sdk --with pytest pytest test_server.py::test_fetch_messages_returns_list -v
  ```
  Expected: `PASSED`

- [ ] **Step 5: Commit**

  ```bash
  git add mcp/community-slack/server.py mcp/community-slack/test_server.py
  git commit -m "feat: add fetch_messages tool to community-slack MCP"
  ```

---

## Task 3: Implement `fetch_thread` tool

**Files:**
- Modify: `mcp/community-slack/server.py`
- Modify: `mcp/community-slack/test_server.py`

- [ ] **Step 1: Write a failing test**

  Add to `test_server.py`:
  ```python
  def test_fetch_thread_returns_replies(monkeypatch):
      fake_resp = {
          "messages": [
              {"ts": "1000.0001", "user": "U123", "text": "parent"},
              {"ts": "1000.0002", "user": "U456", "text": "reply 1"},
              {"ts": "1000.0003", "user": "U789", "text": "reply 2"},
          ],
          "has_more": False,
          "response_metadata": {"next_cursor": ""},
      }
      server = _load_server(monkeypatch)
      server._channel_cache["dbt-fusion-engine"] = "C999"
      with patch.object(server.client, "conversations_replies", return_value=fake_resp):
          result = server._fetch_thread_impl(thread_ts="1000.0001", channel="dbt-fusion-engine")
      # parent message excluded, only replies
      assert len(result) == 2
      assert result[0]["text"] == "reply 1"
  ```

- [ ] **Step 2: Run test to verify it fails**

  ```bash
  uv run --with mcp --with slack-sdk --with pytest pytest test_server.py::test_fetch_thread_returns_replies -v
  ```
  Expected: `AttributeError: module 'server' has no attribute '_fetch_thread_impl'`

- [ ] **Step 3: Implement `fetch_thread`**

  Add to `server.py`:
  ```python
  def _fetch_thread_impl(thread_ts: str, channel: str = "dbt-fusion-engine") -> list[dict[str, Any]]:
      channel_id = resolve_channel(channel)
      replies = []
      cursor = None
      while True:
          kwargs: dict[str, Any] = {"channel": channel_id, "ts": thread_ts, "limit": 200}
          if cursor:
              kwargs["cursor"] = cursor
          resp = client.conversations_replies(**kwargs)
          msgs = resp.get("messages", [])
          # first message is the parent — skip it
          for msg in msgs[1:] if not cursor else msgs:
              replies.append({
                  "ts": msg["ts"],
                  "user": msg.get("user", ""),
                  "text": msg.get("text", ""),
              })
          meta = resp.get("response_metadata", {})
          cursor = meta.get("next_cursor") if resp.get("has_more") else None
          if not cursor:
              break
      return replies

  @mcp.tool()
  def fetch_thread(thread_ts: str, channel: str = "dbt-fusion-engine") -> list[dict[str, Any]]:
      """Fetch all replies in a Slack thread given a message timestamp."""
      return _fetch_thread_impl(thread_ts=thread_ts, channel=channel)
  ```

- [ ] **Step 4: Run test to verify it passes**

  ```bash
  uv run --with mcp --with slack-sdk --with pytest pytest test_server.py::test_fetch_thread_returns_replies -v
  ```
  Expected: `PASSED`

- [ ] **Step 5: Commit**

  ```bash
  git add mcp/community-slack/server.py mcp/community-slack/test_server.py
  git commit -m "feat: add fetch_thread tool to community-slack MCP"
  ```

---

## Task 4: Create `run.sh` wrapper

**Files:**
- Create: `mcp/community-slack/run.sh`

- [ ] **Step 1: Write `run.sh`**

  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  # Source private secrets (token lives here, not in tracked dotfiles)
  SECRETS="$HOME/Developer/dotfiles_env/secrets.zsh"
  if [[ -f "$SECRETS" ]]; then
    source "$SECRETS"
  fi
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  exec uv run \
    --with slack-sdk \
    --with mcp \
    "$SCRIPT_DIR/server.py"
  ```

- [ ] **Step 2: Make executable**

  ```bash
  chmod +x mcp/community-slack/run.sh
  ```

- [ ] **Step 3: Smoke-test (token must be set)**

  Send a minimal JSON-RPC init message and check the process doesn't exit immediately with a token error:
  ```bash
  echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}' \
    | timeout 10 env COMMUNITY_SLACK_BOT_TOKEN=xoxb-fake \
      uv run --with slack-sdk --with mcp mcp/community-slack/server.py \
    | head -1
  ```
  Expected: JSON response line (not `COMMUNITY_SLACK_BOT_TOKEN not set`). First run may be slow while uv downloads deps — that's fine.

- [ ] **Step 4: Commit**

  ```bash
  git add mcp/community-slack/run.sh
  git commit -m "feat: add run.sh wrapper sourcing dotfiles_env secrets for community-slack MCP"
  ```

---

## Task 5: Register in Claude Desktop and Claude Code CLI

**Files:**
- Modify: `.config/claude/claude_desktop_config.json`
- Modify: `.claude/settings.json`

- [ ] **Step 1: Add to Claude Desktop config**

  In `.config/claude/claude_desktop_config.json`, add under `"mcpServers"`:
  ```json
  "community-slack": {
    "command": "/Users/dataders/Developer/dotfiles/mcp/community-slack/run.sh",
    "args": []
  }
  ```

- [ ] **Step 2: Add to Claude Code CLI settings**

  In `.claude/settings.json`, add a top-level `"mcpServers"` key if absent, then add:
  ```json
  "mcpServers": {
    "community-slack": {
      "command": "/Users/dataders/Developer/dotfiles/mcp/community-slack/run.sh",
      "args": [],
      "type": "stdio"
    }
  }
  ```

- [ ] **Step 3: Verify symlink targets are correct**

  ```bash
  ./links.sh check
  ```
  Expected: no broken links.

- [ ] **Step 4: Restart Claude Desktop**

  Quit and relaunch Claude Desktop. Open a new chat and confirm `community-slack` appears in the MCP tools list.

- [ ] **Step 5: Commit**

  ```bash
  git add .config/claude/claude_desktop_config.json .claude/settings.json
  git commit -m "feat: register community-slack MCP in Claude Desktop and Claude Code CLI"
  ```

---

## Task 6: End-to-end smoke test with real token

> **Note:** All steps in this task must run in the same shell session after sourcing secrets — child processes inherit the env var from the parent shell.

- [ ] **Step 1: Verify token is loaded**

  ```bash
  source ~/Developer/dotfiles_env/secrets.zsh
  echo $COMMUNITY_SLACK_BOT_TOKEN | cut -c1-10
  ```
  Expected: `xoxb-` prefix visible.

- [ ] **Step 2: Test channel resolution**

  ```bash
  source ~/Developer/dotfiles_env/secrets.zsh
  uv run --with slack-sdk --with mcp python -c "
  import os; os.environ['COMMUNITY_SLACK_BOT_TOKEN'] = os.environ['COMMUNITY_SLACK_BOT_TOKEN']
  import sys; sys.path.insert(0, 'mcp/community-slack')
  import server
  print(server.resolve_channel('dbt-fusion-engine'))
  "
  ```
  Expected: a Slack channel ID like `C0XXXXXXX`.

- [ ] **Step 3: Fetch a day of messages**

  ```bash
  uv run --with slack-sdk --with mcp python -c "
  import os, json, sys
  sys.path.insert(0, 'mcp/community-slack')
  import server
  msgs = server._fetch_messages_impl(days=1)
  print(json.dumps(msgs[:3], indent=2))
  print(f'Total: {len(msgs)} messages')
  "
  ```
  Expected: JSON list of messages, count > 0.

- [ ] **Step 4: Fetch a thread (use a ts from step 3 with reply_count > 0)**

  ```bash
  uv run --with slack-sdk --with mcp python -c "
  import os, json, sys
  sys.path.insert(0, 'mcp/community-slack')
  import server
  msgs = server._fetch_messages_impl(days=7)
  threaded = [m for m in msgs if m['reply_count'] > 0]
  if threaded:
      replies = server._fetch_thread_impl(threaded[0]['ts'])
      print(json.dumps(replies[:3], indent=2))
  else:
      print('no threads in last 7 days')
  "
  ```
  Expected: list of reply messages.

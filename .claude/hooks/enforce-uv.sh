#!/usr/bin/env bash
# PreToolUse hook: block bare pip/pip3/python3 invocations in favor of uv
# Reads tool input JSON from stdin (Claude Code hook protocol)

input=$(cat)
cmd=$(echo "$input" | jq -r '.tool_input.command // empty')

# Block pip/pip3
if echo "$cmd" | grep -qE '(^|[[:space:];&|`])(pip3?)[[:space:]]'; then
  echo "Blocked: use 'uvx <tool>' or 'uv add <pkg>' instead of pip" >&2
  exit 2
fi

# Block bare python3 not wrapped in uv run
if echo "$cmd" | grep -qE '(^|[[:space:];&|`])python3[[:space:]]' \
  && ! echo "$cmd" | grep -qE 'uv (run|tool)'; then
  echo "Blocked: use 'uv run python3 ...' instead of bare python3" >&2
  exit 2
fi

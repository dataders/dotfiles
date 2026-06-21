#!/usr/bin/env bash
# PreToolUse(Bash) hook: in a background session, GUI `open` can't reach the
# user's display — it fires into the void (the agent thinks it opened a browser
# tab; nothing happens). Block it and tell the agent to print the URL instead.
#
# Only intervenes when CLAUDE_JOB_DIR is set (i.e. a background job). Interactive
# foreground sessions are left alone, where `open` works fine.
set -euo pipefail

input=$(cat)

# Not a background session → allow.
[ -n "${CLAUDE_JOB_DIR:-}" ] || exit 0

cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')

# Match `open` used as a command word: at line start or right after a shell
# separator (; & |, which also covers && and ||), followed by whitespace.
# Avoids false positives like `openssl`, `xdg-open-tool`, `fopen`.
if printf '%s' "$cmd" | grep -Eq '(^|[;&|])[[:space:]]*open[[:space:]]'; then
  cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"This is a background session — `open` cannot reach the user's display, so it silently does nothing. Do NOT run it. Instead, print the URL/path as a clickable link in your reply, and optionally tell the user they can run `! open <url>` from their own prompt to open it themselves."}}
JSON
fi
exit 0

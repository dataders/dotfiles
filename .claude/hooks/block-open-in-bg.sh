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
  # Linux remote boxes: xdg-open goes through the SSH URL relay to the Mac and
  # works from background sessions, so steer the agent there instead.
  if [ "$(uname -s)" = Linux ] && grep -q 'url-open-relay' "$HOME/.local/bin/xdg-open" 2>/dev/null; then
    cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"On this Linux box `open` is not a browser opener. Use `xdg-open <url>` instead: it goes through the SSH URL relay to the user's Mac and works from background sessions, including OAuth loopback callbacks. Also print the URL as a clickable link in case the relay is down."}}
JSON
    exit 0
  fi
  cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"This is a background session — `open` cannot reach the user's display, so it silently does nothing. Do NOT run it. Instead, print the URL/path as a clickable link in your reply, and optionally tell the user they can run `! open <url>` from their own prompt to open it themselves."}}
JSON
fi
exit 0

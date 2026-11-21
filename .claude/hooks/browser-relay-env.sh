#!/usr/bin/env bash
# SessionStart hook: Claude Code background/agent sessions export BROWSER=true,
# which turns browser-based OAuth (Snowflake externalbrowser, gcloud, gh, ...)
# into a silent no-op. On the Linux remote boxes the xdg-open shim reaches the
# Mac through the SSH URL relay, so point BROWSER back at it for Bash commands.
#
# Only acts on Linux, and only when the relay shim is installed. macOS and boxes
# without the shim are left alone.
set -euo pipefail

[ "$(uname -s)" = Linux ] || exit 0
[ -n "${CLAUDE_ENV_FILE:-}" ] || exit 0

shim="$HOME/.local/bin/xdg-open"
[ -x "$shim" ] && grep -q 'url-open-relay' "$shim" 2>/dev/null || exit 0

# The user and project settings can both run this hook; write the line once.
line="$(printf 'export BROWSER=%q' "$shim")"
grep -qxF "$line" "$CLAUDE_ENV_FILE" 2>/dev/null || printf '%s\n' "$line" >> "$CLAUDE_ENV_FILE"
exit 0

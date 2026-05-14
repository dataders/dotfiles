#!/usr/bin/env bash
set -euo pipefail
SECRETS="$HOME/Developer/dotfiles_env/secrets.zsh"
if [[ -f "$SECRETS" ]]; then
  source "$SECRETS"
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec uv run \
  --with slack-sdk \
  --with mcp \
  "$SCRIPT_DIR/server.py"

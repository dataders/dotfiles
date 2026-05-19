#!/usr/bin/env bash
set -euo pipefail
SECRETS="$HOME/Developer/dotfiles_env/secrets.zsh"
if [[ -f "$SECRETS" ]]; then
  source "$SECRETS"
fi
exec npx -y mcp-remote https://search.parallel.ai/mcp \
  --header "Authorization: Bearer $PARALLEL_API_KEY"

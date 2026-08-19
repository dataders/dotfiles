#!/usr/bin/env bash
#
# Refresh a remote host's dotfiles + dotfiles_env checkout and re-apply the
# managed symlinks in remote/links.tsv. Safe to re-run any time either repo
# changes locally — this is the "just refresh peach01" command.
#
# Usage: remote/sync-env.sh <hostname>
#
# Expects:
#   - SSH access to <hostname> (key-based auth, agent forwarding for the
#     `git pull` over SSH to GitHub)
#   - ~/Developer/dotfiles already cloned on <hostname> (run setup.sh once
#     first if not)
#
# Run from the dotfiles repo root: remote/sync-env.sh peach01

set -euo pipefail

HOST="${1:?Usage: $0 <hostname>}"
ENV_DIR="${HOME}/Developer/dotfiles_env"

echo "==> Refreshing ${HOST}"

echo "--- Pulling dotfiles (public config)..."
ssh "$HOST" 'cd ~/Developer/dotfiles && git pull --ff-only' || echo "git pull failed on ${HOST} — resolve manually (local changes or diverged history?)"

if [[ -d "$ENV_DIR" ]]; then
    echo "--- Syncing dotfiles_env (private config)..."
    rsync -avz "$ENV_DIR/" "${HOST}:~/Developer/dotfiles_env/"
else
    echo "--- Skipping dotfiles_env sync (${ENV_DIR} not found locally)"
fi

echo "--- Re-applying managed symlinks (remote/links.tsv)..."
ssh "$HOST" 'cd ~/Developer/dotfiles && DOTFILES_MANIFEST=remote/links.tsv ./links.sh apply'

echo ""
echo "==> Done. Verify with:"
echo "    ssh ${HOST} 'cd ~/Developer/dotfiles && DOTFILES_MANIFEST=remote/links.tsv ./links.sh check'"

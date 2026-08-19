#!/usr/bin/env bash
#
# Bootstrap a remote Linux machine with Anders' shell environment.
# Usage: ./setup.sh <hostname>
#
# Expects SSH access to <hostname> (key-based auth).
# Run from the dotfiles repo root: remote/setup.sh nectarine01
#
set -euo pipefail

HOST="${1:?Usage: $0 <hostname>}"
REMOTE_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Setting up shell environment on ${HOST}"

# ─────────────────────────────────────────────────────────────────────────────
# 1. Install system packages (zsh, tmux, jq)
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Installing system packages..."
ssh "$HOST" 'sudo apt-get install -y -qq zsh tmux jq 2>/dev/null || echo "apt install failed — some packages may already be present"'

# ─────────────────────────────────────────────────────────────────────────────
# 1b. Install fzf + Node.js/npm without sudo (user-local, so a host without
#     apt access for the caller still ends up with a working environment)
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Installing fzf (user-local)..."
ssh "$HOST" 'command -v fzf >/dev/null 2>&1 || { [[ -d ~/.fzf ]] || git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf; ~/.fzf/install --bin --no-update-rc --no-key-bindings --no-completion; mkdir -p ~/.local/bin; ln -sf ~/.fzf/bin/fzf ~/.local/bin/fzf; }'

echo "--- Installing Node.js/npm (user-local)..."
ssh "$HOST" 'command -v node >/dev/null 2>&1 || { NODE_VERSION=$(curl -fsSL https://nodejs.org/dist/index.json | jq -r "map(select(.lts != false)) | .[0].version"); mkdir -p ~/.local; curl -fsSL "https://nodejs.org/dist/${NODE_VERSION}/node-${NODE_VERSION}-linux-x64.tar.xz" | tar -xJ -C ~/.local --strip-components=1; }'

# ─────────────────────────────────────────────────────────────────────────────
# 2. Install Starship prompt
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Installing Starship..."
ssh "$HOST" 'command -v starship >/dev/null 2>&1 || curl -sS https://starship.rs/install.sh | sh -s -- -y'

# ─────────────────────────────────────────────────────────────────────────────
# 3. Install rustup + cargo tools (bat, eza)
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Installing rustup..."
ssh "$HOST" 'command -v cargo >/dev/null 2>&1 || curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable'
echo "--- Installing bat and eza via cargo..."
ssh "$HOST" 'source ~/.cargo/env 2>/dev/null && { command -v bat >/dev/null 2>&1 || cargo install bat --locked; } && { command -v eza >/dev/null 2>&1 || cargo install eza --locked; }'

# ─────────────────────────────────────────────────────────────────────────────
# 4. Install zoxide
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Installing zoxide..."
ssh "$HOST" 'command -v zoxide >/dev/null 2>&1 || { [[ -f ~/.local/bin/zoxide ]] || curl -sSfL https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | sh; }'

# ─────────────────────────────────────────────────────────────────────────────
# 5. Clone Prezto + contrib
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Setting up Prezto..."
ssh "$HOST" '[[ -d ~/.zprezto ]] || git clone --recursive https://github.com/sorin-ionescu/prezto.git ~/.zprezto'
ssh "$HOST" '[[ -d ~/.zprezto/contrib ]] || (cd ~/.zprezto && git clone --recurse-submodules https://github.com/belak/prezto-contrib contrib)'

# ─────────────────────────────────────────────────────────────────────────────
# 6. Clone dotfiles on the remote, then sync dotfiles_env and wire up every
#    managed config/credential symlink via remote/links.tsv (see
#    remote/sync-env.sh — also the command to re-run later to refresh a host).
#    This covers the Linux-adapted shell/git/codex configs (from remote/),
#    portable public dotfiles (tmux, starship, .zprofile, ...), private
#    warehouse/dbt credentials (from dotfiles_env), and portable Claude/Codex
#    agent config (hooks, RTK.md, settings) — anything macOS-only (editor
#    app configs, karabiner, launchagents, gh auth token, .claude.json's
#    local MCP/session state) is deliberately left out of that manifest.
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Cloning dotfiles..."
ssh "$HOST" '[[ -d ~/Developer/dotfiles/.git ]] || git clone git@github.com:dataders/dotfiles.git ~/Developer/dotfiles'
"${REMOTE_DIR}/sync-env.sh" "$HOST"

# ─────────────────────────────────────────────────────────────────────────────
# 7. Install Claude Code CLI (native installer, no npm required)
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Installing Claude Code CLI..."
ssh "$HOST" 'command -v claude >/dev/null 2>&1 || curl -fsSL https://claude.ai/install.sh | bash'

# ─────────────────────────────────────────────────────────────────────────────
# 8. Set up npm for user-local global installs (no sudo needed)
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Configuring npm prefix..."
ssh "$HOST" 'bash -lc "npm config get prefix | grep -q npm-global || npm config set prefix ~/.npm-global"'

# ─────────────────────────────────────────────────────────────────────────────
# 9. Install Codex CLI (needs the npm prefix set above)
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Installing Codex CLI..."
ssh "$HOST" 'bash -lc "command -v codex >/dev/null 2>&1 || npm install -g @openai/codex"'

# ─────────────────────────────────────────────────────────────────────────────
# 10. Register portable MCP servers with Claude Code (github, lucid)
# ─────────────────────────────────────────────────────────────────────────────
# ~/.claude.json isn't linked/copied — it mixes secrets/session state with
# config. serena and parallel-search are skipped: they're stdio servers backed
# by local scripts/tools this host doesn't have.
echo "--- Registering Claude Code MCP servers..."
ssh "$HOST" 'bash -lc "source ~/Developer/dotfiles_env/secrets.zsh 2>/dev/null; claude mcp add --scope user --transport http github https://api.githubcopilot.com/mcp --header \"Authorization: Bearer \$GITHUB_PAT_MCP\""' || echo "Skipping github MCP registration (claude CLI or secrets.zsh not ready)"
ssh "$HOST" 'bash -lc "claude mcp add --scope user --transport http lucid https://dbt.runlayer.com/api/v1/proxy/5bcab31b-de80-4be2-a8ea-553d8c365fea/mcp"' || echo "Skipping lucid MCP registration"

# ─────────────────────────────────────────────────────────────────────────────
# 11. Install Ghostty terminfo (so TERM=xterm-ghostty works over SSH)
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Installing Ghostty terminfo..."
infocmp -x xterm-ghostty 2>/dev/null | ssh "$HOST" 'tic -x - 2>/dev/null' || echo "Skipping (xterm-ghostty terminfo not found locally)"

# ─────────────────────────────────────────────────────────────────────────────
# 12. Set default shell to zsh
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Setting default shell to zsh..."
ssh "$HOST" 'if [[ "$(getent passwd $(whoami) | cut -d: -f7)" != *zsh ]]; then sudo chsh -s $(which zsh) $(whoami); fi'

echo ""
echo "==> Done! SSH into ${HOST} to verify:"
echo "    ssh ${HOST}"
echo ""
echo "    Expected: Starship prompt with ❯"
echo "    Try: ls, cat somefile, tmux, claude --version, codex --version"
echo ""
echo "    lucid needs a one-time Runlayer login: run 'claude' and follow the"
echo "    MCP auth prompt, or use Runlayer via Okta to authorize the connector."

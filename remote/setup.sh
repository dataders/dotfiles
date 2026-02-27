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
DOTFILES_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE_DIR="$(dirname "$0")"

echo "==> Setting up shell environment on ${HOST}"

# ─────────────────────────────────────────────────────────────────────────────
# 1. Install system packages (zsh, tmux, fzf)
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Installing system packages..."
ssh "$HOST" 'sudo apt-get install -y -qq zsh tmux fzf 2>/dev/null || echo "apt install failed — some packages may already be present"'

# ─────────────────────────────────────────────────────────────────────────────
# 2. Install Starship prompt
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Installing Starship..."
ssh "$HOST" 'command -v starship >/dev/null 2>&1 || curl -sS https://starship.rs/install.sh | sh -s -- -y'

# ─────────────────────────────────────────────────────────────────────────────
# 3. Install cargo tools (bat, eza)
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Installing bat and eza via cargo..."
ssh "$HOST" 'source ~/.cargo/env 2>/dev/null && { command -v bat >/dev/null 2>&1 || cargo install bat; } && { command -v eza >/dev/null 2>&1 || cargo install eza; }'

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
# 6. Copy portable configs (directly from dotfiles)
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Copying portable config files..."
ssh "$HOST" 'mkdir -p ~/.config'
scp "${DOTFILES_DIR}/.config/starship.toml" "${HOST}:~/.config/starship.toml"
scp "${DOTFILES_DIR}/.tmux.conf" "${HOST}:~/.tmux.conf"
scp "${DOTFILES_DIR}/.zprofile" "${HOST}:~/.zprofile"
scp "${DOTFILES_DIR}/.zlogin" "${HOST}:~/.zlogin"
scp "${DOTFILES_DIR}/.zlogout" "${HOST}:~/.zlogout"

# ─────────────────────────────────────────────────────────────────────────────
# 7. Copy adapted configs (from remote/ directory)
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Copying adapted config files..."
scp "${REMOTE_DIR}/.zshrc" "${HOST}:~/.zshrc"
scp "${REMOTE_DIR}/.zpreztorc" "${HOST}:~/.zpreztorc"
scp "${REMOTE_DIR}/.zshenv" "${HOST}:~/.zshenv"
scp "${REMOTE_DIR}/.gitconfig" "${HOST}:~/.gitconfig"

# ─────────────────────────────────────────────────────────────────────────────
# 8. Copy secrets (from dotfiles_env — not committed to git)
# ─────────────────────────────────────────────────────────────────────────────
SECRETS_FILE="${HOME}/Developer/dotfiles_env/secrets.zsh"
if [[ -f "$SECRETS_FILE" ]]; then
    echo "--- Copying secrets..."
    scp "$SECRETS_FILE" "${HOST}:~/secrets.zsh"
    ssh "$HOST" 'chmod 600 ~/secrets.zsh'
else
    echo "--- Skipping secrets (${SECRETS_FILE} not found)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 9. Install Ghostty terminfo (so TERM=xterm-ghostty works over SSH)
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Installing Ghostty terminfo..."
infocmp -x xterm-ghostty 2>/dev/null | ssh "$HOST" 'tic -x - 2>/dev/null' || echo "Skipping (xterm-ghostty terminfo not found locally)"

# ─────────────────────────────────────────────────────────────────────────────
# 10. Set default shell to zsh
# ─────────────────────────────────────────────────────────────────────────────
echo "--- Setting default shell to zsh..."
ssh "$HOST" 'if [[ "$(getent passwd $(whoami) | cut -d: -f7)" != *zsh ]]; then sudo chsh -s $(which zsh) $(whoami); fi'

echo ""
echo "==> Done! SSH into ${HOST} to verify:"
echo "    ssh ${HOST}"
echo ""
echo "    Expected: Starship prompt with ❯"
echo "    Try: ls, cat somefile, tmux"

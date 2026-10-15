# Managed by dotfiles (remote/.bashrc).
#
# Some headless remote boxes have a directory-sync/compliance agent that
# rewrites /etc/passwd's shell field back to /bin/bash on every login
# (observed on peach01: /etc/passwd's mtime matches the login timestamp),
# so `chsh -s $(which zsh)` never sticks. Rather than fight that, hand off
# to zsh immediately so remote/.zshrc still runs for interactive sessions.
case $- in
  *i*) ;;
  *) return ;;
esac

# Preserve commands passed through `bash -c` (including Codex's SSH websocket
# bootstrap). Replacing that shell with zsh would discard the command and make
# zsh consume the websocket handshake from stdin.
if [[ -n "${BASH_EXECUTION_STRING:-}" ]]; then
  return
fi

if [[ -z "$ZSH_VERSION" ]] && command -v zsh >/dev/null 2>&1; then
  exec zsh -l
fi

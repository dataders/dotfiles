#
# Executes commands at the start of an interactive session.
#

# Source Prezto
if [[ -s "${ZDOTDIR:-$HOME}/.zprezto/init.zsh" ]]; then
  source "${ZDOTDIR:-$HOME}/.zprezto/init.zsh"
fi

# PATH
[[ -d "$HOME/.local/bin" ]] && export PATH="$HOME/.local/bin:$PATH"
[[ -d "$HOME/.cargo/bin" ]] && export PATH="$HOME/.cargo/bin:$PATH"
[[ -d "$HOME/.npm-global/bin" ]] && export PATH="$HOME/.npm-global/bin:$PATH"

# Completions
autoload -U +X bashcompinit && bashcompinit

# Aliases
alias gh='nocorrect gh'

# Modern CLI tools
alias cat='bat --paging=never'
alias ls='eza --icons --group-directories-first'
alias ll='eza -la --icons --group-directories-first --git'
alias tree='eza --tree --icons'

# Private/local overlays from dotfiles_env (not committed to public dotfiles repo)
for f in \
  "$HOME/Developer/dotfiles_env/secrets.zsh" \
  "$HOME/Developer/dotfiles_env/local.zsh"; do
  [[ -f "$f" ]] && source "$f"
done

# Starship prompt
eval "$(starship init zsh)"

# Zoxide (smarter cd)
eval "$(zoxide init zsh)"

# fzf (--zsh requires 0.48+; fall back to key-bindings/completion scripts)
if fzf --zsh &>/dev/null; then
  source <(fzf --zsh)
elif [[ -f /usr/share/doc/fzf/examples/key-bindings.zsh ]]; then
  source /usr/share/doc/fzf/examples/key-bindings.zsh
  [[ -f /usr/share/doc/fzf/examples/completion.zsh ]] && source /usr/share/doc/fzf/examples/completion.zsh
fi

# forgit (fzf-powered git commands) — git-cloned here since there's no writable
# Homebrew Cellar on this box (see remote/setup.sh)
[[ -f "$HOME/.local/share/zsh-plugins/forgit/forgit.plugin.zsh" ]] && \
  source "$HOME/.local/share/zsh-plugins/forgit/forgit.plugin.zsh"

# fzf-tab (same git-clone reasoning as forgit above)
[[ -f "$HOME/.local/share/zsh-plugins/fzf-tab/fzf-tab.plugin.zsh" ]] && \
  source "$HOME/.local/share/zsh-plugins/fzf-tab/fzf-tab.plugin.zsh"
# fzf-tab zstyle config — shared with .zshrc via .config/zsh/fzf-tab.zsh
# (edit that file, not here, so both stay in sync)
[[ -f "$HOME/Developer/dotfiles/.config/zsh/fzf-tab.zsh" ]] && \
  source "$HOME/Developer/dotfiles/.config/zsh/fzf-tab.zsh"

# fast-syntax-highlighting — must be sourced last so it can wrap all ZLE widgets
# (same git-clone reasoning as forgit above)
[[ -f "$HOME/.local/share/zsh-plugins/fast-syntax-highlighting/F-Sy-H.plugin.zsh" ]] && \
  source "$HOME/.local/share/zsh-plugins/fast-syntax-highlighting/F-Sy-H.plugin.zsh"
alias source='noglob source'

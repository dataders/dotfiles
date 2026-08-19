# fzf-tab zstyle config, shared by .zshrc (macOS) and remote/.zshrc (Linux).
# Edit only here — both files source this so the two stay in sync.

# use bracket format so group headers render without raw escape codes
zstyle ':completion:*:descriptions' format '[%d]'
# hide group headers (zsh color codes don't render in fzf)
zstyle ':fzf-tab:*' show-group none
# show directory contents when completing cd; auto-select single matches; float in a popup
zstyle ':fzf-tab:complete:cd:*' fzf-preview 'eza -A --icons --group-directories-first $realpath'
if [[ -n "$TMUX" || -n "$ZELLIJ" ]]; then
  zstyle ':fzf-tab:*' fzf-flags '--select-1' '--no-sort' '--tmux center,60%'
else
  zstyle ':fzf-tab:*' fzf-flags '--select-1' '--no-sort' '--height=~40%'
fi

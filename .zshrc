#
# Executes commands at the start of an interactive session.
#
# Authors:
#   Sorin Ionescu <sorin.ionescu@gmail.com>
#

# Source Prezto.
if [[ -s "${ZDOTDIR:-$HOME}/.zprezto/init.zsh" ]]; then
  source "${ZDOTDIR:-$HOME}/.zprezto/init.zsh"
fi

# Customize to your needs...

# ─────────────────────────────────────────────────────────────────────────────
# PATH Configuration (order matters: first entry = highest priority)
# ─────────────────────────────────────────────────────────────────────────────
path_additions=(
    "/opt/homebrew/bin"                          # Homebrew
    "/opt/homebrew/opt/openjdk@17/bin"           # OpenJDK 17
    "$HOME/.wasmtime/bin"                        # Wasmtime
    "$HOME/.codeium/windsurf/bin"                # Windsurf
    "$HOME/.local/bin"                           # dbt Cloud CLI, local scripts
)

# Prepend each path if it exists and isn't already in PATH
for p in "${path_additions[@]}"; do
    [[ -d "$p" && ":$PATH:" != *":$p:"* ]] && PATH="$p:$PATH"
done
export PATH

# Related exports
export WASMTIME_HOME="$HOME/.wasmtime"
export CPPFLAGS="-I/opt/homebrew/opt/openjdk@17/include"

# # use HTTPS for codespaces
# if [ -z "$CODESPACES" ]; then
#   git config --global url."git@github.com".insteadOf "https://github.com"
# fi


# Prompt handled by Starship (initialized at end of file)

# autoload -U +X compinit && compinit
autoload -U +X bashcompinit && bashcompinit
source ~/Developer/dbt-completion.bash/dbt-completion.bash


# zsh autocorrect disable specific commands
alias gh='nocorrect gh'
alias pip='noglob pip' # no searching w/ pip install
alias source='noglob source'

alias fsd=/Users/dataders/Developer/fs/target/debug/fs

eval "$(direnv hook zsh)"

# Private/local overlays from dotfiles_env (not committed to public dotfiles repo)
for _dotfiles_overlay in \
    "$HOME/Developer/dotfiles_env/secrets.zsh" \
    "$HOME/Developer/dotfiles_env/local.zsh"; do
    [[ -f "$_dotfiles_overlay" ]] && source "$_dotfiles_overlay"
done
unset _dotfiles_overlay

# dbt aliases
alias dbtf=/Users/dataders/.local/bin/dbt
alias dbt-core=/Users/dataders/Developer/jaffle-sandbox/.venv/bin/dbt
alias dbtd=/Users/dataders/Developer/fs/target/debug/dbt
alias dbtr=/Users/dataders/Developer/fs/target/release/dbt
alias dbtc=compute-dbt

# ─────────────────────────────────────────────────────────────────────────────
# Modern CLI Tools
# ─────────────────────────────────────────────────────────────────────────────

# Starship prompt
eval "$(starship init zsh)"

# Zoxide (smarter cd - use 'z' to jump to directories)
eval "$(zoxide init zsh)"

# fzf (fuzzy finder: Ctrl+R for history, Ctrl+T for files)
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# forgit (fzf-powered git commands - see docs/forgit.md)
source /opt/homebrew/opt/forgit/share/forgit/forgit.plugin.zsh

# Modern tool aliases
alias cat='bat --paging=never'
alias ls='eza --icons --group-directories-first'
alias ll='eza -la --icons --group-directories-first --git'
alias tree='eza --tree --icons'

# Pipe --help through bat with syntax highlighting
alias -g -- '--help=--help | bat -plhelp'

# Colored manpages via bat
export MANPAGER="sh -c 'sed -u -e \"s/\\x1B\[[0-9;]*m//g; s/.\\x08//g\" | bat -plman -ppager'"

# Auto-snapshot Brewfile after mutating brew operations
brew() {
    command brew "$@"
    local ret=$?
    case "$1" in
        install|uninstall|remove|rm|upgrade|tap|untap)
            command brew bundle dump --file=~/Developer/dotfiles/Brewfile --force
            ;;
    esac
    return $ret
}
# Added by dbt installer
export PATH="$PATH:/Users/dataders/.local/bin"

# Cortex CLI completion (disable via /settings in cortex)
[[ -s ~/.zsh/completions/cortex.zsh ]] && source ~/.zsh/completions/cortex.zsh

if command -v wt >/dev/null 2>&1; then eval "$(command wt config shell init zsh)"; fi

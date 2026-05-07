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

# dbt native zsh completion loaded via fpath (_dbt in ~/Developer/dbt-completion.bash)


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

# fzf-tab: use bracket format so group headers render without raw escape codes
zstyle ':completion:*:descriptions' format '[%d]'

# Modern tool aliases
alias cat='bat --paging=never'
alias ls='eza -A --icons --group-directories-first'
alias ll='eza -lA --icons --group-directories-first --git --no-permissions --no-user'
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

# Route claude through cmux claude-teams when inside cmux.
# cmux claude-teams creates a tmux server socket at /tmp/cmux-claude-teams/UUID and sets $TMUX
# to point to it — Claude Code needs $TMUX to spawn background agents as new panes
# (teammateMode: "tmux" in settings.json). Without this, agent teams silently run as
# local processes with no visible panes. The $TMUX guard prevents recursion: agent
# panes spawned by Claude Code inherit the cmux-claude-teams socket path, so they
# fall through to `command claude` directly.
claude() {
  if [[ -n "$CMUX_SURFACE_ID" && "$TMUX" != /tmp/cmux-claude-teams/* ]]; then
    cmux claude-teams "$@"
  else
    command claude "$@"
  fi
}

# Auto-name cmux tabs and color workspaces on directory change or branch switch.
# Tab name: "repo · branch". Workspace color: looked up from _CMUX_REPO_COLORS.
# Worktree suffix stripped for color lookup (e.g. fs.feat-foo → fs → Blue).
# Claude Code's session-start hook overrides the tab name with a task title.
if [[ -n "$CMUX_SURFACE_ID" ]]; then
  typeset -g _CMUX_TAB_LAST_PWD=""
  typeset -g _CMUX_TAB_GIT_CMD=0
  typeset -g _CMUX_WS_LAST_REPO=""

  typeset -gA _CMUX_REPO_COLORS=(
    dotfiles              Amber
    fs                    Blue
    fidget                Green
    dbt-clickhouse        Teal
    duckdb-iceberg        Aqua
    jaffle-sandbox        Olive
    fusion_issue_analysis Purple
    stocks                Rose
    sandbox-spark-iceberg Navy
    saas-metrics-demo     Indigo
    query-plan-diff       Crimson
  )

  # Light/dark theme pairs per repo. cmux themes set is app-wide but follows the
  # focused workspace — works well for the one-workspace-per-repo model.
  typeset -gA _CMUX_REPO_THEMES_LIGHT=(
    dotfiles              "Gruvbox Light"
    fs                    "Iceberg Light"
    fidget                "Everforest Light Med"
    dbt-clickhouse        "Flexoki Light"
    duckdb-iceberg        "Bluloco Light"
    jaffle-sandbox        "Zenbones Light"
    fusion_issue_analysis "Rose Pine Dawn"
    stocks                "Melange Light"
    sandbox-spark-iceberg "Dayfox"
    saas-metrics-demo     "Farmhouse Light"
    query-plan-diff       "Atom One Light"
  )

  typeset -gA _CMUX_REPO_THEMES_DARK=(
    dotfiles              "Gruvbox Dark"
    fs                    "Iceberg Dark"
    fidget                "Everforest Dark Hard"
    dbt-clickhouse        "Flexoki Dark"
    duckdb-iceberg        "Bluloco Dark"
    jaffle-sandbox        "Zenbones Dark"
    fusion_issue_analysis "Rose Pine"
    stocks                "Melange Dark"
    sandbox-spark-iceberg "Nightfox"
    saas-metrics-demo     "Farmhouse Dark"
    query-plan-diff       "Atom One Dark"
  )

  _cmux_tab_preexec() {
    case "${1## }" in
      git\ checkout*|git\ switch*|gh\ pr\ checkout*) _CMUX_TAB_GIT_CMD=1 ;;
    esac
  }

  _cmux_tab_precmd() {
    if [[ "$PWD" != "$_CMUX_TAB_LAST_PWD" ]] || (( _CMUX_TAB_GIT_CMD )); then
      _CMUX_TAB_LAST_PWD="$PWD"
      _CMUX_TAB_GIT_CMD=0
      local dir branch repo color
      dir=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null)
      dir=${dir:-$(basename "$PWD")}
      branch=$(git branch --show-current 2>/dev/null)
      if [[ -n "$branch" ]]; then
        cmux rename-tab "$dir · $branch" 2>/dev/null &!
      else
        cmux rename-tab "$dir" 2>/dev/null &!
      fi
      repo="${dir%%.*}"
      if [[ "$repo" != "$_CMUX_WS_LAST_REPO" ]]; then
        _CMUX_WS_LAST_REPO="$repo"
        color="${_CMUX_REPO_COLORS[$repo]}"
        [[ -n "$color" ]] && cmux workspace-action --action set-color --color "$color" 2>/dev/null &!
        local light dark
        light="${_CMUX_REPO_THEMES_LIGHT[$repo]}"
        dark="${_CMUX_REPO_THEMES_DARK[$repo]}"
        [[ -n "$light" && -n "$dark" ]] && cmux themes set --light "$light" --dark "$dark" 2>/dev/null &!
      fi
    fi
  }

  add-zsh-hook preexec _cmux_tab_preexec
  add-zsh-hook precmd _cmux_tab_precmd
fi

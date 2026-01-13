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


# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/Users/dataders/miniforge3/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/Users/dataders/miniforge3/etc/profile.d/conda.sh" ]; then
        . "/Users/dataders/miniforge3/etc/profile.d/conda.sh"
    else
        export PATH="/Users/dataders/miniforge3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

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


# needed for spaceship theme
PYENV_VIRTUALENV_DISABLE_PROMPT=1
SPACESHIP_PROMPT_ADD_NEWLINE="false"
SPACESHIP_TIME_SHOW="true"
SPACESHIP_PROMPT_PREFIXES_SHOW="false"

# autoload -U +X compinit && compinit
autoload -U +X bashcompinit && bashcompinit
source ~/Developer/dbt-completion.bash/dbt-completion.bash


# zsh autocorrect disable specific commands
alias gh='nocorrect gh'
alias pip='noglob pip' # no searching w/ pip install
alias source='noglob source'

alias fsd=/Users/dataders/Developer/fs/target/debug/fs

set AWS_PROFILE=SandboxPower
set AWS_DEFAULT_PROFILE=SandboxPower

eval "$(direnv hook zsh)"

# Source secrets from dotfiles_env (not committed to public dotfiles repo)
[[ -f ~/Developer/dotfiles_env/secrets.zsh ]] && source ~/Developer/dotfiles_env/secrets.zsh

# dbt aliases
alias dbtf=/Users/dataders/.local/bin/dbt
alias dbt-core=/Users/dataders/Developer/jaffle-sandbox/.venv/bin/dbt
alias dbtd=/Users/dataders/Developer/fs/target/debug/dbt
alias dbtr=/Users/dataders/Developer/fs/target/release/dbt

set AWS_PROFILE=SandboxPower
set AWS_DEFAULT_PROFILE=SandboxPower
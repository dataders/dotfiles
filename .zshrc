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

# add homebrew and miniforge to path
export PATH="/opt/homebrew/bin:/Users/dataders/miniforge3/bin:$PATH" 

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

# dbt Cloud CLI
export DBT_CLOUD_API_KEY="325ae470b24598d5329106b4ae3a9fbc1799ef5c"

eval "$(direnv hook zsh)"
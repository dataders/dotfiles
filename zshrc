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

export PATH="/Users/dataders/opt/anaconda3/bin:$PATH"  # commented out by conda initialize

# Customize to your needs...

# # >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/Users/dataders/opt/anaconda3/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/Users/dataders/opt/anaconda3/etc/profile.d/conda.sh" ]; then
        . "/Users/dataders/opt/anaconda3/etc/profile.d/conda.sh"
    else
        export PATH="/Users/dataders/opt/anaconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# # <<< conda initialize <<<


# needed for spaceship theme
export PYENV_VIRTUALENV_DISABLE_PROMPT=1
SPACESHIP_PROMPT_ADD_NEWLINE="false"
SPACESHIP_TIME_SHOW="true"
SPACESHIP_PROMPT_PREFIXES_SHOW="false"

# autoload -U +X compinit && compinit
autoload -U +X bashcompinit && bashcompinit
source ~/.dbt-completion.bash

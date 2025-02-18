# my dotfiles

here's where I store most of my config files, symlinked to their homes

reminder for myself how symlnk works to save me a google

```zsh
ln -s /Users/dataders/Developer/dotfiles/{FILE} /Users/dataders/{FILE}
```

for symlinking from private repo to public dotfiles if info is sensitive
```zsh
ln -s /Users/dataders/Developer/dotfiles_env/{FILE} /Users/dataders/Developer/dotfiles/{FILE}
```

## Installation

### install [Prezto](https://github.com/sorin-ionescu/prezto)

```sh
git clone --recursive https://github.com/sorin-ionescu/prezto.git "${ZDOTDIR:-$HOME}/.zprezto"

# create config files (that will be copied over later)
setopt EXTENDED_GLOB
for rcfile in "${ZDOTDIR:-$HOME}"/.zprezto/runcoms/^README.md(.N); do
  ln -s "$rcfile" "${ZDOTDIR:-$HOME}/.${rcfile:t}"
done
```


#### get [contrib modules](https://github.com/belak/prezto-contrib)


```sh
cd $ZPREZTODIR
git clone --recurse-submodules https://github.com/belak/prezto-contrib contrib
```

#### [dbt-completion bash script](https://github.com/dbt-labs/dbt-completion.bash)

clone it and make sure  the zshrc references it right


### install [homebrew](https://brew.sh/)

```sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```


## Configurations

run [`symmer.sh`](./symmer.sh) to symlink to their homes

### Prezto

symlinked to home directory

- `.zpreztorc` -> `~/.zpreztorc`
- `.zlogin` -> `~/.zlogin`
- `.zlogout` -> `~/.zlogout`
- `.zprofile` -> `~/.zprofile`
- `.zshenv` -> `~/.zshenv`
- `.zshrc` -> `~/.zshrc`

### Database drivers

symlinked to `/opt/homebrew/etc/`

- `odbcinst.ini` -> `/opt/homebrew/etc/odbcinst.ini`
- `odbc.ini` -> `/opt/homebrew/etc/odbc.ini`
- `freetds.conf` -> `/opt/homebrew/etc/freetds.conf`

## VSCode workspaces

I use these to organize my repos into workspaces based on task
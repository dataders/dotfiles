# my dotfiles

here's where I store most of my config files, symlinked to their homes

reminder for myself how symlnk works to save me a google

```zsh
ln -s /Users/dataders/repos/dotfiles/{FILE} /Users/dataders/{FILE}
```

## Configurations

### Prezto

symlinked to home directory

- `zpreztorc` -> `~/.zpreztorc`
- `zlogin` -> `~/.zlogin`
- `zlogout` -> `~/.zlogout`
- `zprofile` -> `~/.zprofile`
- `zshenv` -> `~/.zshenv`
- `zshrc` -> `~/.zshrc`

### Database drivers

symlinked to `/opt/homebrew/etc/`

- `odbcinst.ini` -> `/opt/homebrew/etc/odbcinst.ini`
- `odbc.ini` -> `/opt/homebrew/etc/odbc.ini`
- `freetds.conf` -> `/opt/homebrew/etc/freetds.conf`

### VSCode workspaces

I use these to organize my repos into workspaces based on task
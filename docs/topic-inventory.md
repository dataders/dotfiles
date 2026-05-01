# Topic Inventory

This inventory maps owned config areas to their source, home target, privacy
boundary, and a quick validation command.

| Topic | Source | Target | Privacy | Validation |
| --- | --- | --- | --- | --- |
| Link manifest | `links.tsv` | consumed by `links.sh` | public | `./links.sh dry-run` |
| Link health | `links.sh` | managed symlinks under `~`, `~/.config`, app dirs, and workspaces | mixed | `./links.sh check` |
| Doctor checks | `links.sh doctor` | shell/tool/dbt/private overlay health | mixed | `./links.sh doctor` |
| zsh/Prezto | `.zshrc`, `.zprofile`, `.zshenv`, `.zpreztorc`, `.zlogin`, `.zlogout` | `~/.*` | public with private overlay hooks | `zsh -lc 'command -v uv && command -v direnv && command -v starship'` |
| zsh overlays | `~/Developer/dotfiles_env/secrets.zsh`, `~/Developer/dotfiles_env/local.zsh` | sourced by `.zshrc` when present | private | `./links.sh doctor` |
| Git | `.gitconfig`, `.gitignore_global`, `.config/git/ignore` | `~/.gitconfig`, `~/.gitignore_global`, `~/.config/git/ignore` | public with private include hook | `git config --global --get include.path` |
| Git overlay | `~/Developer/dotfiles_env/gitconfig.local` | included by `.gitconfig` when present | private | `./links.sh doctor` |
| Direnv | `.config/direnv/direnvrc` | `~/.config/direnv/direnvrc` | public helper, private project env files | `direnv status` |
| Direnv project overlays | `~/Developer/dotfiles_env/projects/<repo>.envrc` | sourced by `source_dotfiles_env` from repo `.envrc` files | private | `direnv reload` in project |
| Claude | `.claude/*` | `~/.claude/*`, `~/.claude.json` | mostly public, settings local tracked here | `./links.sh check` |
| Codex | `.codex/*` | `~/.codex/*` | public rules/config, no secrets | `./links.sh check` |
| Shared skills | `.ai/skills/*` | `~/.codex/skills/*`, `~/.claude/skills/*` | public | `./links.sh check` |
| dbt | `~/Developer/dotfiles_env/.dbt/*` | `~/.dbt/*` | private direct links | `readlink ~/.dbt/profiles.yml` |
| Warehouse config | `.aws/config`, `.snowflake/connections.toml`, `.databrickscfg` | `~/.aws/config`, `~/.snowflake/connections.toml`, `~/.databrickscfg` | private via `dotfiles_env` symlinks | `./links.sh check` |
| Editors | `.vscode/settings.json`, `.config/zed/settings.json` | Code, Insiders, Cursor, Zed user settings | public | `./links.sh check` |
| Workspaces | `workspaces/*/settings.json` | `~/Developer/<repo>/.vscode/settings.json` | public | `./links.sh check` |
| Terminal | `.config/cmux/settings.json`, `.config/ghostty/config`, `.tmux.conf` | `~/.config/cmux/settings.json`, `~/.config/ghostty/config`, `~/.tmux.conf` | public | `./links.sh check` |
| Homebrew | `Brewfile` | Homebrew bundle state | public | `brew bundle check --file=Brewfile` |
| Rust/Cargo | `.cargo/config.toml`, `.rustup/settings.toml` | `~/.cargo/config.toml`, `~/.rustup/settings.toml` | public | `rustup show active-toolchain` |
| Security hooks | `.githooks/pre-commit` | repo-local `core.hooksPath` | public | `git config core.hooksPath` |

## Overlay Hook Contract

Overlay hooks are explicit extension points from public config into
`~/Developer/dotfiles_env`. They are intentionally named, optional, and quiet
when missing.

- `.zshrc` sources `secrets.zsh` and `local.zsh` from `dotfiles_env` when those
  files exist.
- `.gitconfig` includes `~/Developer/dotfiles_env/gitconfig.local` when Git
  reads global config.
- `.config/direnv/direnvrc` defines `source_dotfiles_env`, which a project can
  call from `.envrc` to load `dotfiles_env/projects/<repo>.envrc`.

Do not add broad auto-discovery such as sourcing every `*.zsh` file. Keep hooks
explicit so shell startup and secret boundaries stay debuggable.

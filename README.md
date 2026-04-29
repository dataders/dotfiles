# my dotfiles

## TL;DR

macOS dotfiles for dbt/Fusion work, modern terminal UX, editor settings, agent
config, and warehouse tooling. Public config lives here; private config stays in
`~/Developer/dotfiles_env`; `links.sh` wires both back into home paths.

## Modern CLI UX

These are the muscle-memory upgrades from `.zshrc`:

| Old habit | Use now | Backing tool |
| --- | --- | --- |
| `cat file` | `cat file` with syntax highlighting | `alias cat='bat --paging=never'` |
| `ls` | `ls` with icons and grouped dirs | `eza` |
| `ls -la` | `ll` | `eza -la --icons --group-directories-first --git` |
| `tree` | `tree` with icons | `eza --tree --icons` |
| `man foo` | `man foo` with color | `MANPAGER` pipes through `bat` |
| `cmd --help` | `cmd --help` with color | global alias pipes help through `bat -plhelp` |
| `cd some/deep/path` | `z repo-or-dir` | `zoxide` |
| `git diff` | `git diff` with side-by-side color | `delta` via `.gitconfig` |
| `brew install ...` | same command | wrapper auto-runs `brew bundle dump` into `Brewfile` |
| noisy shell commands in Codex | `rtk <cmd>` | `rtk` proxy cuts command output tokens |

Other aliases:

```zsh
gh       # nocorrect gh
pip      # noglob pip
source   # noglob source
fsd      # /Users/dataders/Developer/fs/target/debug/fs
dbtf     # dbt Cloud CLI
dbt-core # dbt-core from jaffle-sandbox venv
dbtd     # debug Fusion dbt
dbtr     # release Fusion dbt
dbtc     # compute-dbt
```

## LLM Agent

Codex and Claude config are repo-backed, then symlinked into `~/.codex` and
`~/.claude` by `links.sh`. Codex uses `.codex/config.toml` for model, sandbox,
MCP servers, plugins, trusted projects, and Guardian review; command approvals
live separately in `.codex/rules/default.rules`.

Claude uses `.claude/settings.json`, `.claude/settings.local.json`,
`.claude/hooks/*.sh`, and `.claude/CLAUDE.md`. Keep parallel behavior in both
trees when it affects both agents: Python enforcement, RTK guidance, shared
instructions, and safety rules.

Shared custom skills live only in `.ai/skills`. `links.sh` removes old generated
skill dirs and symlinks each skill into both `~/.codex/skills` and
`~/.claude/skills`, so plugin caches stay derived state instead of source of
truth.

## Daily Cheatsheet

| Thing | Shortcut or command | Use |
| --- | --- | --- |
| Search shell history | `Ctrl-R` | fuzzy history picker from `fzf` |
| Pick files | `Ctrl-T` | insert fuzzy-selected file paths |
| Jump directories | `Alt-C` | fuzzy `cd` widget |
| Complete command args | `Tab` | zsh completion with `fzf-tab` UI |
| Jump by memory | `z <name>` | zoxide directory jump |
| Browse git log | `glo` | forgit log picker |
| Pick files to stage | `ga` | forgit add picker |
| Pick files to diff | `gd` | forgit diff picker |
| Switch branches | `gcb` | forgit branch checkout picker |
| Unstage files | `grh` | forgit reset-head picker |
| Browse stash | `gss` | forgit stash picker |
| Create fixup commit | `gfu` | forgit fixup picker |
| Restore file | `gcf` | forgit checkout-file picker |
| Interactive blame | `gbl` | forgit blame picker |
| Clean untracked files | `gclean` | forgit clean picker |
| Reload tmux config | `Ctrl-b r` | source `~/.tmux.conf` |
| Split tmux vertical | `Ctrl-b \|` | side-by-side split |
| Split tmux horizontal | `Ctrl-b -` | top/bottom split |
| Check direnv | `direnv status` | show loaded `.envrc` state |
| Trust project env | `direnv allow` | approve current `.envrc` |
| Re-run project env | `direnv reload` | reload current `.envrc` |
| Remove project trust | `direnv deny` | revoke current `.envrc` |

More forgit reminders live in [`docs/forgit.md`](docs/forgit.md).

## Completions

Completion stack:

1. Prezto loads the `completion` module from `.zpreztorc`.
2. `fzf-tab` changes normal `Tab` completion into an interactive picker.
3. `.zshrc` runs `bashcompinit` so bash completion scripts can work in zsh.
4. `~/Developer/dbt-completion.bash/dbt-completion.bash` adds dbt selector
   completion from `target/manifest.json`.
5. `~/.fzf.zsh` adds `Ctrl-R`, `Ctrl-T`, `Alt-C`, and fzf completion widgets.
6. `forgit.plugin.zsh` adds git picker aliases like `ga`, `gd`, and `glo`.
7. `wt config shell init zsh` adds Worktrunk shell integration and completions.
8. `~/.zsh/completions/cortex.zsh` is loaded when present.

dbt completion needs a compiled project manifest. If a selector does not show
up, run `dbt parse` or `dbt compile` in that project first.

Quick checks:

```zsh
zsh -ic 'print -r -- ${_comps[dbt]}'
zsh -ic 'bindkey | grep -F fzf'
zsh -ic 'whence -w ga gd glo gcb'
```

## Direnv

Direnv is set up globally:

- `direnv` is installed by `Brewfile`.
- `.zshrc` runs `eval "$(direnv hook zsh)"`.
- Project-specific env vars should live in each repo's `.envrc`.
- First time in a repo, run `direnv allow`.

Expected check:

```zsh
command -v direnv
direnv version
direnv status
```

In this repo, `direnv status` saying `No .envrc or .env loaded` is fine because
dotfiles itself does not need a project env.

## Workspaces

Workspace settings under `workspaces/` are VS Code workspace settings. They also
work for Cursor and Positron because both read repo-local `.vscode/settings.json`
files:

```zsh
workspaces/fs/settings.json                 -> ~/Developer/fs/.vscode/settings.json
workspaces/internal-analytics/settings.json -> ~/Developer/internal-analytics/.vscode/settings.json
workspaces/jaffle-sandbox/settings.json     -> ~/Developer/jaffle-sandbox/.vscode/settings.json
```

## Managed Tools

| Tool | Config source | Home target | How configured |
| --- | --- | --- | --- |
| zsh/Prezto | `.zshrc`, `.zprofile`, `.zpreztorc`, `.zlogin`, `.zlogout`, `.zshenv` | `~/.*` | Prezto modules in `.zpreztorc`; login shell PATH/env in `.zprofile`; interactive tools in `.zshrc` |
| Homebrew | `Brewfile` | Homebrew bundle state | `brew()` wrapper snapshots mutating operations back to `Brewfile` |
| GitHub dashboard | `.config/gh-dash/config.yml` | `~/.config/gh-dash/config.yml` | PR, review, issue, and notification sections for `gh dash` |
| Ghostty | `.config/ghostty/config` | `~/.config/ghostty/config` | JetBrains Mono Nerd Font, light/dark GitHub themes, zsh shell integration |
| Starship | `.config/starship.toml` | `~/.config/starship.toml` | Prompt format, git status, Python, AWS, command duration, time |
| Git | `.gitconfig`, `.gitignore_global`, `.config/git/ignore` | `~/.gitconfig`, `~/.gitignore_global`, `~/.config/git/ignore` | `delta` pager, SSH signing, `rerere`, histogram diff, GitHub credential helper |
| Git hooks | `.githooks/pre-commit` | repo-local `core.hooksPath` | Blocks likely-sensitive paths and TruffleHog findings in staged diff |
| GitHub CLI | `.config/gh/hosts.yml` | `~/.config/gh/hosts.yml` | Auth host config, symlinked through `links.sh` |
| Codex | `.codex/config.toml`, `.codex/AGENTS.md`, `.codex/RTK.md`, `.codex/rules/default.rules` | `~/.codex/...` | Model, sandbox, MCP servers, plugins, rules, trusted projects |
| Claude | `.claude/CLAUDE.md`, `.claude/settings*.json`, `.claude/hooks/*.sh`, `.claude/RTK.md` | `~/.claude/...` | Shared instructions, hooks, permissions, RTK guidance |
| Shared AI skills | `.ai/skills/*` | `~/.codex/skills/*`, `~/.claude/skills/*` | `links.sh` replaces old skill dirs and symlinks each skill into both agents |
| dbt | `~/Developer/dotfiles_env/.dbt/*` | `~/.dbt/*` | Private profiles, Cloud config, MCP config, keyfile, user state |
| dbt CLIs | `.zshrc` aliases | shell aliases | `dbtf`, `dbt-core`, `dbtd`, `dbtr`, `dbtc` route to Cloud/core/debug/release helpers |
| Database drivers | `odbcinst.ini`, `odbc.ini`, `freetds.conf` | `/opt/homebrew/etc/...` and `~/.odbc.ini` | ODBC, FreeTDS, and user DSN config |
| Snowflake/AWS/Databricks | symlinks into `dotfiles_env` or repo placeholders | `~/.snowflake`, `~/.aws`, `~/.databrickscfg` | Sensitive connection config stays private |
| VS Code/Cursor | `.vscode/settings.json`, `workspaces/*/settings.json` | Code, Insiders, Cursor user settings; repo `.vscode` dirs | Shared editor settings and per-repo themes |
| Zed | `.config/zed/settings.json` | `~/.config/zed/settings.json` | Zed user settings |
| Worktrunk | `.config/wt.toml` | `~/.config/wt.toml` | Copies ignored cache after new worktree start; shell init from `.zshrc` |
| Rust/Cargo | `.cargo/config.toml`, `.rustup/settings.toml` | `~/.cargo/config.toml`, `~/.rustup/settings.toml` | Cargo config and rustup toolchain settings |
| SSH signing | `.ssh/allowed_signers`, `.ssh/config` | `~/.ssh/...` | Git SSH signing verification uses allowed signers file |
| tmux | `.tmux.conf` | `~/.tmux.conf` | Mouse, easier splits, 1-based panes, reload binding |
| Karabiner | `karabiner/karabiner.json` | `~/.config/karabiner/karabiner.json` | Keyboard rules |
| Marimo | `.config/marimo/marimo.toml` | `~/.config/marimo/marimo.toml` | Marimo config |
| Raycast scripts | `.raycast_scripts/*` | repo-managed scripts | Small local automation scripts |

## Architecture

This repo has three layers:

1. `~/Developer/dotfiles` is public, git-tracked config.
2. `~/Developer/dotfiles_env` is private, local-only config.
3. Home paths under `~`, `~/.config`, app config dirs, and `/opt/homebrew/etc`
   point back to the right source with symlinks.

`links.sh` is the main explicit symlink script. It wires nested config dirs,
agent config, dbt private config, editor settings, workspaces, Rust, Worktrunk,
and AI skills.

`symmer.sh` is the older broad helper for top-level dotfiles and `.conf`/`.ini`
files. Prefer adding new links to `links.sh` when the target is important or
non-obvious.

Sensitive dbt config uses direct private links:

```zsh
~/.dbt/profiles.yml   -> ~/Developer/dotfiles_env/.dbt/profiles.yml
~/.dbt/dbt_cloud.yml  -> ~/Developer/dotfiles_env/.dbt/dbt_cloud.yml
~/.dbt/mcp.yml        -> ~/Developer/dotfiles_env/.dbt/mcp.yml
~/.dbt/keyfile.json   -> ~/Developer/dotfiles_env/.dbt/keyfile.json
~/.dbt/.user.yml      -> ~/Developer/dotfiles_env/.dbt/.user.yml
```

Do not delete those dbt symlinks. If one must be removed for testing, restore it
right away:

```zsh
ln -sf ~/Developer/dotfiles_env/.dbt/dbt_cloud.yml ~/.dbt/dbt_cloud.yml
```

### Useful Link Patterns

Public file to home:

```zsh
ln -sf /Users/dataders/Developer/dotfiles/{FILE} /Users/dataders/{FILE}
```

Private file through public repo:

```zsh
ln -sf /Users/dataders/Developer/dotfiles_env/{FILE} /Users/dataders/Developer/dotfiles/{FILE}
```

## Security

Secrets belong in `~/Developer/dotfiles_env`, not this repo. The sensitive dbt,
Snowflake, AWS, and Databricks files either point into that private tree or stay
out of git.

This repo has a pre-commit hook at `.githooks/pre-commit`. It blocks staged
paths that usually contain private config, then scans the staged diff with
TruffleHog. The TruffleHog scan does not call verification endpoints, so
detected credentials are not sent to provider APIs.

Enable it in this checkout:

```zsh
git config core.hooksPath .githooks
```

Manual check:

```zsh
git diff --cached --no-ext-diff --binary | trufflehog --log-level=-1 stdin --no-update --no-verification --fail --fail-on-scan-errors
```

Bypass only after review:

```zsh
SKIP_SECRET_SCAN=1 git commit ...
```

No license file yet. Public GitHub visibility does not grant reuse rights by
itself; add a license, probably MIT, if this repo should be reusable as a
template.

## Install

### Homebrew

```zsh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew bundle --file=~/Developer/dotfiles/Brewfile
gh extension install dlvhdr/gh-dash
```

### Prezto

```zsh
git clone --recursive https://github.com/sorin-ionescu/prezto.git "${ZDOTDIR:-$HOME}/.zprezto"

setopt EXTENDED_GLOB
for rcfile in "${ZDOTDIR:-$HOME}"/.zprezto/runcoms/^README.md(.N); do
  ln -s "$rcfile" "${ZDOTDIR:-$HOME}/.${rcfile:t}"
done
```

### Prezto contrib

```zsh
cd $ZPREZTODIR
git clone --recurse-submodules https://github.com/belak/prezto-contrib contrib
```

### dbt completion

Clone [`dbt-completion.bash`](https://github.com/dbt-labs/dbt-completion.bash)
to `~/Developer/dbt-completion.bash`. `.zshrc` loads it through
`bashcompinit`.

## Inspiration

- [@gwenwindflower](https://github.com/gwenwindflower) /
  [gwenwindflower/dotfiles](https://github.com/gwenwindflower/dotfiles)
- [@serramatutu](https://github.com/serramatutu) /
  [serramatutu/dotfiles](https://github.com/serramatutu/dotfiles)
- [@ryancharris](https://github.com/ryancharris) /
  [ryancharris/dotfiles](https://github.com/ryancharris/dotfiles)

# my dotfiles

## TL;DR

macOS dotfiles for dbt/Fusion work, modern terminal UX, editor settings, agent
config, and warehouse tooling. Public config lives here; private config stays in
`~/Developer/dotfiles_env`; `links.tsv` declares managed links and `links.sh`
applies, checks, unlinks, and diagnoses them.

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

`AGENTS.md` is the canonical shared rule file. Codex and Claude keep short
global files that point back here plus the few hard guardrails agents must see
immediately. This keeps global context clean instead of duplicating the same
wall of rules in every agent config.

Codex and Claude config are repo-backed, then symlinked into `~/.codex` and
`~/.claude` by `links.sh`. Codex uses `.codex/config.toml` for model, sandbox,
MCP servers, plugins, trusted projects, hooks, and Guardian review; command
approvals live separately in `.codex/rules/default.rules`.

Claude uses `.claude/settings.json`, `.claude/settings.local.json`,
`.claude/hooks/*.sh`, and `.claude/CLAUDE.md`. Keep shared behavior in the
canonical rule file unless a tool genuinely needs its own config syntax.

Shared custom skills live only in `.ai/skills`. `links.sh` removes old generated
skill dirs and symlinks each skill into both `~/.codex/skills` and
`~/.claude/skills`, so plugin caches stay derived state instead of source of
truth.

Agents should use a skill when the task name or shape matches one of these
repo-backed skills. Open the relevant `SKILL.md` first, follow its workflow, and
prefer skill scripts/templates over recreating the same logic. Current shared
skills: `business-value-case`, `bvc-benchmarks`, `content-intelligence`,
`fusion-diary`, `gh-fix-ci`, `mviz`, and `worktrunk`.

## cmux Agent Terminal

cmux is the default terminal app. Config is split in two files because cmux
reads Ghostty terminal settings from `.config/ghostty/config`, while cmux-owned
app settings live in `.config/cmux/settings.json`.

`.config/cmux/settings.json` is tuned for coding-agent multitasking:

| Setting | Why it is set |
| --- | --- |
| `app.preferredEditor = "code"` | Command used for Cmd-click file opens. Empty string uses macOS default. cmux appends the clicked path, so practical values include `code`, `cursor`, `zed`, `subl`, or a wrapper script. |
| `app.openMarkdownInCmuxViewer = true` | Cmd-click Markdown files into cmux viewer with live reload instead of leaving terminal flow. |
| `app.keepWorkspaceOpenWhenClosingLastSurface = true` | Keep workspace shell/history container even after last pane closes. Less accidental workspace loss. |
| `app.iMessageMode = true` | Agent prompt behavior: when a prompt is sent, move that workspace to top and show submitted prompt text in sidebar. Useful when many agents are running and you need to remember what each one is doing. |
| `app.commandPaletteSearchesAllSurfaces = true` | Command palette can find panes/tabs outside the active workspace. Better for many parallel agents. |
| `terminal.showScrollBar = false` | Less chrome; alternate-screen TUIs already hide scrollbars. |
| `notifications.unreadPaneRing = true` and `notifications.paneFlash = true` | Visual signal when an agent finishes or asks for attention. |
| `notifications.sound = "default"` | Audible agent notification. Change to `none` later if parallel agents get too noisy. |
| `sidebar.branchLayout = "vertical"` | Branch + directory stay readable in narrow sidebar. |
| `sidebar.showNotificationMessage = true` | Last agent message appears beside workspace. |
| `sidebar.showPullRequests`, `showPorts`, `showProgress` | Surface PRs, local dev servers, and agent progress without hunting through panes. |
| `automation.socketControlMode = "automation"` | Allow cmux CLI/API automation from trusted local tools, including agent hooks. |
| `automation.claudeCodeIntegration = true` | Enable cmux Claude Code integration hooks. |
| `automation.portBase = 9100`, `portRange = 10` | Reserve predictable local port ranges per workspace. |
| `browser.openTerminalLinksInCmuxBrowser = true` | Keep local preview links in cmux browser panes. |
| `browser.hostsToOpenInEmbeddedBrowser` | Keep localhost-style app previews inside cmux. |
| `browser.insecureHttpHostsAllowedInEmbeddedBrowser` | Allow local HTTP previews without repeated warnings. |

`.config/ghostty/config` handles terminal feel inside cmux:

| Setting | Why it is set |
| --- | --- |
| `font-family = JetBrainsMono Nerd Font`, `font-size = 14` | Readable code font with icons for shell prompt/tooling. |
| `window-show-tab-bar = never` | Hide Ghostty tabs because cmux owns workspaces/tabs. |
| `confirm-close-surface = false` | Let cmux workspace controls handle close confirmation instead of double prompts. |
| `split-inherit-working-directory`, `tab-inherit-working-directory`, `window-inherit-working-directory` | New panes/tabs/windows start in current repo. Essential for agent fanout. |
| `window-inherit-font-size = true` | Zoom once, keep size across new surfaces. |
| `unfocused-split-opacity = 0.70`, `split-divider-color = 45475a` | Make active agent pane obvious in dense split layouts. |
| `scrollback-limit = 50000` | Keep enough agent trace history without unbounded scrollback. |
| `clipboard-trim-trailing-spaces`, `clipboard-paste-protection`, `clipboard-paste-bracketed-safe` | Safer copy/paste for commands and generated snippets. |
| `macos-option-as-alt = true` plus `alt+left/right/backspace` | Normal shell word navigation and word delete. |
| `cmd+d`, `cmd+shift+d`, `cmd+alt+arrows`, `cmd+ctrl+arrows` | cmux/Ghostty split creation, focus, and resize keys. These match cmux defaults and do not steal normal browser/editor shortcuts like `Cmd-L`. |

`cmux omx` and `cmux omc` are not part of the baseline install. Use them only
when you deliberately want Oh My Codex or Oh My Claude Code team/HUD workflows;
normal daily work should use native cmux workspaces, Codex, Claude Code, and the
repo-backed skills above.

Clicked terminal URLs do not use `preferredEditor`. They use the browser
settings: localhost-style URLs open in a cmux browser pane, reusing an existing
browser pane when one is present and otherwise creating a new browser split. cmux
does not expose a setting to turn URL clicks into a new terminal split. For a
terminal split, use `Cmd-D`, `cmux new-pane --type terminal --direction right`,
or a small wrapper/custom command for a specific workflow.

cmux/Ghostty shortcuts and tmux shortcuts live at different layers. `Cmd-*` and
`Option-Cmd-*` are handled by cmux/Ghostty before shell input reaches tmux.
tmux shortcuts only matter inside a running `tmux` session after the tmux prefix
(`Ctrl-b` here). Prefer cmux splits for normal local multitasking; use tmux only
when a remote/session-persistence workflow needs it.

A `preferredEditor` wrapper script is optional. Use one when `code <path>` is
too blunt and file opens need routing logic. cmux appends one path argument to
the command, so a wrapper can choose an editor by file type, repo, or path:

```sh
#!/bin/sh
set -eu
path=${1:?}

case "$path" in
  *.csv|*.tsv) open -a "Numbers" "$path" ;;
  *) code -r "$path" ;;
esac
```

Then set `app.preferredEditor` to the wrapper path. Keep the wrapper in this repo
and symlink it through `links.tsv` if it becomes real config.

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
- `.config/direnv/direnvrc` defines `source_dotfiles_env` for private per-repo
  env overlays from `~/Developer/dotfiles_env/projects/<repo>.envrc`.
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

Project `.envrc` files can opt into private overlays without committing secrets:

```sh
source_dotfiles_env
```

That loads `~/Developer/dotfiles_env/projects/<current-repo>.envrc` if present.
Pass a name to load a different file: `source_dotfiles_env fs`.

## Workspaces

Workspace settings under `workspaces/` are VS Code workspace settings. They also
work for Cursor and Positron because both read repo-local `.vscode/settings.json`
files:

```zsh
workspaces/fs/settings.json                 -> ~/Developer/fs/.vscode/settings.json
workspaces/internal-analytics/settings.json -> ~/Developer/internal-analytics/.vscode/settings.json
workspaces/jaffle-sandbox/settings.json     -> ~/Developer/jaffle-sandbox/.vscode/settings.json
```

## Topic Inventory

[`docs/topic-inventory.md`](docs/topic-inventory.md) maps each managed topic to
its source path, target path, privacy boundary, and validation command. Use it
when deciding whether a config belongs in this public repo or in
`~/Developer/dotfiles_env`.

## Managed Tools

| Tool | Config source | Home target | How configured |
| --- | --- | --- | --- |
| zsh/Prezto | `.zshrc`, `.zprofile`, `.zpreztorc`, `.zlogin`, `.zlogout`, `.zshenv` | `~/.*` | Prezto modules in `.zpreztorc`; login shell PATH/env in `.zprofile`; interactive tools in `.zshrc` |
| zsh overlays | `~/Developer/dotfiles_env/secrets.zsh`, `~/Developer/dotfiles_env/local.zsh` | sourced by `.zshrc` when present | Private shell tokens, aliases, and one-off local tweaks |
| Homebrew | `Brewfile` | Homebrew bundle state | `brew()` wrapper snapshots mutating operations back to `Brewfile` |
| GitHub dashboard | `.config/gh-dash/config.yml` | `~/.config/gh-dash/config.yml` | PR, review, issue, and notification sections for `gh dash` |
| cmux | `.config/cmux/settings.json`, `.config/ghostty/config` | `~/.config/cmux/settings.json`, `~/.config/ghostty/config` | Default terminal app; cmux app settings plus Ghostty terminal rendering config |
| Starship | `.config/starship.toml` | `~/.config/starship.toml` | Prompt format, git status, Python, AWS, command duration, time |
| Git | `.gitconfig`, `.gitignore_global`, `.config/git/ignore` | `~/.gitconfig`, `~/.gitignore_global`, `~/.config/git/ignore` | `delta` pager, SSH signing, `rerere`, histogram diff, GitHub credential helper, private `gitconfig.local` include |
| Git hooks | `.githooks/pre-commit` | repo-local `core.hooksPath` | Blocks likely-sensitive paths and TruffleHog findings in staged diff |
| Direnv | `.config/direnv/direnvrc` | `~/.config/direnv/direnvrc` | Defines `source_dotfiles_env` for private per-project env overlays |
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

`links.tsv` is the declarative manifest for managed symlinks. Each row records
source, target, topic group, privacy classification, and a note.

`links.sh` consumes that manifest and supports:

```zsh
./links.sh apply    # create/update managed symlinks; default
./links.sh dry-run  # print planned actions
./links.sh check    # verify managed symlinks
./links.sh unlink   # remove only managed symlinks pointing to expected sources
./links.sh doctor   # run link, shell, tool, dbt, and overlay health checks
```

It wires nested config dirs, agent config, dbt private config, editor settings,
workspaces, Rust, Worktrunk, and AI skills.

`symmer.sh` is the older broad helper for top-level dotfiles and `.conf`/`.ini`
files. Prefer adding new links to `links.tsv` so `links.sh check` and
`links.sh doctor` can validate them.

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

### Overlay Hooks

Overlay hooks are explicit, optional extension points from public config into
`~/Developer/dotfiles_env`:

- `.zshrc` sources `~/Developer/dotfiles_env/secrets.zsh` and
  `~/Developer/dotfiles_env/local.zsh` when present.
- `.gitconfig` includes `~/Developer/dotfiles_env/gitconfig.local`.
- `.config/direnv/direnvrc` provides `source_dotfiles_env` for project `.envrc`
  files.

Use hooks for secrets, work-only local settings, and machine-specific tweaks.
Do not use broad auto-discovery or profile flags; hooks should stay named and
debuggable.

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

### Links And Doctor

```zsh
cd ~/Developer/dotfiles
./links.sh dry-run
./links.sh apply
./links.sh doctor
```

Run `./links.sh check` after changing `links.tsv`, shell config, agent config,
or private symlink wiring.

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

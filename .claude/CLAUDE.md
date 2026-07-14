# Agent Rules

Canonical shared rules live in `/Users/dataders/Developer/dotfiles/AGENTS.md`.
Use that file as source of truth. Keep this file short so Claude global context
does not become noisy.

Hard rules:

- Use `uv`, never bare `pip`, `pip3`, or `python3`.
- Public config lives in `~/Developer/dotfiles`; private config lives in
  `~/Developer/dotfiles_env`.
- Use `links.tsv` plus `./links.sh dry-run`, `./links.sh check`, and
  `./links.sh doctor` for symlink work.
- Never run `./links.sh apply` from a worktree / Conductor workspace — it
  repoints `~` symlinks into the throwaway checkout and breaks them on archive.
  Apply only from the primary checkout `~/Developer/dotfiles`.
- Do not delete critical `~/.dbt/*` symlinks.
- Use explicit overlay hooks only: `secrets.zsh`, `local.zsh`,
  `gitconfig.local`, and `source_dotfiles_env`.
- Use matching repo-backed skills from `.ai/skills`.
- Use `worktrunk` / `wt` for worktrees, never `superpowers:using-git-worktrees`.
- Spawn agent teams via the session's implicit team: `TaskCreate → Agent(name=…)`, coordinate with `SendMessage`; never `cmux claude-teams`, never inline execution, never bare `Agent(run_in_background=true)`. (`TeamCreate`/`team_name` removed in CLI 2.1.179.)
- changie changelog entries: `author` must be `"dataders claude"` (pass `--custom 'author=dataders claude'`), never `aswanson`.
- In a background session (`CLAUDE_JOB_DIR` set) never run `open` — it can't reach the display and silently no-ops. Print the URL/path as a clickable link instead; suggest `! open <url>`. Enforced by the `block-open-in-bg.sh` PreToolUse hook.

MCP config layout (all tracked in dotfiles via links.tsv):

- Claude Code reads MCP servers from `~/.claude.json` (→ `dotfiles/.claude.json`); top-level `mcpServers` = user scope. Add via `claude mcp add <name> --scope user …`. Currently: github, lucid, serena, parallel-search. (`~/.claude/mcp.json` is NOT read by Claude Code — kept empty.)
- `~/.codex/config.toml` → `dotfiles/.codex/config.toml` — Codex MCP servers (local MCPs + Runlayer remotes, incl. lucid).
- `~/.claude/settings.json` and `~/.claude.json` are symlinked too; `mcpServers` is NOT valid in settings files — it belongs in `~/.claude.json` top-level, not `settings.json`.

@RTK.md

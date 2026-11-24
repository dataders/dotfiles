# Agent Rules

Canonical shared rules live in `~/Developer/dotfiles/AGENTS.md`.
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
- Use matching repo-backed skills from `.ai/skills` or `.agents/skills` in the current repo.
- Use `worktrunk` / `wt` for worktrees, never `superpowers:using-git-worktrees`.
- Spawn teammates only when independent work benefits from parallel execution. Use the session's native agent tools and assign each writer an exclusive checkout when needed.
- changie changelog entries: `author` must be `"dataders claude"` (pass `--custom 'author=dataders claude'`), never `aswanson`.
- In a background session (`CLAUDE_JOB_DIR` set) never run `open` — it can't reach the display and silently no-ops. Print the URL/path as a clickable link instead; suggest `! open <url>`. Enforced by the `block-open-in-bg.sh` PreToolUse hook.
  On the Linux remote boxes, `xdg-open <url>` works even in background sessions
  (SSH URL relay to the Mac, OAuth callbacks included); `browser-relay-env.sh`
  resets Claude's `BROWSER=true` to it so browser-SSO CLIs work.

- Register Claude MCP servers with `claude mcp add <name> --scope user …`.
  User-scope MCP definitions and app state live in the local `~/.claude.json`.
- Codex MCP servers live in the local `~/.codex/config.toml`, initially seeded
  from the platform template in dotfiles.

@RTK.md

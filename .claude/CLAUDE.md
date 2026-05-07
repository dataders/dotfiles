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
- Do not delete critical `~/.dbt/*` symlinks.
- Use explicit overlay hooks only: `secrets.zsh`, `local.zsh`,
  `gitconfig.local`, and `source_dotfiles_env`.
- Use matching repo-backed skills from `.ai/skills`.
- Use `worktrunk` / `wt` for worktrees, never `superpowers:using-git-worktrees`.
- Spawn agent teams via `TeamCreate → TaskCreate → Agent(team_name)`; never `cmux claude-teams`, never bare `Agent(run_in_background=true)`.

@RTK.md

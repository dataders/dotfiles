# Global Development Context

## Shared rules

- Keep changes minimal and focused. Prefer editing existing files.
- Use `uv` for Python packages and scripts; never bare `pip`, `pip3`, or `python3`. Do not use conda or miniforge.
- Keep public config in `~/Developer/dotfiles` and private config in `~/Developer/dotfiles_env`.
- Use explicit private overlay hooks only: `secrets.zsh`, `local.zsh`, `gitconfig.local`, and `source_dotfiles_env`.
- For symlink changes, update `links.tsv` and run `./links.sh dry-run`, `./links.sh check`, and `./links.sh doctor`. Run `apply` only from the primary `~/Developer/dotfiles` checkout; running it from a worktree repoints home symlinks into a temporary checkout.
- Preserve critical `~/.dbt/*` symlinks to `dotfiles_env`. Before committing a changed symlink inside the public dotfiles repo, check that it still is a symlink; atomic replacement can put private data in the public tree.
- Use a matching repo-backed skill from `.ai/skills` or `.agents/skills` when one applies.

## Tools

- Use `rg` for text search, `ast-grep` for syntax patterns, and Serena for symbol meaning across files when available.
- RTK is optional when installed. Use it for noisy output when a summary is enough. Use raw output for debugging, exact matches, test failures, and quoted evidence. Do not delay work to install or locate RTK.

## Worktrees

- Use the current checkout for sequential work when its branch, changes, and active processes are compatible. Create a separate checkout only when concurrent writers need exclusive files, an existing checkout must be preserved, or work needs an independent pinned branch or revision.
- For worktree workflows use the `worktrunk` skill and `wt`, never `superpowers:using-git-worktrees` or agent-managed `isolation: worktree`. In large build repos with repeated parallel work, reuse a bounded pool of clean worktrees and warm build targets. Build artifact size alone does not require a worktree.

## Response style

Be direct and concise. Keep technical terms exact and report evidence and limits.

---
name: cleaning-disk-pressure
description: Use when the user needs more local disk space, hits ENOSPC or disk full errors, asks to clean stale worktrees, caches, target dirs, Trash, or says to preserve running agents, active worktrees, or PR-specific worktrees during cleanup under /Users/dataders/Developer.
---

# Cleaning Disk Pressure

## Overview

Reclaim disk space without losing live work. Always start from live evidence: free space, registered worktrees, active agent cwd paths, PR branch/SHA identity, dirty status, and large generated directories.

## Fast Path

1. Check pressure first.
   ```bash
   df -h / /Users/dataders/Developer
   ```

2. Identify protected worktrees before deletion.
   - Running agents: use `ps`/`lsof` with escalation if sandbox blocks process cwd inspection.
   - PR-specific keeps: verify with `gh pr view <number> --repo <owner/repo> --json headRefName,headRefOid,baseRefName,state,url`.
   - Main/reserved checkouts: never delete the main checkout for a repo.

3. Inventory registered worktrees.
   ```bash
   uv run python3 /Users/dataders/Developer/dotfiles/.ai/skills/cleaning-disk-pressure/scripts/worktree_inventory.py \
     --root /Users/dataders/Developer \
     --protect-path /Users/dataders/Developer/fs \
     --protect-head <pr-head-sha>
   ```

4. Delete only after classification.
   ```bash
   git -C <repo-main> worktree remove --force <worktree-path>
   git -C <repo-main> worktree prune
   ```

5. Verify.
   ```bash
   git -C <repo-main> worktree list --porcelain
   df -h /Users/dataders/Developer
   ```

## Classification Rules

| Evidence | Action |
|---|---|
| Protected by live agent cwd, requested PR SHA/branch, or main checkout | Keep |
| Clean, merged, not protected | Remove |
| Clean, unmerged, pushed | Remove only when user asked to nuke non-protected worktrees |
| Dirty only with generated dirs such as `.venv/`, `target/`, `node_modules/` | `--force` is acceptable after confirming no source edits |
| Dirty source edits or local-only branch | Stop and report exact path, size, branch, and changed files |
| Missing/prunable registration | `git worktree prune` |
| Orphaned backup directory not in `git worktree list` | Inspect first; use `trash`, not `rm -rf`, if user approves |

## Local Notes

- Use `uv`; never call bare `python3` or `pip`.
- `trash` moves files to Trash and may not reclaim space until Trash is emptied.
- Real high-volume Trash path on this machine is `~/.local/share/Trash/files/`; inspect before deleting.
- `git worktree remove --force` deletes the checkout and uncommitted files, but leaves branch refs.
- Stashes are repo-global; do not treat repeated stash counts as per-worktree blockers.

## Common Mistakes

- Deleting by old-looking directory name instead of registered worktree state.
- Treating a PR number as enough context; verify current PR head SHA and branch.
- Deleting a running agent worktree because its shell process is nested several directories down.
- Removing local-only dirty work under disk pressure without reporting the exact risk.

---
name: cleaning-stale-worktrees
description: Use when the user asks to clean up, prune, remove, or "get rid of" stale, old, merged, or unneeded git worktrees (worktrunk `wt` / `git worktree`).
---

# Cleaning Stale Worktrees

## Overview

Remove worktrees that are done with — but **never silently delete unmerged work.**
A worktree is only "stale" if its branch is fully merged into `main` and it has no
uncommitted changes. Anything else is a judgment call that belongs to the user.

Uses `worktrunk` (`wt`), per the standing rule to never use `superpowers:using-git-worktrees`.

## Procedure

1. **Enumerate**
   ```bash
   wt list                 # fallback: git worktree list
   ```

2. **Gather facts for every non-`main` worktree** (decide from facts, never from age alone):
   ```bash
   for b in <branch>...; do
     git merge-base --is-ancestor "$b" main && echo "$b MERGED" || \
       { echo "$b NOT merged:"; git log --oneline main.."$b"; }
   done
   git -C <worktree-path> status --porcelain        # uncommitted changes?
   git ls-remote --heads origin <branch>            # is the work pushed anywhere?
   ```

3. **Classify**

   | Situation | Action |
   |---|---|
   | Merged into `main`, clean | **Stale** → remove |
   | Unique commits, **not pushed** to remote | **STOP — ask the user** (keep / PR / discard) |
   | Unique commits, already pushed | Low risk, but still confirm before removing |
   | Uncommitted changes that are real work | Don't force-remove; ask |
   | Uncommitted changes = trivial drift (`.DS_Store` etc.) | `--force` is fine |

4. **Remove the stale ones**
   ```bash
   wt remove <name>            # merged + clean
   wt remove --force <name>    # only-trivial uncommitted drift (e.g. .DS_Store)
   wt remove -D <name>         # also delete an unmerged branch (only after user OKs)
   ```

5. **Verify**
   ```bash
   git worktree prune          # clear stale admin entries
   wt list                     # confirm only what should remain
   ```

## When work isn't merged but the user wants it gone

If the user chooses "open a PR" for an unmerged branch:
```bash
git -C <worktree-path> push -u origin <branch>
gh pr create --base main --head <branch> --title "..." --body "..."
wt remove --force <name>      # branch survives on origin + locally; nothing lost
```

## Safety Rules — do not violate

- **Never remove a worktree whose only copy of commits is local + unmerged** without explicit user confirmation. Push/PR first, or ask.
- **Never delete the `main` checkout** — sibling worktrees share its `.git`.
- **`wt remove --force` discards uncommitted changes.** Only use it when you've confirmed the change is trivial drift, not real work.
- **Stashes are repo-global**, shared across all worktrees — an identical stash count on every worktree is the shared list, not per-worktree work. Don't treat it as a per-worktree blocker, but inspect (`git stash list`) before any destructive cleanup.
- For any *manual* directory deletion (build artifacts, etc.), prefer `trash` over `rm -rf` (matches the repo's rm-rf guard). Trashing is a same-volume move: space isn't reclaimed until the Trash is emptied.

## Common Mistakes

- Judging "stale" by age (`6d`, `1w`) instead of merge status — old ≠ disposable.
- Running `wt remove --force` to get past a "has uncommitted changes" error without looking at *what* changed.
- Deleting an unmerged branch (`-D`) to "clean up," losing the only copy of the work.

---
name: cleaning-disk-pressure
description: Use when the user needs more local disk space, hits ENOSPC or disk full errors, asks to clean stale worktrees, build artifacts (target/.venv/node_modules), Conductor workspaces, caches, or Trash, or says to preserve running agents, active worktrees, or PR-specific worktrees during cleanup under /Users/dataders/Developer.
---

# Cleaning Disk Pressure

## Overview

Reclaim disk space without losing live work. Always start from live evidence: free space,
machine-wide size ranking (not just `~/Developer`), active agent cwd paths, PR branch/SHA
identity, dirty status, and large generated directories.

The single biggest reclaimable chunk here is almost always **regenerable build output**
(Rust `target/`, `.venv`, `node_modules`), not worktree checkouts themselves — those
directories get duplicated across every nested worktree and Conductor workspace. Sweep
those before spending time on worktree classification.

## Fast Path

1. Check pressure first.
   ```bash
   df -h / /Users/dataders/Developer
   ```

2. Rank the actual offenders before assuming you know where the space went.
   ```bash
   du -d 2 -h ~ 2>/dev/null | sort -rh | head -40
   ```
   Known blind spots that don't show up under `~/Developer` and have been missed
   repeatedly: `~/conductor/workspaces/` (duplicate Rust `target/` copies per workspace),
   `~/.cache/uv`, `~/.cargo`, `~/.rustup`, colima's VM disk, `~/Library`. If the totals
   from step 1 aren't explained by what you can see and measure, assume it's Trash (see
   Local Notes) rather than chasing something exotic like APFS snapshots.

3. Identify live agents by cwd — prefer session metadata over process inspection.
   - If a session-management tool is available (e.g. one that lists other sessions with
     their `cwd`), use it first — it's instant and can't time out.
   - Fall back to `ps`/`lsof` only if that's unavailable. `lsof +D <dir>` is slow on
     multi-GB trees — scope it to one candidate path at a time, not a whole repo, and
     give it a timeout; don't let it eat the whole tool-call budget silently.
   - PR-specific keeps: verify with `gh pr view <number> --repo <owner/repo> --json headRefName,headRefOid,baseRefName,state,url`.
   - Main/reserved checkouts: never delete the main checkout for a repo.

4. Sweep regenerable build artifacts first. Zero-risk regardless of worktree status, and
   consistently the largest single win.
   ```bash
   find /Users/dataders/Developer /Users/dataders/conductor -maxdepth 6 -type d -name target 2>/dev/null \
     -exec du -sh {} + | sort -rh
   ```
   - Rust: `cargo clean` inside the crate root — same effect as `rm -rf`, idiomatic, and
     doesn't fight a build that holds the directory lock.
   - No `clean` target (some `build/` dirs have none): `trash` it, but see the Trash note
     below before counting that as reclaimed space.
   - These duplicate everywhere: nested worktrees, sibling `repo.branch-name` checkouts,
     and Conductor workspaces each carry their own copy (repeatedly seen: three Conductor
     workspaces each holding an identical 20+ G `codex-rs/target`). Sweep every copy, not
     just the main checkout.
   - Rebuilds happen fast under active agent use — a repo swept yesterday needing the same
     sweep again today is normal churn, not a sign anything was missed.

5. Prune stale worktree registrations before inventorying — it's free and cuts noise.
   ```bash
   git -C <repo-main> worktree prune -n -v   # dry run first
   git -C <repo-main> worktree prune
   ```
   Ephemeral test worktrees (pytest tmp dirs, `/tmp/main-wt*`) reliably show up as
   prunable "gitdir file points to non-existent location" entries in any repo whose test
   suite exercises worktrees.

6. Inventory registered worktrees, including nested ones.
   ```bash
   uv run python3 /Users/dataders/Developer/dotfiles/.ai/skills/cleaning-disk-pressure/scripts/worktree_inventory.py \
     --root /Users/dataders/Developer --root /Users/dataders/conductor \
     --protect-path /Users/dataders/Developer/fs \
     --protect-head <pr-head-sha>
   ```
   - Worktrees show up in three shapes here, all equally common: sibling
     `repo.branch-name` directories, `<repo>/.worktrees/<name>` (worktrunk/wt), and
     `<repo>/.claude/worktrees/<name>` (Claude Code's own worktree feature). All three
     appear in `git worktree list --porcelain` for the repo's common `.git` dir — the
     script finds them by walking to that common dir, not by pattern-matching a directory
     name, so don't assume a nested worktree is "hidden" just because a naive `du -sh */`
     glob misses it (dotdirs aren't globbed).
   - The script parallelizes `du`/`git status` per repo and flushes output as it goes. If
     it still runs long on a repo with many worktrees, let it run via `run_in_background`
     rather than re-issuing the same command against the timeout.

7. Classify, re-verify, then delete.
   - Re-run `git status --short` immediately before each removal, not just once during
     inventory — state can flip in between (an agent can start writing mid-cleanup).
   - `git -C <repo-main> worktree remove --force <worktree-path>` then
     `git -C <repo-main> worktree prune`.
   - Worktrees with large `node_modules` or many tracked files can hang the removal's
     status scan — background it (`run_in_background`) instead of letting one slow
     removal block the rest.

8. Verify.
   ```bash
   git -C <repo-main> worktree list --porcelain
   df -h /Users/dataders/Developer
   ```
   If the reclaimed size doesn't match `df`'s delta immediately, it's almost always
   accounting lag — recheck after 30-60s before concluding something is holding the
   blocks. If it's still not adding up after that, the gap is most likely Trash.

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
| Rust `target/`, any `.venv/`, any `node_modules/`, regardless of worktree status | Regenerable — clean it, don't wait on worktree classification first |

## Local Notes

- Use `uv`; never call bare `python3` or `pip`.
- `trash` moves files to `~/.local/share/Trash/files/` and **does not reclaim any space
  until the Trash is emptied** — this has been confirmed repeatedly, not a "may" case.
  Emptying the Trash permanently deletes data, which is outside what this skill will do —
  surface the exact size sitting there and ask the user to empty it themselves.
- `~/.Trash` (the Finder Trash, distinct from the path above) is TCC-blocked from `du`,
  `ls`, and `find` — you cannot measure or empty it. If disk usage is unaccounted for
  after checking everything measurable, say so plainly and name Trash as the likely
  reason, rather than guessing at a number.
- `git worktree remove --force` deletes the checkout and uncommitted files, but leaves
  branch refs — removing a worktree never loses committed work, even on a local-only
  branch.
- Stashes are repo-global; do not treat repeated stash counts as per-worktree blockers.
- Build artifacts regrow fast under active agent use (tens of GB/day has been observed on
  this machine) — treat this as an ongoing sweep, not a one-time fix.

## Common Mistakes

- Deleting by old-looking directory name instead of registered worktree state.
- Treating a PR number as enough context; verify current PR head SHA and branch.
- Deleting a running agent worktree because its shell process is nested several
  directories down — check session cwds first, not just `ps`.
- Removing local-only dirty work under disk pressure without reporting the exact risk.
- Classifying a worktree as clean once during inventory and deleting later without
  re-checking — status can change in between.
- Chasing APFS local snapshots as the explanation for "used didn't drop after deletion" —
  on this machine it has always turned out to be accounting lag, not a snapshot hold.
- Assuming `~/Developer` explains all disk usage — Conductor workspaces and caches
  elsewhere under `$HOME` are common, recurring blind spots.
- Trusting `du -sh */` globs to find nested worktrees — they live under dotdirs
  (`.worktrees/`, `.claude/worktrees/`) that a bare glob won't expand.

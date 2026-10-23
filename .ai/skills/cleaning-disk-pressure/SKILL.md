---
name: cleaning-disk-pressure
description: Use when the user needs more local disk space, hits ENOSPC or disk full errors, asks to clean stale worktrees, build artifacts (target/.venv/node_modules), Conductor workspaces, caches, or Trash, or says to preserve running agents, active worktrees, or PR-specific worktrees during cleanup under ~/Developer (macOS laptop or the Linux remote boxes such as peach01).
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

Paths below use `~`; this machine set is a macOS laptop (`/Users/dataders`, APFS) plus Linux
remote boxes (`/home/anders`, ext4). The filesystem matters — see "Why it refills".

## Fast Path

1. Check pressure first.
   ```bash
   df -hT / ~/Developer
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

   On Linux also look for **loose `<repo>.<name>.target` dirs** next to the checkouts
   (e.g. `~/Developer/fs.replay-main.target`, 26–39G each). They are agent-chosen
   `CARGO_TARGET_DIR`s, not worktrees, so `git worktree list` never shows them. They hold
   only `CACHEDIR.TAG` + `debug/`.
   ```bash
   ls -d ~/Developer/*.target ~/Developer/*-target 2>/dev/null
   ```

3. Identify live agents by cwd — prefer session metadata over process inspection.
   - If a session-management tool is available (e.g. one that lists other sessions with
     their `cwd`), use it first — it's instant and can't time out.
   - On Linux, `/proc` is instant and covers Codex and other agents that the session tool
     can't see. A cwd ending in ` (deleted)` is a process still sitting in a worktree
     that's already gone, so it doesn't protect anything.
     ```bash
     for p in /proc/[0-9]*; do readlink $p/cwd; done 2>/dev/null \
       | grep -oE "$HOME/Developer/[^/]+(/\.(claude/)?worktrees/[^/]+)?" | sort | uniq -c
     ```
     For a loose target dir, check `/proc/*/environ` for a `CARGO_TARGET_DIR` pointing
     at it instead, because builds there run with a cwd elsewhere.
   - Fall back to `ps`/`lsof` only if that's unavailable. `lsof +D <dir>` is slow on
     multi-GB trees — scope it to one candidate path at a time, not a whole repo, and
     give it a timeout; don't let it eat the whole tool-call budget silently.
   - PR-specific keeps: verify with `gh pr view <number> --repo <owner/repo> --json headRefName,headRefOid,baseRefName,state,url`.
   - Main/reserved checkouts: never delete the main checkout for a repo.

4. Sweep regenerable build artifacts first. Zero-risk regardless of worktree status, and
   consistently the largest single win.
   ```bash
   find ~/Developer ~/conductor -maxdepth 6 -type d -name target 2>/dev/null \
     -exec du -sh {} + | sort -rh
   ```
   - Rust: `cargo clean` inside the crate root — same effect as `rm -rf`, idiomatic, and
     doesn't fight a build that holds the directory lock. `rm -rf` is blocked by the
     permission guard anyway, so `cargo clean` is the path that works. Only clean dirs
     that have `CACHEDIR.TAG`, which proves cargo owns them.
   - Loose `*.target` dirs with no worktree of their own: run
     `cargo clean --offline --target-dir <dir>` from any checkout of that repo. It
     deletes exactly that directory.
   - Per-worktree `cargo clean` only works because each worktree has its own `target/`.
     Never "fix" disk use by exporting a shared `CARGO_TARGET_DIR`. Then no worktree can
     be cleaned on its own (`cargo clean -p` hits every worktree at once), parallel agents
     wait on cargo's build lock, and branches with different features invalidate each
     other's builds.
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
   uv run --no-project python -I ~/Developer/dotfiles/.ai/skills/cleaning-disk-pressure/scripts/worktree_inventory.py \
     --root ~/Developer --root ~/conductor \
     --protect-path ~/Developer/fs \
     --protect-head <pr-head-sha>
   ```
   Columns: `status` ignores fs's tracked `target-head-pr/` / `target-origin-main/` stub
   deletions (`--ignore-status ''` to count them). `local` = commits on HEAD that aren't
   on **any** remote ref. `unique` = `local` minus merge commits minus commits whose
   subject matches a commit already on a remote, i.e. rebased or cherry-picked copies.
   `unique` is the number that means "work exists only here". The subject match is a
   heuristic, which is one more reason to take backup refs (step 7).
   - Add PR state per branch in one call rather than per worktree:
     `gh pr list --repo <owner/repo> --state all --author @me --limit 2000 --json headRefName,state,number`.
     Squash-merged PRs have their remote branch deleted, so a merged branch looks
     "unpushed" without this.
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
   - Before removing anything, save every HEAD to a hidden ref. It costs nothing, and it
     makes removal lossless even for detached-HEAD agent worktrees, whose commits have no
     branch to keep them alive:
     ```bash
     git -C <repo-main> update-ref refs/wt-backup/<worktree-basename> <head-sha>
     # restore: git worktree add ../<repo>.<name> refs/wt-backup/<name>
     # drop later: git for-each-ref --format='delete %(refname)' refs/wt-backup | git update-ref --stdin
     ```
   - Remove with `wt remove --foreground -y --no-hooks <worktree-path>`. It deletes the
     branch only if merged, keeps unmerged branches, and refuses dirty trees. If it
     refuses only because of ignorable stub drift (e.g. `target-head-pr/`), confirm that
     is the only change, then add `--force`. Fallback:
     `git -C <repo-main> worktree remove --force <worktree-path>`, then
     `git -C <repo-main> worktree prune`.
   - Worktrees with large `node_modules` or many tracked files can hang the removal's
     status scan — background it (`run_in_background`) instead of letting one slow
     removal block the rest.

8. Verify.
   ```bash
   git -C <repo-main> worktree list --porcelain
   df -h ~/Developer
   ```

## Why it refills

Cleanup alone doesn't stop the regrowth. Check these whenever one repo shows many
20–80G checkouts:

- **`wt step copy-ignored` on a filesystem without reflink.** On APFS it reflinks
  `target/` into each new worktree for free. On ext4 (the Linux remotes) it makes a full
  copy. Without a `.worktreeinclude` it copies **every** gitignored file. The
  worktrunk user config (`dotfiles/.config/worktrunk/config.toml`) guards this to macOS
  with `--require-include`. If a box shows sibling checkouts that each hold a
  full-size `target/`, check that guard first.
- **Sharing compiled deps on Linux is sccache's job, not a shared target dir.**
  `remote/.cargo-config.toml` sets `rustc-wrapper = "sccache"`, and
  `remote/sccache-config.toml` caps `~/.cache/sccache` (60 GiB, LRU). sccache saves build
  *time*, not disk space: each built worktree still holds a full `target/`. The disk win
  comes from fewer live worktrees. `sccache --show-stats` shows hit rate and whether
  the cap is full.
- **Agent worktrees are never removed.** Codex/Claude runs create
  `fs.codex-<topic>-<issue>` siblings and `.claude/worktrees/agent-*` and leave them
  behind after the PR merges or the run stops. That's the steady source of new ones, so
  expect to repeat the sweep (164 → 103 fs worktrees in one pass in Oct 2026).
   If the reclaimed size doesn't match `df`'s delta immediately, it's almost always
   accounting lag — recheck after 30-60s before concluding something is holding the
   blocks. If it's still not adding up after that, the gap is most likely Trash.

## Classification Rules

| Evidence | Action |
|---|---|
| Protected by live agent cwd, requested PR SHA/branch, or main checkout | Keep |
| Clean, merged (ancestor of main, or PR `MERGED`), not protected | Remove |
| Clean, `unique` = 0 (local commits are only merges or copies of remote work), PR not open | Remove after backup refs, with user OK |
| Clean, unmerged, pushed | Remove only when user asked to nuke non-protected worktrees |
| PR `OPEN` | Keep unless the user says otherwise |
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
- Calling a branch "unpushed" because `origin/<same-name>` is missing or behind. Agents
  push under other names and stack many PR branches into integration branches. Use
  `--not --remotes` plus the `unique` count. In Oct 2026 this cut 67 "unpushed" fs
  worktrees down to 22 that really had unique commits.
- Reporting tracked-stub deletions or a regenerated `crates/workspace-hack/Cargo.toml`
  as "uncommitted work". Look at what changed before counting a worktree as dirty.
- Exporting a shared `CARGO_TARGET_DIR` to save space (see step 4). It trades disk for
  lock contention and makes `cargo clean` impossible per worktree.

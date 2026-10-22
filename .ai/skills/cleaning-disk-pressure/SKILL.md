---
name: cleaning-disk-pressure
description: Use when the user needs more local disk space, hits ENOSPC / "No space left on device", asks to clean stale worktrees, build artifacts (target/, target_*, build/, .venv, node_modules), /tmp scratch, caches, or Trash, or says to preserve running agents, active worktrees, or PR-specific worktrees during cleanup. Covers the shared Linux hosts (peach01, nectarine01; ~/Developer under /home/anders) and the Mac (/Users/dataders/Developer).
---

# Cleaning Disk Pressure

## Overview

Reclaim disk space without losing live work. Measure first, plan second, and let the
user run anything that `rm`s. The largest wins are regenerable build output
(`target/`, dbt `target_*` run dirs, `build/`) and idle worktree checkouts, not caches.

Check the host first with `uname -s`; the two hosts fail in different ways.
- **Linux (peach01, nectarine01):** shared ext4 host. `/tmp` is on the root disk,
  there's no reflink, so every copied `target/` is a full copy, and other users' data
  counts in `df` but is invisible to you.
- **macOS:** APFS, Conductor workspaces, Finder Trash. See macOS Notes.

## Hard Rules

- **Plan, then hand off deletes.** Agents may run `cargo clean` and `uv cache prune`.
  Every `rm -rf` goes to the user as one reviewed command: Codex forbids it
  (`~/.codex/rules/default.rules`) and Claude's guard blocks it. Don't route around
  that with `find -delete`, `shutil.rmtree`, a script with a delete flag, or `mv`.
- **Never move things to Trash to free space.** `~/.local/share/Trash` is on the same
  disk. An agent once moved 81 GB there and reclaimed nothing. Report Trash size;
  the user empties it.
- **Never `dbt clean` a run dir**, and don't use Codex's auto-approved
  `rm -rf dbt_packages target` there. Both wipe `target/db`; re-pulling it once cost
  11 minutes.
- **Always pass `--target-dir` to `cargo clean`.** With `CARGO_TARGET_DIR` exported, a
  bare `cargo clean` wipes the shared dir for every worktree using it.
- **Don't push branches or remove worktrees "for safety"** when the problem is build
  output. `cargo clean` is enough.
- **Check for evidence binaries** before cleaning a tree with a debug `dbt`, runner, or
  test binary: nothing running uses it, and no open report or PR cites it.
- **Stop at the goal.** Once free space reaches the user's target (or after the first
  ~100 GB if they gave none), report and ask before going further.

## Fast Path

1. **Measure pressure and your share of it.**
   ```bash
   df -hT / /home /tmp "$HOME" 2>/dev/null   # Linux
   df -h / "$HOME/Developer"                  # macOS
   ```
   On the shared Linux hosts most of `df`'s "used" can belong to other users (about
   750 GB of 1.8 TB on peach01 in Oct 2026). Say so and don't chase it:
   `disk_sweep.py --measure-home` prints "df used minus yours".

2. **Run the plan-only sweep.** In the background (`run_in_background`); it is
   `nice`/`ionice`d and takes minutes on ~150 checkouts. Don't re-issue it against the
   tool timeout.
   ```bash
   uv run python3 "$HOME/Developer/dotfiles/.ai/skills/cleaning-disk-pressure/scripts/disk_sweep.py" \
     --root "$HOME/Developer" --target-free-gb 200
   ```
   For every checkout and nested worktree it sizes ignored or untracked `target`,
   `target_*`, `build`, `vcpkg`, `.venv`, `node_modules` and `logs*`, plus your `/tmp`
   entries, uv caches and Trash. Anything with a live process cwd, open file, or
   `CARGO_TARGET_DIR` (`/proc`), or writes in the last hour, is KEEP. It prints
   agent-safe commands, one user-run `rm` line, and an ask list. It deletes nothing.

3. **Confirm live agents.** Prefer session tools that list other sessions with their
   cwd; the sweep's `/proc` check covers the rest on Linux. On peach01 expect Codex,
   Claude Remote Control sessions, Pi (`pi-webui`), and long `dbt` runs in
   `internal-analytics.*` dirs. Never `lsof +D` a whole tree.
   - PR-specific keeps: `gh pr view <n> --repo <owner/repo> --json headRefName,headRefOid,state`.
   - Never delete the main checkout of a repo.

4. **Reclaim in this order.**
   1. **Agent-safe:** the sweep's `cargo clean --manifest-path … --target-dir …` lines
      for idle cargo targets (20 to 60 GB each on Linux). `cargo clean -p <crate>` is a
      lighter option.
   2. **uv caches:** `uv cache prune` for `~/.cache/uv`, and
      `UV_CACHE_DIR=/tmp/uv-cache uv cache prune` for the cache Codex uses on Linux.
   3. **User-run:** the sweep's `rm -rf` line. It covers idle `.venv`/`node_modules`,
      ignored `build/` with no tracked files, and your `/tmp` entries idle over 24 h.
      Add `target/debug/incremental` of a busy-but-paused target here if needed; it's
      40 to 60 % of a target, but removing it is an `rm`.
   4. **Ask list:** dbt `target_*` run dirs (keep the one a live run writes to),
      `logs*` (run evidence), and untracked dirs like `vcpkg/`.
   5. **Worktrees:** step 5. On peach01 this is the biggest bucket by count
      (139 `fs.*` checkouts at about 2.1 GB each, Oct 2026).

5. **Worktrees.**
   ```bash
   git -C <repo-main> worktree prune -n -v && git -C <repo-main> worktree prune
   uv run python3 "$HOME/Developer/dotfiles/.ai/skills/cleaning-disk-pressure/scripts/worktree_inventory.py" \
     --root "$HOME/Developer" --no-size --protect-head <pr-head-sha>
   ```
   - `--no-size` gives status, idle days, and protection reasons (`main`, `head`,
     `live-cwd:<comm>`) without walking every tree. Drop it to size a shortlist.
   - Worktree shapes: sibling `repo.branch` (wt), sibling `repo.agent-<id>` (Claude
     agent isolation), `<repo>/.worktrees/<name>`, `<repo>/.claude/worktrees/<name>`,
     and jj workspaces. Git lists all but jj. Spot a jj workspace by its `.jj/repo`
     *file* (`cat <dir>/.jj/repo`); don't run `jj` in a colocated repo during cleanup.
     It auto-imports git refs and once abandoned 499 commits mid-cleanup.
   - Classify with the table below. Re-run `git status --short` right before each
     `git -C <repo-main> worktree remove --force <path>`. Background removals of big
     trees.
   - Under Codex, removing a worktree outside the session's cwd needs escalation.
     Start cleanup sessions from `$HOME/Developer` so the sandbox covers every repo.

6. **Verify.** `df` again. A mismatch with the plan is usually accounting lag; recheck
   after 30 to 60 s. Report what was freed, what's still in the user's court, and the
   root causes below.

## Classification Rules

| Evidence | Action |
|---|---|
| Live process cwd, open file or `CARGO_TARGET_DIR`; writes < 1 h; requested PR SHA/branch; main checkout | Keep |
| Idle cargo target (`CACHEDIR.TAG` or `.rustc_info.json`) | `cargo clean --target-dir` (agent) |
| Idle, gitignored `.venv` / `node_modules` / `build` with no tracked files | User `rm -rf` |
| dbt run dir (`target_*` with `manifest.json`, `run_results.json` or `db/`) | Ask; keep the live run's; never `dbt clean` |
| `logs*` | Ask: run evidence |
| Untracked, not ignored (e.g. `vcpkg/`) | Ask |
| Own `/tmp` entry idle > 24 h | User `rm -rf`; keep `/tmp/claude-<uid>` while any Claude session runs |
| Trash | Report size; user empties |
| Worktree clean, merged, not protected | `git worktree remove` |
| Worktree clean, unmerged, pushed | Remove only if the user asked to nuke non-protected worktrees |
| Dirty source edits or local-only branch | Stop; report path, size, branch, changed files |
| Prunable registration | `git worktree prune` |

## Root Causes

Tell the user about these; don't change their config unasked.
- **`wt step copy-ignored`** (`~/.config/worktrunk/config.toml`, `post-start.copy`)
  copies `fs` `target/` into each new worktree via `fs/.worktreeinclude`. On APFS
  that's a free reflink; on ext4 it's a full copy per worktree. On Linux, drop
  `target/` from `~/Developer/fs/.worktreeinclude` or use `git worktree add`. Check
  the config exists on the host first; `remote/links.tsv` doesn't link it.
- **Cargo profile:** `~/.cargo/config.toml` (`debug = "line-tables-only"`) shrinks every
  `target/`. It's linked by `remote/links.tsv`; check with `ls -la ~/.cargo/config.toml`
  after `remote/sync-env.sh`. A profile change invalidates existing artifacts, and
  cargo writes new ones alongside the old. `cargo clean` idle targets right after
  linking it.
- **Parallel agents:** keep a free-space floor (about 40 GB on Linux). One target grew
  from 15 to 44 GB in an hour under an active agent. A shared `CARGO_TARGET_DIR` saves
  space but serializes builds on cargo's lock. Suggest it only for agents on the same
  branch.

## Emergency: Disk Full and Tools Failing

When tool output itself fails (ENOSPC writing temp files), skip the sweep:
1. Pick the oldest idle target, e.g. `ls -dtr "$HOME"/Developer/*/target | head -3`.
2. Confirm no process uses it: `ls -l /proc/*/cwd 2>/dev/null | grep <checkout>`.
3. Run `cargo clean --manifest-path <checkout>/Cargo.toml --target-dir <checkout>/target`.
4. Then run the sweep.

## macOS Notes

- Paths: `/Users/dataders/Developer`. Blind spots: `~/conductor/workspaces/` (one
  20 G+ `codex-rs/target` per workspace), `~/.cache/uv`, `~/.cargo`, `~/.rustup`,
  colima's VM disk, `~/Library`.
- `trash` moves files to `~/.local/share/Trash/files/` and reclaims nothing until the
  user empties it. `~/.Trash` (Finder) is TCC-blocked from `du`, `ls`, and `find`. If
  usage is unaccounted for, name Trash as the likely gap rather than guess.
- "Used didn't drop" has always been accounting lag here, not APFS snapshots.
- There's no `/proc`, so the sweep's in-use check is off. Use session tools, or
  `lsof +D` on one candidate at a time with a timeout.
- BSD-only flags (`stat -f`, `find -flags`) don't exist on Linux. Use `stat -c` and
  `find -printf` there.

## Local Notes

- Use `uv`; never call bare `python3` or `pip`.
- `git worktree remove --force` deletes the checkout and uncommitted files but keeps
  branch refs, so committed work survives even on a local-only branch.
- Stashes are repo-global; don't treat repeated stash counts as per-worktree blockers.
- Build output regrows by tens of GB a day under active agents. Treat cleanup as an
  ongoing sweep.

## Common Mistakes

- Running the Mac commands on Linux: `/Users/dataders` paths fail, and the old
  inventory default silently found nothing.
- Searching only for dirs named exactly `target`. dbt run dirs are `target_*`, and
  they aren't gitignored by `target/`.
- Ignoring `/tmp` on Linux (Codex's `/tmp/uv-cache`, Claude scratchpads, old scratch
  dirs).
- Deleting by old-looking directory name instead of registered worktree state and
  live-process checks.
- Treating a PR number as enough context; verify the current head SHA and branch.
- Classifying once during inventory and deleting later without re-checking status.
- Chasing space owned by other users on a shared host.
- Trusting `du -sh */` globs to find nested worktrees; they live under dotdirs.

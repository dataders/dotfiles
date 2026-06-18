# Source-controlled per-repo Serena config — design

**Date:** 2026-06-18
**Status:** Approved (design); pending implementation plan
**Repo:** `~/Developer/dotfiles` (public)

## Problem

Serena (the MCP code-understanding server) drops a `.serena/` directory into
every repo it works in. Today this directory is **not** gitignored in most
repos (`fs`, `dbt-duckdb`, …), so it shows up as untracked clutter and risks
being committed into OSS repos. At the same time, the per-repo content —
especially Serena's `memories/` — is valuable knowledge that the user wants
**backed up and source-controlled centrally** in the dotfiles repo.

Two desires that seem to conflict:

1. **Gitignored** in each project repo (never pollutes, never accidentally
   committed to OSS).
2. **Source-controlled** centrally in `~/Developer/dotfiles`.

## Background: Serena's config model

Confirmed from Serena's annotated `project.yml` and the configuration docs.

Configuration precedence (low → high):

1. `serena_config.yml` — global defaults (already tracked in dotfiles,
   symlinked to `~/.serena/serena_config.yml`).
2. `project.yml` — per-repo overrides (the `.serena/project.yml` files).
3. contexts + modes.
4. CLI flags.

**Memories** live at `$projectDir/.serena/memories/*.md` — inherently per-repo
with **no global equivalent**. They are the highest-value artifact to preserve.

`cache/` is a regenerable language-server cache — never source-control it.

### What in `project.yml` is genuinely per-repo

Going through all 22 fields, only a handful cannot sensibly be globalized:

| Field | Per-repo? | Reason |
|---|---|---|
| `project_name` | yes | unique identifier |
| `languages` | yes | the real differentiator (bash/rust/python/…) |
| `initial_prompt` | yes | repo-specific LLM context |
| `additional_workspace_folders` | yes | monorepo sibling paths |
| `ignored_paths` | yes | repo-specific (global ones merge additively) |
| `read_only` | yes | per-repo intent |
| `ignore_all_files_in_gitignore` | semi | only a `project.yml` field (no global key); relies on Serena's built-in `true` default |
| everything else | no | already has a global default in `serena_config.yml`, or a sane built-in default; the stub leaves it unset to inherit |

`serena_config.yml` already globalizes: `language_backend` (LSP),
`line_ending` (native), `base_modes` (interactive, editing), `tool_timeout`,
`symbol_info_budget`, the tool include/exclude/fixed lists, and the
`ignored_memory_patterns`. It also maintains a `projects:` registry.

**Implication:** the "globalize" half is largely already done. The remaining
work is to define a *minimal stub* `project.yml` and ensure no per-repo file
duplicates a global default.

A thin-pointer trick (like the `.envrc` → `source_dotfiles_env` pattern) is
**not possible** for Serena: `project.yml` has no include/source directive. The
only mechanisms are **symlink** or **copy**. This design uses symlinks (live
capture), consistent with the repo's symlink-native, `links.tsv`-driven
philosophy.

## Design

### 1. Global ignore

Add `.serena/` to the global gitignore (`~/.gitignore_global`, tracked in
dotfiles). This stops `.serena/` from appearing in any repo, and subsumes any
need to separately ignore `.serena/cache/` (it's a child of an ignored dir).

Already-tracked `.serena/` files in the dotfiles repo itself remain tracked
(git ignores `.gitignore` entries for paths already under version control), so
nothing about dotfiles' own Serena config breaks. **Precondition to verify in
the plan:** `dotfiles/.serena/project.yml` is actually committed (not merely
present on disk) before the global ignore lands — an *untracked* file there
*would* become newly ignored.

### 2. Central home in dotfiles

```
dotfiles/serena/projects/<repo>/
    project.yml        # minimal stub — real file, committed
    memories/          # fills up as Serena writes; committed
```

`cache/` is never centralized; it stays a local, ignored, regenerable dir in
each project.

### 3. Symlink wiring (per repo, via links.tsv)

Two rows per repo. Example for `fs` (under `~/Developer`, so use the existing
`developer:` target prefix — consistent with rows like
`developer:fs/.vscode/settings.json`):

```
repo:serena/projects/fs/project.yml   developer:fs/.serena/project.yml   agents  public  serena per-repo config
repo:serena/projects/fs/memories      developer:fs/.serena/memories      agents  public  serena per-repo memories
```

Repos **not** under `~/Developer` would instead use a `home:`/absolute target;
`serena-link` chooses the prefix from the path. `group` is `agents` (matching
the existing `serena_config.yml` row); rows are appended (the file is grouped
loosely, not strictly sorted, so append is acceptable).

`./links.sh apply` creates the symlinks. **Confirmed against `links.sh`:**
`expand_path` resolves nested targets (`developer:fs/.serena/project.yml`) and
`ensure_parent` runs `mkdir -p` on the target's parent; `ln -sfn` symlinks a
directory (`memories/`) correctly; and `check`/`unlink`/`doctor` operate on
`-L`/`readlink`, which are symlink-type-agnostic.

The symlink direction matches all existing dotfiles symlinks: **the pointer
lives in the project, the committed truth lives in dotfiles** (just like
`~/.zshrc → dotfiles/.zshrc`). Serena reads/writes through the symlink; edits
and new memory files land in dotfiles as plain files the user commits. Because
`.serena/` is globally gitignored, the symlinks never appear in the project
repo's `git status`.

**Constraint:** `./links.sh apply` must be run only from the **primary checkout**
(`~/Developer/dotfiles`), never from a worktree/Conductor workspace — running it
from a worktree repoints `~` symlinks into a throwaway checkout. (The dotfiles
repo is worked on directly on `main`, not in worktrees, so this is the normal
case.)

**dotfiles is special-cased:** its own `.serena/project.yml` is already tracked
in place, so it receives **no** symlink rows.

### 4. The `serena-link` helper (`bin/serena-link`)

Removes the per-repo setup toil. `serena-link <repo-path>`:

1. Resolve repo name = basename of the path; choose the `links.tsv` target
   prefix from the path (`developer:` if under `~/Developer`, else `home:`/abs).
2. **Collision guard (blocking requirement):** if `dotfiles/serena/projects/<name>/`
   already exists, refuse and require an explicit override name. Two repos with
   the same basename (e.g. `~/Developer/fs` and a future `~/work/fs`) must not
   silently share/clobber config + memories.
3. Create `dotfiles/serena/projects/<name>/`.
4. **Move** any existing real `.serena/project.yml` into it; otherwise write a
   minimal stub (see §5).
5. Remove the (empty) real `.serena/memories/` dir, then create `memories/` in
   dotfiles. Removing first avoids the `ln -sfn src existing_dir` gotcha
   (verified: when the target is a real directory the symlink is created
   *inside* it as `memories/<src>`, rather than replacing it).
6. Append the two `links.tsv` rows.
7. Print instructions to run `./links.sh apply` from the primary checkout.
   **Refuse if invoked against a worktree copy of dotfiles** — the hazard is
   editing a throwaway checkout's `links.tsv` and later applying from it. The
   guard is about *which dotfiles checkout's `links.tsv` is being edited*; the
   move of the project's own `.serena/project.yml` is independent of that.

Moving/removing the real files **before** apply is required because `links.sh`
deliberately refuses to clobber a non-symlink target
(`refusing to replace non-symlink target`).

### 5. Minimal stub schema

```yaml
project_name: "<repo>"
languages:
  - <lang>
ignore_all_files_in_gitignore: true   # built-in Serena default; set explicitly for clarity
# everything else inherited from serena_config.yml or Serena built-in defaults
```

`languages` is best-effort: the user sets it per repo; the helper may default to
a guess or leave a TODO comment.

### 6. Migration

Run `serena-link` once per existing repo in the `serena_config.yml` `projects:`
registry — 11 repos, skipping both `dotfiles` (special-cased, tracked in place)
and the ephemeral conductor workspace at `~/conductor/workspaces/...`. Re-derive
the actual set from the registry at execution time rather than trusting a fixed
count. Memories are empty today, so migration is a clean move of just the stub
configs.

## Recovery / failure modes

- **Broken `memories/` symlink + Serena recreates a real dir.** Serena normally
  writes *through* the symlink, so the real dir won't reappear. But if the
  symlink is removed and Serena then runs, it recreates a real `memories/` dir;
  a subsequent `links.sh apply` would hit the `ln -sfn` gotcha and a later
  `check`/`doctor` reports `FAIL … is not a symlink`. `links.sh` offers no
  auto-recovery for this — recovery is manual: remove the real `memories/` dir,
  then re-apply. The plan should document this in the helper's `--help`/README.

## Scope / non-goals (YAGNI)

- **No automatic new-repo detection.** The user runs `serena-link` when adopting
  Serena in a new repo. Discovery automation can be added later if manual
  invocation becomes annoying.
- **No bidirectional sync logic.** Symlinks make capture live; there is nothing
  to sync.
- **No migration of memory content** (none exists yet).

## Resolved during spec review

- `links.sh` nested-target resolution (`developer:`/`home:` with subpaths): **works.**
- `links.sh` directory symlinking for `memories/` via `ln -sfn`: **works**; `check`/`unlink`/`doctor` are symlink-type-agnostic.
- `ln -sfn src existing_dir` gotcha: **real**; mitigated by removing the empty dir first (§4 step 5).
- Duplicate basenames: addressed by the collision guard (§4 step 2).
- `links.tsv` prefix/group/ordering: use `developer:` (or path-derived), `group=agents`, append.

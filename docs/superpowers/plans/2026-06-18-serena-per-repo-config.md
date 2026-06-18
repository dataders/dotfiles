# Source-controlled per-repo Serena config — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each repo's Serena `.serena/project.yml` + `memories/` globally gitignored (never pollute a repo) while being source-controlled centrally in dotfiles via symlinks.

**Architecture:** Global-ignore `.serena/` everywhere; store the real per-repo files at `dotfiles/serena/projects/<repo>/`; symlink them back into each repo through `links.tsv`/`links.sh`. A `bin/serena-link` helper automates per-repo setup (move/stub the config, clear the empty `memories/` dir, append the manifest rows). Serena then reads/writes through the symlinks, so edits and new memories land in dotfiles as committable plain files.

**Tech Stack:** zsh (helper + `links.sh`), Python `unittest` (existing test harness invoking shell in a sandboxed `DOTFILES_ROOT`), git.

**Spec:** `docs/superpowers/specs/2026-06-18-serena-per-repo-config-design.md`

**Working context:** This repo is worked on **directly on `main`, never in a worktree** (`worktree.bgIsolation: none`). `./links.sh apply` is therefore always run from the primary checkout, which is the required safe location.

---

## File structure

- `.gitignore_global` — add `.serena/` (tracked; symlinked to `~/.gitignore_global`).
- `serena/projects/<repo>/project.yml` — per-repo stub/config (real file, committed).
- `serena/projects/<repo>/memories/` — per-repo memories (committed as they appear).
- `serena/README.md` — short explainer of the scheme.
- `bin/serena-link` — helper to register a repo (zsh).
- `tests/test_serena_link.py` — unittest coverage for the helper.
- `links.tsv` — two rows appended per migrated repo.
- `AGENTS.md` — document the scheme + helper.

---

## Task 1: Global-ignore `.serena/`

**Files:**
- Modify: `.gitignore_global`

- [ ] **Step 1: Confirm dotfiles' own Serena files are committed (precondition)**

Run:
```bash
cd ~/Developer/dotfiles
git ls-files .serena/project.yml .serena/serena_config.yml
```
Expected: both paths printed (tracked). If `project.yml` is missing, `git add .serena/project.yml && git commit -m "chore: track dotfiles serena project.yml"` BEFORE proceeding — an untracked file there would become newly ignored.

- [ ] **Step 2: Add the ignore rule**

Edit `.gitignore_global`, append:
```
# Serena MCP per-repo dirs. The real project.yml + memories/ live in
# dotfiles/serena/projects/<repo>/ and are symlinked back in (see serena/README.md).
# cache/ is regenerable. dotfiles' own .serena/* stays tracked (already committed).
.serena/
```

- [ ] **Step 3: Verify it ignores other repos but not dotfiles' tracked files**

Run:
```bash
cd ~/Developer/fs && git check-ignore .serena && echo "fs .serena IGNORED (good)"
cd ~/Developer/dotfiles && git status --porcelain .serena/ && echo "<-- dotfiles .serena still shows tracked state (empty or staged), not ignored"
git check-ignore .serena/project.yml; echo "exit=$? (1 = NOT ignored, good — already tracked)"
```
Expected: `fs` reports ignored; dotfiles' tracked `.serena/project.yml` is still tracked (`git check-ignore` exits 1 for it because already-tracked beats gitignore).

- [ ] **Step 4: Commit**

```bash
git add .gitignore_global
git commit -m "chore: globally gitignore .serena/ (per-repo serena dirs)"
```

---

## Task 2: Central layout + README

**Files:**
- Create: `serena/README.md`
- Create: `serena/projects/.gitkeep`

- [ ] **Step 1: Create the directory + keepfile**

```bash
mkdir -p ~/Developer/dotfiles/serena/projects
touch ~/Developer/dotfiles/serena/projects/.gitkeep
```

- [ ] **Step 2: Write `serena/README.md`**

```markdown
# Serena per-repo config

Serena writes a `.serena/` dir into every repo it works in. `.serena/` is
globally gitignored, so it never pollutes a repo. The per-repo **truth** lives
here and is symlinked back into each repo:

```
serena/projects/<repo>/
    project.yml   # minimal stub (project_name + languages); rest inherited
    memories/     # Serena's notes; fills up over time
```

`<repo>/.serena/project.yml` and `<repo>/.serena/memories/` are symlinks into
this tree (via `links.tsv`), so Serena's writes land here as committable files.
`cache/` is never tracked.

Register a repo with `bin/serena-link <repo-path>`, then run `./links.sh apply`
from the primary checkout. The dotfiles repo itself is special-cased: its own
`.serena/project.yml` is tracked in place with no symlink.
```

- [ ] **Step 3: Commit**

```bash
git add serena/README.md serena/projects/.gitkeep
git commit -m "docs: serena/projects central layout + README"
```

---

## Task 3: `bin/serena-link` helper (TDD)

**Files:**
- Create: `bin/serena-link`
- Test: `tests/test_serena_link.py`

The helper mirrors `links.sh` env conventions (`DOTFILES_ROOT`, `DOTFILES_DEVELOPER`, `DOTFILES_MANIFEST`) so tests can sandbox it.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_serena_link.py`:
```python
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class SerenaLinkTests(unittest.TestCase):
    def run_link(self, repo_path, root, developer, *extra):
        env = os.environ.copy()
        env.update(
            {
                "DOTFILES_ROOT": str(root),
                "DOTFILES_DEVELOPER": str(developer),
                "DOTFILES_MANIFEST": str(root / "links.tsv"),
            }
        )
        return subprocess.run(
            ["zsh", str(ROOT / "bin" / "serena-link"), str(repo_path), *extra],
            cwd=ROOT, env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )

    def _sandbox(self, tmp):
        root = tmp / "dotfiles"
        (root / "serena" / "projects").mkdir(parents=True)
        (root / "links.tsv").write_text("")
        developer = tmp / "Developer"
        developer.mkdir()
        return root, developer

    def test_stub_created_and_rows_appended(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            root, developer = self._sandbox(tmp)
            repo = developer / "foo"
            repo.mkdir()
            r = self.run_link(repo, root, developer, "--lang", "python")
            self.assertEqual(r.returncode, 0, r.stderr)
            yml = (root / "serena/projects/foo/project.yml").read_text()
            self.assertIn('project_name: "foo"', yml)
            self.assertIn("- python", yml)
            self.assertTrue((root / "serena/projects/foo/memories").is_dir())
            manifest = (root / "links.tsv").read_text()
            self.assertIn(
                "repo:serena/projects/foo/project.yml\tdeveloper:foo/.serena/project.yml\tagents\tpublic\tserena per-repo config",
                manifest,
            )
            self.assertIn(
                "repo:serena/projects/foo/memories\tdeveloper:foo/.serena/memories\tagents\tpublic\tserena per-repo memories",
                manifest,
            )

    def test_existing_project_yml_is_moved(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            root, developer = self._sandbox(tmp)
            repo = developer / "bar"
            (repo / ".serena").mkdir(parents=True)
            (repo / ".serena" / "project.yml").write_text('project_name: "bar"\nlanguages:\n- rust\n')
            r = self.run_link(repo, root, developer)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((repo / ".serena" / "project.yml").exists())
            self.assertIn("- rust", (root / "serena/projects/bar/project.yml").read_text())

    def test_empty_memories_dir_removed(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            root, developer = self._sandbox(tmp)
            repo = developer / "baz"
            (repo / ".serena" / "memories").mkdir(parents=True)
            r = self.run_link(repo, root, developer, "--lang", "go")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((repo / ".serena" / "memories").exists())

    def test_collision_guard(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            root, developer = self._sandbox(tmp)
            repo = developer / "dup"
            repo.mkdir()
            self.assertEqual(self.run_link(repo, root, developer, "--lang", "python").returncode, 0)
            r2 = self.run_link(repo, root, developer, "--lang", "python")
            self.assertNotEqual(r2.returncode, 0)
            self.assertIn("already exists", r2.stderr)

    def test_refuses_worktree_checkout(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            _, developer = self._sandbox(tmp)
            wt_root = tmp / ".claude" / "worktrees" / "x" / "dotfiles"
            (wt_root / "serena" / "projects").mkdir(parents=True)
            (wt_root / "links.tsv").write_text("")
            repo = developer / "wtrepo"
            repo.mkdir()
            r = self.run_link(repo, wt_root, developer, "--lang", "python")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("worktree", r.stderr.lower())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest tests.test_serena_link -v`
Expected: errors/failures (file `bin/serena-link` does not exist yet).

- [ ] **Step 3: Implement `bin/serena-link`**

Create `bin/serena-link` (and `chmod +x`):
```zsh
#!/usr/bin/env zsh
# serena-link — register a repo's Serena per-repo config (.serena/project.yml +
# memories/) into dotfiles so it is source-controlled centrally and symlinked back.
#
# Usage: serena-link <repo-path> [--name <override>] [--lang <language>]
#
# After running, apply the new symlinks from the PRIMARY dotfiles checkout:
#   ./links.sh apply
set -u

repo_root="${DOTFILES_ROOT:-${0:A:h:h}}"
# Canonicalize roots so prefix matching survives macOS /var -> /private/var
# (repo_path is :A-canonicalized below, so the roots must be too).
developer_root="${DOTFILES_DEVELOPER:-$HOME/Developer}"
developer_root="${developer_root:A}"
home_dir="${HOME:A}"
manifest="${DOTFILES_MANIFEST:-$repo_root/links.tsv}"
tab=$'\t'

die() { print -r -- "serena-link: $*" >&2; exit 1; }

usage() {
    cat <<'EOF'
serena-link — register a repo's Serena per-repo config (.serena/project.yml +
memories/) into dotfiles so it is source-controlled centrally and symlinked back.

Usage: serena-link <repo-path> [--name <override>] [--lang <language>]

After running, apply from the PRIMARY dotfiles checkout:  ./links.sh apply
EOF
}

override_name=""
lang=""
repo_path=""
while (( $# )); do
    case "$1" in
        --name) override_name="${2:-}"; shift 2 ;;
        --lang) lang="${2:-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) repo_path="$1"; shift ;;
    esac
done
[[ -n "$repo_path" ]] || die "missing <repo-path>"

# refuse to edit a worktree copy of dotfiles (would mutate a throwaway links.tsv)
case "$repo_root" in
    */.claude/worktrees/*) die "refusing to run against a worktree checkout: $repo_root (run from the primary dotfiles checkout)" ;;
esac

repo_path="${repo_path:A}"
[[ -d "$repo_path" ]] || die "not a directory: $repo_path"
name="${override_name:-${repo_path:t}}"

dest="$repo_root/serena/projects/$name"
[[ -e "$dest" ]] && die "serena/projects/$name already exists; pass --name <override>"

# choose links.tsv target prefix
if [[ "$repo_path" == "$developer_root"/* ]]; then
    target="developer:${repo_path#$developer_root/}"
elif [[ "$repo_path" == "$home_dir"/* ]]; then
    target="home:${repo_path#$home_dir/}"
else
    target="abs:$repo_path"
fi

mkdir -p "$dest/memories"

# project.yml: move an existing real file, else write a minimal stub
src_yml="$repo_path/.serena/project.yml"
if [[ -f "$src_yml" && ! -L "$src_yml" ]]; then
    mv "$src_yml" "$dest/project.yml"
else
    : "${lang:=TODO}"
    cat > "$dest/project.yml" <<EOF
project_name: "$name"
languages:
- $lang
ignore_all_files_in_gitignore: true
EOF
fi

# memories: migrate any files, then remove the real dir so links.sh can symlink it
src_mem="$repo_path/.serena/memories"
if [[ -d "$src_mem" && ! -L "$src_mem" ]]; then
    if [[ -n "$(ls -A "$src_mem" 2>/dev/null)" ]]; then
        mv "$src_mem"/*(DN) "$dest/memories/"
    fi
    rm -rf "$src_mem"
fi

# append manifest rows
{
    print -r -- "repo:serena/projects/$name/project.yml${tab}${target}/.serena/project.yml${tab}agents${tab}public${tab}serena per-repo config"
    print -r -- "repo:serena/projects/$name/memories${tab}${target}/.serena/memories${tab}agents${tab}public${tab}serena per-repo memories"
} >> "$manifest"

print -r -- "Registered '$name' -> serena/projects/$name (target $target)."
print -r -- "Now run from the primary dotfiles checkout:  ./links.sh apply"
```

- [ ] **Step 4: Make executable + run tests**

Run:
```bash
chmod +x ~/Developer/dotfiles/bin/serena-link
uv run python -m unittest tests.test_serena_link -v
```
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add bin/serena-link tests/test_serena_link.py
git commit -m "feat: serena-link helper to source-control per-repo serena config"
```

---

## Task 4: Migrate existing repos

Migrate the 11 repos in the `serena_config.yml` `projects:` registry, **excluding** `dotfiles` (special-cased) and the ephemeral conductor workspace.

Languages are best-effort — verify each repo before/after (open the generated stub and fix `languages:` if wrong).

| repo | languages (verify) |
|---|---|
| dbt-agent-skills | python |
| dbt-clickhouse | python |
| dbt-duckdb | python |
| dbt-fusion-clickhouse-demo | python |
| dbt_aws_cloud_cost | python |
| duckdb-iceberg | python |
| fs | rust |
| fusion_issue_analysis | python |
| hydrate.ai | python |
| internal-analytics | python |
| james-river-gooners | python |

- [ ] **Step 1: Register each repo**

Run (adjust `--lang` per the table; inspect the repo if unsure):
```bash
cd ~/Developer/dotfiles
for r in dbt-agent-skills dbt-clickhouse dbt-duckdb dbt-fusion-clickhouse-demo \
         dbt_aws_cloud_cost duckdb-iceberg fusion_issue_analysis hydrate.ai \
         internal-analytics james-river-gooners; do
  bin/serena-link ~/Developer/$r --lang python
done
bin/serena-link ~/Developer/fs --lang rust
```
Expected: one "Registered ..." line per repo; 22 new rows in `links.tsv`; `serena/projects/<repo>/` created for each.

Confirm the row count (catches a typo'd repo name that silently produced no row):
```bash
grep -c "serena per-repo" links.tsv   # expect 22
```
Also re-derive the actual repo set from the registry rather than trusting this list:
```bash
grep -A99 "^projects:" .serena/serena_config.yml | grep "Developer/"
```

- [ ] **Step 2: Verify the stubs, fix languages if needed**

Run: `grep -r "languages:" -A1 ~/Developer/dotfiles/serena/projects/`
Open and correct any repo whose detected language is wrong (e.g. a JS/TS repo).

- [ ] **Step 3: Dry-run the new links**

Run: `./links.sh dry-run`
Expected: `DRY-RUN ln -sfn ... serena/projects/<repo>/{project.yml,memories}` lines, no errors. Resolve any `FAIL` (e.g. a leftover non-symlink target means a real file still sits in a repo's `.serena/`).

- [ ] **Step 4: Apply from the primary checkout**

Run: `./links.sh apply`
Expected: `LINK ~/Developer/<repo>/.serena/project.yml -> .../serena/projects/<repo>/project.yml` (and memories) per repo, no `FAIL`.

- [ ] **Step 5: Verify links resolve**

Run:
```bash
./links.sh check
readlink ~/Developer/fs/.serena/project.yml
ls -l ~/Developer/fs/.serena/memories
cd ~/Developer/fs && git status --porcelain .serena/   # expect EMPTY (globally ignored)
```
Expected: `check` prints `OK ...` for each new entry; symlinks point into dotfiles; `fs` shows no `.serena/` clutter.

- [ ] **Step 6: Commit**

```bash
cd ~/Developer/dotfiles
git add links.tsv serena/projects/
git commit -m "feat: migrate existing repos to source-controlled serena config"
```

---

## Task 5: Document the scheme in AGENTS.md

**Files:**
- Modify: `AGENTS.md` (Serena/MCP section)

- [ ] **Step 1: Add a short subsection**

Add near the MCP/Serena config notes:
```markdown
### Serena per-repo config

`.serena/` is globally gitignored. Per-repo `project.yml` + `memories/` live in
`serena/projects/<repo>/` and are symlinked back via `links.tsv`. Register a new
repo with `bin/serena-link <repo-path> [--lang <lang>]`, then `./links.sh apply`
from the primary checkout. dotfiles' own `.serena/project.yml` is tracked in
place (no symlink). Recovery: if a `memories/` symlink breaks and Serena
recreates a real dir, remove it before re-running `./links.sh apply`.
```

- [ ] **Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs: document serena per-repo config scheme in AGENTS.md"
```

---

## Final verification

- [ ] `uv run python -m unittest tests.test_links tests.test_serena_link -v` — all pass.
- [ ] `./links.sh check` — all `OK`, no `FAIL`.
- [ ] `git -C ~/Developer/fs status --porcelain .serena/` — empty (ignored).
- [ ] `git -C ~/Developer/dotfiles log --oneline -6` — shows the 5 task commits.

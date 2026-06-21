# dbt Wizard Config Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Source-control dbt Wizard's non-secret settings via the dotfiles symlink convention and maximize config overlap with the Claude/Codex setups (shared rules file, shared AGENTS.md, mirrored MCP servers).

**Architecture:** Canonical Wizard config lives in a new tracked `dotfiles/wizard/` dir, symlinked into `~/.dbt/wizard/` through `links.tsv` (the `.dbt/` gitignore stays intact). Command-approval rules and global instructions are shared with Codex/Claude by symlinking Wizard's slots to the existing canonical files (`.codex/rules/default.rules`, `AGENTS.md`). MCP servers are mirrored from Codex into Wizard's `config.toml` (Codex-schema fork).

**Tech Stack:** zsh (`links.sh`), TOML (`config.toml`, `wizard_config.toml`), JSON (`providers.json`), Codex `prefix_rule(...)` rules DSL, Python `unittest` (`tests/test_links.py`).

**Spec:** `docs/superpowers/specs/2026-06-01-wizard-config-consolidation-design.md`

**Branch:** `wizard-config-consolidation` (already created).

---

## Pre-flight (one-time, no commit)

- [ ] **Confirm current state**

Run:
```bash
cd /Users/dataders/Developer/dotfiles
ls -la ~/.dbt/wizard/config.toml ~/.dbt/wizard/wizard_config.toml ~/.dbt/wizard/providers.json
readlink ~/.dbt   # expect: /Users/dataders/Developer/dotfiles/.dbt
```
Expected: three regular files (not symlinks); `~/.dbt` is a symlink into the repo.

---

## Task 1: Create canonical source dir and migrate files

**Files:**
- Create: `dotfiles/wizard/config.toml` (copied from live)
- Create: `dotfiles/wizard/wizard_config.toml` (copied from live)
- Create: `dotfiles/wizard/providers.json` (copied from live)

- [ ] **Step 1: Make the source dir and copy live content into it**

Copy the real files (resolving through the `~/.dbt` symlink) into the new tracked dir. Copy content, do NOT move — the originals get replaced by symlinks in Task 5, and we want the canonical copy in place first.

```bash
cd /Users/dataders/Developer/dotfiles
mkdir -p wizard
cp ~/.dbt/wizard/config.toml         wizard/config.toml
cp ~/.dbt/wizard/wizard_config.toml  wizard/wizard_config.toml
cp ~/.dbt/wizard/providers.json      wizard/providers.json
```

- [ ] **Step 2: Verify copies are byte-identical to the live files**

Run:
```bash
diff ~/.dbt/wizard/config.toml        wizard/config.toml        && echo "config OK"
diff ~/.dbt/wizard/wizard_config.toml wizard/wizard_config.toml && echo "wizard_config OK"
diff ~/.dbt/wizard/providers.json     wizard/providers.json     && echo "providers OK"
```
Expected: three "OK" lines, no diff output.

- [ ] **Step 3: Confirm no secrets landed in the copies**

Run:
```bash
grep -rIlE 'sk-|bearer|api[_-]?key|access_token|refresh_token|"secret"' wizard/ || echo "no secrets"
```
Expected: `no secrets`. (If anything matches, STOP and re-evaluate before continuing.)

- [ ] **Step 4: Commit**

```bash
git add wizard/config.toml wizard/wizard_config.toml wizard/providers.json
git commit -m "wizard: track config, project state, and provider catalog as canonical sources"
```

---

## Task 2: Add links.tsv entries

**Files:**
- Modify: `links.tsv` (append 5 rows)

- [ ] **Step 1: Append the manifest rows**

Append these tab-separated rows to `links.tsv` (use real tabs, matching existing rows). Group `agents`, visibility `public`. The two shared-file rows reuse existing sources (`.codex/rules/default.rules`, `AGENTS.md`) with new Wizard targets — `links.sh` is manifest-driven and already supports one source mapping to multiple targets (see the three `repo:.vscode/settings.json` rows).

```
repo:wizard/config.toml	home:.dbt/wizard/config.toml	agents	public	Wizard general config (Codex schema)
repo:wizard/wizard_config.toml	home:.dbt/wizard/wizard_config.toml	agents	public	Wizard per-project state
repo:wizard/providers.json	home:.dbt/wizard/providers.json	agents	public	Wizard model provider catalog
repo:.codex/rules/default.rules	home:.dbt/wizard/rules/default.rules	agents	public	Shared Codex/Wizard command-approval rules
repo:AGENTS.md	home:.dbt/wizard/AGENTS.md	agents	public	Shared global agent instructions
```

- [ ] **Step 2: Verify the manifest parses (dry-run)**

Run:
```bash
cd /Users/dataders/Developer/dotfiles
./links.sh dry-run 2>&1 | grep -E 'wizard|unknown path prefix'
```
Expected: five `DRY-RUN ln -sfn ...` lines for the wizard targets; **no** `unknown path prefix` lines.

- [ ] **Step 3: Commit**

```bash
git add links.tsv
git commit -m "wizard: add symlink manifest entries (config + shared rules + shared AGENTS.md)"
```

---

## Task 3: Clean and extend the shared command-approval rules

**Files:**
- Modify: `.codex/rules/default.rules`

This file becomes the single source of truth for Codex AND Wizard. Cleaning removes session-accumulated cruft; folding in Wizard's allows keeps both tools working.

- [ ] **Step 1: Identify the durable/cruft boundary**

Run:
```bash
cd /Users/dataders/Developer/dotfiles
grep -n 'prefix_rule' .codex/rules/default.rules | tail -50
```
The curated durable block ends at the last multi-line `prefix_rule(...)` with a `justification=` (the `sort -u` rule). Everything after that — the terse single-line `prefix_rule(pattern=[...], decision="allow")` entries containing machine-specific worktree paths, `kill <PID>`, the multi-line `gh pr create ...` blob, and duplicates of earlier rules (`gh api`, `gh pr list`, `git fetch`, `git push`, etc.) — is the cruft to remove.

- [ ] **Step 2: Delete the auto-appended one-off block**

Edit `.codex/rules/default.rules`: remove every `prefix_rule(...)` line below the curated `sort -u` rule. Keep the curated block intact (the `forbidden` set + the structured `allow` rules with `justification=`/`match=`).

- [ ] **Step 3: Append Wizard-specific allows to the curated block**

Add these three rules to the end of the curated block (after the `sort -u` rule). They mirror Wizard's original `rules/default.rules`:

```python
prefix_rule(
    pattern = ["wizard"],
    decision = "allow",
    justification = "Wizard CLI self-invocation is trusted.",
    match = ["wizard exec", "wizard doctor"],
)

prefix_rule(
    pattern = ["pkill", "-f", "^wizard$"],
    decision = "allow",
    justification = "Cleaning up a stuck Wizard process is trusted.",
)

prefix_rule(
    pattern = ["rm", "-rf", "dbt_packages", "target"],
    decision = "allow",
    justification = "Clearing dbt build artifacts is routine (specific override of the general rm -rf forbid).",
)
```

- [ ] **Step 4: Verify Codex still loads the rules**

Run:
```bash
cd /Users/dataders/Developer/dotfiles
codex debug prompt-input 'echo hi' 2>&1 | head -5 || true
grep -c 'prefix_rule' .codex/rules/default.rules
```
Expected: rule count is the curated-block count + 3, no parse errors. (If `codex debug` is unavailable, confirm the file is valid by eyeballing balanced parens.)

- [ ] **Step 5: Commit**

```bash
git add .codex/rules/default.rules
git commit -m "rules: prune machine-specific one-offs, add Wizard allows for shared Codex/Wizard ruleset"
```

---

## Task 4: Mirror Codex MCP servers into Wizard's config.toml

**Files:**
- Modify: `wizard/config.toml`

- [ ] **Step 1: Append all `[mcp_servers.*]` blocks**

Append the following to `wizard/config.toml`, preserving the existing top keys (`model`, `model_reasoning_effort`, the `[projects.*]` trust entry). These are copied verbatim from `.codex/config.toml` with two adjustments: (a) `serena` keeps `--context=codex` (Wizard is a Codex fork), (b) the duplicate `google-sheets` server is dropped (the canonical name `google_sheets` is kept).

```toml
[mcp_servers.github]
url = "https://dbt.runlayer.com/api/v1/proxy/7e8a07e2-98ed-4c76-8edb-d8a68b55bccc/mcp"
bearer_token_env_var = "GITHUB_PAT_MCP"

[mcp_servers.github.tools.add_comment_to_pending_review]
approval_mode = "approve"
[mcp_servers.github.tools.add_issue_comment]
approval_mode = "approve"
[mcp_servers.github.tools.add_reply_to_pull_request_comment]
approval_mode = "approve"
[mcp_servers.github.tools.create_branch]
approval_mode = "approve"
[mcp_servers.github.tools.create_or_update_file]
approval_mode = "approve"
[mcp_servers.github.tools.create_pull_request]
approval_mode = "approve"
[mcp_servers.github.tools.fork_repository]
approval_mode = "approve"
[mcp_servers.github.tools.issue_write]
approval_mode = "approve"
[mcp_servers.github.tools.pull_request_review_write]
approval_mode = "approve"
[mcp_servers.github.tools.sub_issue_write]
approval_mode = "approve"
[mcp_servers.github.tools.update_pull_request]
approval_mode = "approve"
[mcp_servers.github.tools.update_pull_request_branch]
approval_mode = "approve"

[mcp_servers.notion-runlayer]
url = "https://dbt.runlayer.com/api/v1/proxy/24736211-1060-47e7-897e-fdf5a531a3d5/mcp"

[mcp_servers.slack]
url = "https://dbt.runlayer.com/api/v1/proxy/dcf3b868-a852-4758-97aa-024fb941a173/mcp"

[mcp_servers.dbt]
url = "https://dbt.runlayer.com/api/v1/proxy/404ba041-4eb4-4e29-a474-ae38e7899ac9/mcp"

[mcp_servers.grep]
url = "https://dbt.runlayer.com/api/v1/proxy/2af56970-3fbd-4f0b-9cd7-562e921c2c99/mcp"

[mcp_servers.salesforce]
url = "https://dbt.runlayer.com/api/v1/proxy/70b141cc-940c-4190-8da5-f9cd50d34923/mcp"

[mcp_servers.runlayer-docs]
url = "https://dbt.runlayer.com/api/v1/proxy/68a80158-1c82-4a97-b1aa-509703ad4b94/mcp"

[mcp_servers.google_sheets]
url = "https://dbt.runlayer.com/api/v1/proxy/ab3aadc4-d6ac-4d92-85d6-cfba5eafc0e1/mcp"

[mcp_servers.serena]
command = "serena"
args = [
    "start-mcp-server",
    "--context=codex",
    "--project-from-cwd",
]
startup_timeout_sec = 60

[mcp_servers.community-slack]
command = "/Users/dataders/Developer/dotfiles/mcp/community-slack/run.sh"
args = []

[mcp_servers.parallel-search]
command = "/Users/dataders/Developer/dotfiles/mcp/parallel-search/run.sh"
args = []

[mcp_servers.strudel]
command = "strudel-mcp"
```

- [ ] **Step 2: Verify the TOML parses**

Run:
```bash
cd /Users/dataders/Developer/dotfiles
uv run python3 -c "import tomllib,sys; d=tomllib.load(open('wizard/config.toml','rb')); s=sorted(d.get('mcp_servers',{}).keys()); print(len(s),'servers:', s)"
```
Expected: prints `12 servers: [...]` (github, notion-runlayer, slack, dbt, grep, salesforce, runlayer-docs, google_sheets, serena, community-slack, parallel-search, strudel); no exception. Confirm `google-sheets` is **absent** and `model` is still present.

- [ ] **Step 3: Commit**

```bash
git add wizard/config.toml
git commit -m "wizard: mirror Codex MCP servers into config for cross-agent overlap"
```

---

## Task 5: Apply symlinks and verify Wizard sees the config

**Files:** none modified (filesystem symlinks only).

- [ ] **Step 1: Remove the pre-existing live regular files so `links.sh` can symlink them**

`links.sh`'s `safe_remove_existing_skill_dir` guard **refuses to overwrite a non-symlink target** unless it sits under `.codex/skills/`/`.claude/skills/`. Four of our targets already exist as regular files and would otherwise make `apply` print `FAIL` and skip them: `config.toml`, `wizard_config.toml`, `providers.json`, and `rules/default.rules`. (`AGENTS.md` is new — no conflict.) Their content is already preserved: the three config files were copied byte-identically in Task 1, and the live `rules/default.rules` content was folded into `.codex/rules/default.rules` in Task 3.

First re-confirm the copies are intact, THEN delete the live files (plain `rm` of explicit paths — not `rm -rf`):

```bash
cd /Users/dataders/Developer/dotfiles
diff ~/.dbt/wizard/config.toml        wizard/config.toml        && \
diff ~/.dbt/wizard/wizard_config.toml wizard/wizard_config.toml && \
diff ~/.dbt/wizard/providers.json     wizard/providers.json     && echo "copies verified"
# only proceed if the line above printed "copies verified":
rm ~/.dbt/wizard/config.toml ~/.dbt/wizard/wizard_config.toml ~/.dbt/wizard/providers.json ~/.dbt/wizard/rules/default.rules
```
Expected: `copies verified`, then the four files removed. (Re-running `apply` later is safe without this step — once a target is a symlink, the guard passes and `ln -sfn` re-links cleanly.)

- [ ] **Step 2: Dry-run, then apply**

Run:
```bash
cd /Users/dataders/Developer/dotfiles
./links.sh dry-run 2>&1 | grep wizard
./links.sh apply 2>&1 | grep -E 'wizard|FAIL'
```
Expected: dry-run shows planned links; apply shows five `LINK ... -> ...` lines for the wizard targets and **no** `FAIL`.

- [ ] **Step 3: Verify the symlinks resolve to the tracked sources**

Run:
```bash
for f in config.toml wizard_config.toml providers.json rules/default.rules AGENTS.md; do
  printf '%s -> ' "$f"; readlink ~/.dbt/wizard/$f
done
./links.sh check 2>&1 | grep -E 'wizard|FAIL'
```
Expected: `config.toml`/`wizard_config.toml`/`providers.json` point into `dotfiles/wizard/`; `rules/default.rules` → `dotfiles/.codex/rules/default.rules`; `AGENTS.md` → `dotfiles/AGENTS.md`. `check` prints `OK` for each wizard target, **no** `FAIL`.

- [ ] **Step 4: Confirm critical dbt symlinks are untouched**

Run:
```bash
for f in profiles.yml dbt_cloud.yml mcp.yml keyfile.json .user.yml; do
  printf '%s -> ' "$f"; readlink ~/.dbt/$f
done
```
Expected: all still point into `dotfiles_env/.dbt/` (unchanged).

- [ ] **Step 5: Verify Wizard loads everything**

Run:
```bash
wizard doctor 2>&1 | grep -iE 'config.toml|parse|MCP servers|AGENTS|rules|state'
```
Expected: `config.toml parse ok`, `MCP servers 12` (or similar non-zero), state healthy. No parse errors.

- [ ] **Step 6: Confirm git sees no leaked state**

Run:
```bash
cd /Users/dataders/Developer/dotfiles
git status --short | grep -E '\.dbt/|auth\.json' || echo "clean: no .dbt state tracked"
```
Expected: `clean: no .dbt state tracked` (the `.dbt/` symlinks live in the gitignored tree).

---

## Task 6: Lock the new links into the test suite

**Files:**
- Modify: `tests/test_links.py`

- [ ] **Step 1: Add manifest assertions for the new wizard links**

In `test_manifest_contains_core_private_and_workspace_links`, add assertions mirroring the existing style:

```python
self.assertIn(
    "repo:wizard/config.toml\thome:.dbt/wizard/config.toml",
    manifest,
)
self.assertIn(
    "repo:AGENTS.md\thome:.dbt/wizard/AGENTS.md",
    manifest,
)
self.assertIn(
    "repo:.codex/rules/default.rules\thome:.dbt/wizard/rules/default.rules",
    manifest,
)
```

- [ ] **Step 2: Run the test suite**

Run:
```bash
cd /Users/dataders/Developer/dotfiles
uv run python3 -m unittest tests.test_links -v
```
Expected: all tests pass (the apply/check/unlink test exercises the temp-home manifest run, which now includes the wizard rows).

- [ ] **Step 3: Commit**

```bash
git add tests/test_links.py
git commit -m "tests: assert wizard symlink manifest entries"
```

---

## Task 7: Final verification

- [ ] **Step 1: Full link health check**

Run:
```bash
cd /Users/dataders/Developer/dotfiles
./links.sh check 2>&1 | grep -c FAIL   # expect: 0
./links.sh doctor 2>&1 | grep -iE 'FAIL|missing private' || echo "doctor clean"
```
Expected: `0` failures; `doctor clean` (or only pre-existing unrelated warnings).

- [ ] **Step 2: Confirm only intended files are committed**

Run:
```bash
git log --oneline main..HEAD
git diff --stat main..HEAD
```
Expected: commits touch only `wizard/*`, `links.tsv`, `.codex/rules/default.rules`, `tests/test_links.py`, and the `docs/superpowers/` spec+plan. No unrelated working-tree drift (`.claude.json`, `.serena/...`, etc.) was swept in.

- [ ] **Step 3: Re-run Wizard, Codex sanity**

Run:
```bash
wizard doctor 2>&1 | grep -iE 'config|mcp|auth|state' | head
```
Expected: healthy; auth still works (auth.json untouched, still gitignored).

---

## Notes / out of scope

- RTK hook wiring for Wizard, fixing the `@RTK.md` import in `AGENTS.md`, and unifying MCP across the JSON/TOML format boundary are explicitly out of scope (see spec).
- `skills/.system/` is install-managed and intentionally left untracked.
- Cleaning `.codex/rules/default.rules` means some previously auto-approved one-off commands will prompt again — intended.

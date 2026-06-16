# Tiered env-var decomposition — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Break the monolithic `~/Developer/dotfiles_env/secrets.zsh` into three tiers (global / per-platform warehouse / per-repo) loaded by distinct mechanisms, eliminating cross-repo env-var collisions.

**Architecture:** Global tooling creds stay in a slimmed `secrets.zsh` sourced by `.zshrc`. Everything else moves to `~/Developer/dotfiles_env/projects/*.envrc`, loaded on demand by the existing `source_dotfiles_env` direnv helper. No symlinks. Structured so a later 1Password swap is one-file-at-a-time.

**Tech Stack:** zsh, direnv (stdlib `source_env_if_exists` / `watch_file`), git. No language runtime.

**Spec:** `docs/superpowers/specs/2026-06-16-env-var-tiered-decomposition-design.md`

---

## Critical execution rules

1. **Never copy a real secret value into any file under the public `dotfiles` repo** (this plan, the spec, anything tracked there). Real values move only between `secrets.zsh` and `projects/*.envrc`, both inside the **private** `dotfiles_env` repo.
2. **All edits to profile/secret files happen in `~/Developer/dotfiles_env`** (private repo), not in this `dotfiles` worktree. This plan doc lives in `dotfiles`; the things it creates live in `dotfiles_env`.
3. **`direnv allow`, moving the BigQuery keyfile, and any rotation are performed by the user** (they touch the live environment / require judgment). Steps that need this are marked **[USER]**.
4. Work the tiers in order; keep `secrets.zsh` intact until each destination is verified, then remove the migrated block. This keeps a working environment at every commit.
5. Commit in the `dotfiles_env` repo after each task (it is a git repo; verify with `git -C ~/Developer/dotfiles_env status`).

## File structure (created in `~/Developer/dotfiles_env/`)

| File | Responsibility |
|---|---|
| `projects/snowflake.envrc` | Snowflake adapter-testing creds |
| `projects/bigquery.envrc` | BigQuery adapter-testing creds + keyfile path |
| `projects/redshift.envrc` | Redshift adapter-testing creds |
| `projects/synapse.envrc` | Synapse adapter-testing creds |
| `projects/databricks.envrc` | Databricks adapter-testing creds |
| `projects/motherduck.envrc` | MotherDuck token |
| `projects/all-warehouses.envrc` | Aggregator: sources every per-platform profile |
| `projects/cannon.envrc` | Cannon auctions app (Cannon + Supabase + Vite + eBay + Google) |
| `projects/polaris.envrc` | Polaris/Iceberg catalog creds |
| `projects/clickhouse.envrc` | ClickHouse Cloud API creds |
| `projects/shadowtraffic.envrc` | ShadowTraffic trial license |
| `secrets.zsh` (modify) | Slimmed to global tier only |
| `bigquery-service-key.json` (relocate) | Moved out of public `dotfiles` into here |

Each profile file's body, for Phase 1, is plain `export NAME="value"` lines — values **moved** from the matching `secrets.zsh` lines.

---

## Task 0: Audit `secrets.zsh` into a mapping table

**Files:**
- Read: `~/Developer/dotfiles_env/secrets.zsh`
- Create (scratch, NOT committed to public repo): `$CLAUDE_JOB_DIR/tmp/secrets-mapping.tsv`

- [ ] **Step 1: Enumerate every exported/commented var**

Run (active exports): `grep -cE '^[[:space:]]*export ' ~/Developer/dotfiles_env/secrets.zsh` → Expected: ~93.
Run (commented/dead): `grep -cE '^[[:space:]]*#[[:space:]]*export ' ~/Developer/dotfiles_env/secrets.zsh` → Expected: a handful (RETIRED candidates).
The audit must cover both sets. (Note: the spec's "~167-line" figure counts all lines; ~93 is the active-export count — not a contradiction.)

- [ ] **Step 2: Build the mapping table** — one row per var: `LINE  VAR  DESTINATION`, where DESTINATION ∈ {global, snowflake, bigquery, redshift, synapse, databricks, motherduck, cannon, polaris, clickhouse, shadowtraffic, RETIRED}.

Reference assignment (from spec inventory):
- **global:** `WIZARD_INTERNAL`, `ANTHROPIC_API_KEY`, `PARALLEL_API_KEY`, `GITHUB_TOKEN`, `GITHUB_PAT_MCP`, `TELEPORT_PROXY`, `TELEPORT_AUTH`, `COMMUNITY_SLACK_BOT_TOKEN`
- **snowflake:** `SNOWFLAKE_*`, `DBT_ENV_SECRET_SNOWFLAKE_PASS`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_DEV_*`
- **bigquery:** `BIGQUERY_*` (incl. `BIGQUERY_KEYFILE_JSON`, `BIGQUERY_SERVICE_KEY_PATH`, `*_TEST_*`, `DATAPROC*`, `GCS_BUCKET`)
- **redshift:** `REDSHIFT_*`, `DBT_ENV_SECRET_REDSHIFT_PASS`, `REDSHIFT_TEST_*`
- **synapse:** `SYNAPSE_*`, `DBT_ENV_SECRET_SYNAPSE_CLIENT_SECRET`
- **databricks:** `DBT_DATABRICKS_*`, `DATABRICKS_USER_SCHEMA`, `DBRX_TOKEN`
- **motherduck:** `MOTHERDUCK_TOKEN`
- **cannon:** `CANNON_*`, `SUPABASE_*`, `SUPABASE_POSTGRES_URL`, `VITE_*`, `EBAY_*`, `EXTERNAL_GOOGLE_*`
- **polaris:** active `POLARIS_*`
- **clickhouse:** `CLICKHOUSE_CLOUD_*`
- **shadowtraffic:** `LICENSE_*`
- **RETIRED (commented/dead):** old commented `POLARIS_*` block, old commented `GITHUB_TOKEN` lines, commented `DBT_CLOUD_*` / `DBT_HOST` / `DBT_PATH` block

- [ ] **Step 3: Verify completeness**

Every var from Step 1 has exactly one DESTINATION. Count rows == count from Step 1.
Expected: zero unassigned vars. If any var is unclear, STOP and ask the user.

- [ ] **Step 4: No commit** (scratch file only; it may contain secret names but not in a tracked location).

---

## Task 1: Scaffold `projects/` and prove the direnv mechanism

Prove the loader works with a throwaway var **before** moving real secrets.

**Files:**
- Create: `~/Developer/dotfiles_env/projects/` (dir)
- Create (temp): `~/Developer/dotfiles_env/projects/_smoketest.envrc`
- Create (temp): a test repo `.envrc`

- [ ] **Step 1: Create the directory**

Run: `mkdir -p ~/Developer/dotfiles_env/projects`

- [ ] **Step 2: Write a smoke-test profile**

`~/Developer/dotfiles_env/projects/_smoketest.envrc`:
```sh
export SMOKETEST_VAR="hello-from-dotfiles-env"
```

- [ ] **Step 3: [USER] Wire a scratch repo and allow direnv**

```bash
mkdir -p ~/tmp/direnv-smoke && cd ~/tmp/direnv-smoke
echo 'source_dotfiles_env _smoketest' > .envrc
direnv allow
```

- [ ] **Step 4: Verify it loads in-dir and is absent outside (the core mechanism)**

Run (in `~/tmp/direnv-smoke`): `echo $SMOKETEST_VAR` → Expected: `hello-from-dotfiles-env`
Run (in `~`): `cd ~ && echo "[$SMOKETEST_VAR]"` → Expected: `[]` (empty)

- [ ] **Step 5: Tear down the smoke test**

```bash
rm -rf ~/tmp/direnv-smoke
rm ~/Developer/dotfiles_env/projects/_smoketest.envrc
```

- [ ] **Step 6: Commit the empty scaffold**

```bash
git -C ~/Developer/dotfiles_env add projects/.gitkeep 2>/dev/null || (touch ~/Developer/dotfiles_env/projects/.gitkeep && git -C ~/Developer/dotfiles_env add projects/.gitkeep)
git -C ~/Developer/dotfiles_env commit -m "feat: scaffold projects/ dir for direnv profiles"
```

---

## Task 2: Per-platform warehouse profiles

Repeat this sub-pattern once per platform: **snowflake, bigquery, redshift, synapse, databricks, motherduck**. Do them one at a time, each its own commit.

**Files (per platform `<p>`):**
- Create: `~/Developer/dotfiles_env/projects/<p>.envrc`
- Modify: `~/Developer/dotfiles_env/secrets.zsh` (remove the migrated block)

- [ ] **Step 1: Create `projects/<p>.envrc`** — move (cut) the platform's `export` lines from `secrets.zsh` into it verbatim (values and all). Preserve derived-var ordering (e.g. `SNOWFLAKE_DEV_*` reference `SNOWFLAKE_*`, so they must come after).

Example shape (snowflake — **move real values, do not type them from here**):
```sh
# Snowflake adapter integration-testing creds
export SNOWFLAKE_ACCOUNT=...
export SNOWFLAKE_USER=...
# ... (all SNOWFLAKE_*, DBT_ENV_SECRET_SNOWFLAKE_PASS, SNOWFLAKE_PASSWORD)
# derived (must come after the base vars):
export SNOWFLAKE_DEV_ACCOUNT=$SNOWFLAKE_ACCOUNT
# ...
```

- [ ] **Step 2: Remove the migrated lines from `secrets.zsh`** so they are not double-defined.

- [ ] **Step 3: [USER] Allow direnv in that platform's repo** (e.g. `~/Developer/dbt-snowflake`): add `.envrc` containing `source_dotfiles_env <p>`, then `direnv allow`. (Repo wiring is finalized in Task 6; here just enough to verify.)

- [ ] **Step 4: Verify present-in-repo, absent-in-home (use a FRESH shell)**

direnv cannot unset a var a parent shell already exported, so the absent-in-home
check **must** run in a new shell — otherwise a pre-existing shell that sourced
the un-slimmed `secrets.zsh` makes it falsely fail.

Run (in the repo): `env | grep -c '^SNOWFLAKE_'` → Expected: > 0
Run (fresh shell): `zsh -ic 'cd ~ && env | grep -c "^SNOWFLAKE_"'` → Expected: `0`
(Until Task 6 slims `secrets.zsh`, the home value may still be present in old
shells; the fresh-shell check is authoritative.)

- [ ] **Step 5: Verify nothing was dropped** — every var the mapping assigned to `<p>` now appears in `projects/<p>.envrc` and no longer in `secrets.zsh`. Anchor to **active exports** so comments don't cause false matches:

Run: `grep -cE '^[[:space:]]*export .*SNOWFLAKE' ~/Developer/dotfiles_env/secrets.zsh` → Expected: `0`
Run: `grep -cE '^[[:space:]]*export .*DBT_ENV_SECRET_SNOWFLAKE' ~/Developer/dotfiles_env/secrets.zsh` → Expected: `0`

- [ ] **Step 6: Commit (in `dotfiles_env`)**

```bash
git -C ~/Developer/dotfiles_env add -A
git -C ~/Developer/dotfiles_env commit -m "feat: move <p> creds to projects/<p>.envrc"
```

Repeat Steps 1–6 for each remaining platform.

---

## Task 3: `all-warehouses` aggregator

**Files:**
- Create: `~/Developer/dotfiles_env/projects/all-warehouses.envrc`

- [ ] **Step 1: Write the aggregator**

`~/Developer/dotfiles_env/projects/all-warehouses.envrc`:
```sh
# Compose every per-platform warehouse profile on demand.
for _p in snowflake bigquery redshift synapse databricks motherduck; do
  source_env_if_exists "$HOME/Developer/dotfiles_env/projects/${_p}.envrc"
done
unset _p
```

- [ ] **Step 2: [USER] Verify composition in a scratch dir**

```bash
mkdir -p ~/tmp/wh && cd ~/tmp/wh
echo 'source_dotfiles_env all-warehouses' > .envrc && direnv allow
env | grep -E '^(SNOWFLAKE_ACCOUNT|BIGQUERY_PROJECT|REDSHIFT_HOST|MOTHERDUCK_TOKEN)='
```
Expected: all four lines present.

- [ ] **Step 3: Tear down** `rm -rf ~/tmp/wh`

- [ ] **Step 4: Commit**

```bash
git -C ~/Developer/dotfiles_env add projects/all-warehouses.envrc
git -C ~/Developer/dotfiles_env commit -m "feat: add all-warehouses aggregator profile"
```

---

## Task 4: Per-repo project profiles

Same sub-pattern as Task 2, for: **cannon, polaris, clickhouse, shadowtraffic**.

- [ ] **Step 1:** Create `projects/<name>.envrc`; move the matching `export` lines out of `secrets.zsh`. For `polaris`, move only the **active** block; the commented "old" block is RETIRED (delete it, do not migrate). For `cannon`, the audit (Task 0) must confirm **all** `VITE_*` vars belong to cannon — the broad glob over-assigns if any `VITE_` var belongs elsewhere.
- [ ] **Step 2:** Remove migrated lines from `secrets.zsh`.
- [ ] **Step 3 [USER]:** Wire/verify in the relevant repo. Known: clickhouse → `~/Developer/dbt-fusion-clickhouse-demo`. For `cannon`, `polaris`, `shadowtraffic` the consuming repo path is **[USER]-supplied** (the executor cannot infer it). Use the fresh-shell present-in-repo / absent-in-home check from Task 2 Step 4.
- [ ] **Step 4:** Commit per profile in `dotfiles_env`.

---

## Task 5: Relocate the BigQuery keyfile out of the public repo **[USER]**

`~/bigquery-service-key.json` currently symlinks into the **public** `dotfiles` repo. Move the real file into `dotfiles_env`.

**Files:**
- Move: public `dotfiles/...bigquery-service-key.json` → `~/Developer/dotfiles_env/bigquery-service-key.json`
- Modify: `~/.gitignore_global` / `links.tsv` as needed; repoint the `~/bigquery-service-key.json` symlink

- [ ] **Step 1: Locate the real file**

Run: `ls -lL ~/bigquery-service-key.json; readlink ~/bigquery-service-key.json`
Expected: resolves into `~/Developer/dotfiles/...`

- [ ] **Step 2: Move the real file into `dotfiles_env`** and repoint the home symlink to the new private location (update `links.tsv` if the symlink is managed there).

- [ ] **Step 3: Remove the keyfile from the public `dotfiles` repo** (and its git history is out of scope — flag for the rotation follow-up if the key was ever committed).

- [ ] **Step 4: Verify** `BIGQUERY_SERVICE_KEY_PATH` still resolves to a readable file and the path is no longer inside the public repo.

Run: `cat $(readlink -f ~/bigquery-service-key.json) | head -c 1 >/dev/null && echo OK`

- [ ] **Step 5: Commit** the relocation in `dotfiles_env` and the removal in the `dotfiles` worktree (separate commits, separate repos).

---

## Task 6: Slim `secrets.zsh` and wire repo `.envrc` hooks

**Files:**
- Modify: `~/Developer/dotfiles_env/secrets.zsh` (should now contain only the global tier)
- Create/modify: `.envrc` in each consuming repo

- [ ] **Step 1: Confirm `secrets.zsh` holds only the global tier**

Run: `grep -cE '^[[:space:]]*export ' ~/Developer/dotfiles_env/secrets.zsh` → Expected: the count of `global` rows in the Task 0 audit table (≈8 names; confirm against the table rather than hard-coding, in case any global var spans multiple `export` lines).
Run: `grep -E 'SNOWFLAKE|BIGQUERY|REDSHIFT|SYNAPSE|DATABRICKS|MOTHERDUCK|CANNON|SUPABASE|POLARIS|CLICKHOUSE|LICENSE|EBAY' ~/Developer/dotfiles_env/secrets.zsh` → Expected: no output (including comments — the RETIRED blocks are deleted, not left behind).

- [ ] **Step 2: [USER] Add `.envrc` to each consuming repo** using `source_dotfiles_env <name>` (or `all-warehouses`). Known consumers: `dbt-fusion-clickhouse-demo` → `clickhouse`; adapter repos → their platform; multi-adapter repos → `all-warehouses`. `direnv allow` each.

- [ ] **Step 3: Verify the global tier survives a fresh shell (without printing values)**

Run: `zsh -ic '[[ -n $GITHUB_TOKEN && -n $ANTHROPIC_API_KEY && -n $GITHUB_PAT_MCP && -n $PARALLEL_API_KEY && -n $TELEPORT_PROXY && -n $COMMUNITY_SLACK_BOT_TOKEN ]] && echo OK || echo MISSING'`
Expected: `OK`. (Tests non-emptiness; never echoes the value. If you want a count instead: `zsh -ic 'echo "${#GITHUB_TOKEN} ${#ANTHROPIC_API_KEY}"'` → two non-zero numbers.)

- [ ] **Step 4: Verify the collision is gone (the headline outcome) — fresh shells**

Run (fresh shell, home): `zsh -ic 'cd ~ && env | grep -c "^SNOWFLAKE_"'` → Expected: `0`
Run (in the snowflake repo): `env | grep -c '^SNOWFLAKE_'` → Expected: > 0
(The home check uses a fresh `zsh -ic` because direnv cannot unset vars a long-lived parent shell exported before the slim.)

- [ ] **Step 5: Commit** the slimmed `secrets.zsh` in `dotfiles_env`.

---

## Task 7: `.gitignore_global` convention for `.envrc`

**Files:**
- Modify: `~/.gitignore_global` (tracked in public `dotfiles`)

- [ ] **Step 1: Add `.envrc` to `~/.gitignore_global`** (it is not there today) so OSS repos never stage the personal hook.

- [ ] **Step 2: Document the personal-repo override** — repos where committing `.envrc` is desired add `!.envrc` to their local `.gitignore`, or use `git add -f .envrc`. Pick one convention; note it in the file as a comment.

- [ ] **Step 3: Verify**

Run (in an OSS repo with a fresh `.envrc`): `git check-ignore -v .envrc` → Expected: matches the global ignore rule.

- [ ] **Step 4: Commit** in the `dotfiles` worktree.

---

## Done-when

- `secrets.zsh` contains only the 8 global vars; a fresh `~` shell has them and **no** warehouse/project vars.
- Each consuming repo loads exactly its tier via `source_dotfiles_env`; `env | grep` proves present-in-repo / absent-in-home.
- `all-warehouses` composes all six platforms.
- BigQuery keyfile lives in `dotfiles_env`, not the public repo.
- `.envrc` is globally ignored with a documented personal-repo override.
- The audit table accounts for every original var (assigned or RETIRED).

## Out of scope (follow-up)

- Credential rotation (separate manual checklist in the spec).
- Phase 2: 1Password `op` + `from_op` integration.

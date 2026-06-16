# Tiered secrets decomposition (direnv-first, 1Password-ready)

- **Date:** 2026-06-16
- **Status:** Design approved, pending spec review
- **Author:** Anders Swanson (with Claude)

## Problem

`~/Developer/dotfiles_env/secrets.zsh` is a single ~167-line file sourced into
**every** shell via `.zshrc`. This causes four concrete problems:

1. **Variable collisions** — globally-set vars (`SNOWFLAKE_*`, `DBT_*`,
   `GITHUB_TOKEN`) bleed into repos that need different values, producing
   wrong-account / wrong-creds bugs.
2. **Everything loaded everywhere** — every shell holds all secrets regardless
   of relevance: bloat, leak surface, hard to reason about what is set.
3. **Hard to maintain** — one large file, no clear ownership of which var
   belongs to which project.
4. **Stale / rotation risk** — a mix of live and dead creds with no lifecycle.

This design fixes #1–#3 mechanically. #4 (rotation) is an explicit follow-up
checklist, not in scope (see "Out of scope").

## Goals

- Eliminate cross-repo env-var collisions by scoping secrets to where they are
  used.
- Keep only genuinely cross-cutting tooling creds loaded in every shell.
- Make the structure **forward-compatible with a later 1Password migration**
  so Phase 2 is a localized change, not a rewrite.
- No symlinking of secret files into repos.

## Non-goals / Out of scope

- **Credential rotation.** High-value live creds (Anthropic key, both GitHub
  PATs, warehouse passwords, MotherDuck/Databricks tokens) *should* be rotated,
  but that is a manual follow-up checklist, not part of this project's
  definition of done.
- **1Password integration.** Designed-for but deferred to Phase 2 (separate
  spec/plan).
- **Symlink-based distribution.** Considered and rejected (see Alternatives).

## Existing substrate (already present, currently unused)

`~/.config/direnv/direnvrc` already defines:

```sh
source_dotfiles_env() {
  local name="${1:-$(basename "$PWD")}"
  source_env_if_exists "$HOME/Developer/dotfiles_env/projects/${name}.envrc"
}
```

- The `projects/` directory does **not** exist yet.
- Nothing currently calls the helper.
- The two existing `.envrc` files (`dbt_aws_cloud_cost`,
  `dbt-fusion-clickhouse-demo`) use plain `.env`/`dotenv`, not the helper.

This design activates the helper rather than inventing new machinery.

## Architecture: three tiers

| Tier | Lives in | Loaded by | Present when |
|---|---|---|---|
| **Global tooling** | `dotfiles_env/secrets.zsh` (slimmed) | `.zshrc` source loop (unchanged) | Every shell |
| **Shared profile** | `dotfiles_env/projects/<profile>.envrc` | repo `.envrc` → `source_dotfiles_env <profile>` | Repos that opt in |
| **Per-repo** | `dotfiles_env/projects/<repo>.envrc` | repo `.envrc` → `source_dotfiles_env` (defaults to dir name) | Only that repo's dir |

Secrets always live in `dotfiles_env`. A repo's `.envrc` is a non-secret hook —
it never contains secret values. No symlinks.

### Where everything lives (repo boundaries)
- **`dotfiles_env` (private) — all secret values:** the slimmed `secrets.zsh`
  (global tier), every `projects/*.envrc` (warehouse + per-repo profiles), and
  the `bigquery-service-key.json` keyfile (relocated here from the public repo
  during migration).
- **`dotfiles` (public) — non-secret infrastructure only:** the
  `source_dotfiles_env` helper (`.config/direnv/direnvrc`, already tracked) and
  this spec. No credential values.
- **Individual project repos:** only a non-secret `.envrc` hook
  (`source_dotfiles_env <name>`), gitignored in OSS repos.

## Inventory mapping

### Stays global (`secrets.zsh`, slimmed to only these)
- `WIZARD_INTERNAL`
- `ANTHROPIC_API_KEY`
- `PARALLEL_API_KEY`
- `GITHUB_TOKEN`, `GITHUB_PAT_MCP`
- `TELEPORT_PROXY`, `TELEPORT_AUTH`
- `COMMUNITY_SLACK_BOT_TOKEN`

Rationale: these back always-on tooling — the `claude`/`gh` CLIs and MCP
servers launched at shell/MCP startup. They are not repo-scoped.

### Shared profiles — warehouse/adapter creds (per-platform)
Split per platform so a repo loads only the warehouse it tests (this is the
primary fix for the `SNOWFLAKE_*` collision):

- `projects/snowflake.envrc` — `SNOWFLAKE_*`, `DBT_ENV_SECRET_SNOWFLAKE_PASS`,
  `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_DEV_*`
- `projects/bigquery.envrc` — `BIGQUERY_*` (incl. `BIGQUERY_KEYFILE_JSON`,
  `BIGQUERY_SERVICE_KEY_PATH`, `*_TEST_*`, `DATAPROC*`, `GCS_BUCKET`).
  **Note:** `BIGQUERY_SERVICE_KEY_PATH` is a *path* var, not a secret value —
  it points at `${HOME}/bigquery-service-key.json`, which must exist
  independent of which shell loads the var. That keyfile is currently a symlink
  whose target resolves into the **public** `dotfiles` repo; the migration must
  confirm/relocate the keyfile so a service-account JSON is not stored in a
  public repo. (Pre-existing condition, surfaced here because scoping the var
  makes file-availability newly relevant.)
- `projects/redshift.envrc` — `REDSHIFT_*`, `DBT_ENV_SECRET_REDSHIFT_PASS`,
  `REDSHIFT_TEST_*`
- `projects/synapse.envrc` — `SYNAPSE_*`, `DBT_ENV_SECRET_SYNAPSE_CLIENT_SECRET`
- `projects/databricks.envrc` — `DBT_DATABRICKS_*`, `DATABRICKS_USER_SCHEMA`,
  `DBRX_TOKEN`
- `projects/motherduck.envrc` — `MOTHERDUCK_TOKEN`

### Aggregator — "all warehouses when needed"
`projects/all-warehouses.envrc` composes the per-platform files (single source
of truth stays in each platform file):

```sh
# projects/all-warehouses.envrc
for _p in snowflake bigquery redshift synapse databricks motherduck; do
  source_env_if_exists "$HOME/Developer/dotfiles_env/projects/${_p}.envrc"
done
unset _p
```

A repo that needs everything does `source_dotfiles_env all-warehouses`.

### Per-repo / per-project profiles
Every non-global, non-warehouse var maps to a project profile (nothing in
`secrets.zsh` is dropped — see "Full inventory accounting" below):

- `projects/cannon.envrc` — `CANNON_*`, `SUPABASE_*`, `SUPABASE_POSTGRES_URL`,
  `VITE_SUPABASE_*`, `VITE_POSTHOG_KEY`, `EBAY_*`, `EXTERNAL_GOOGLE_*`
  (one app: Cannon auctions + Supabase backend + Vite frontend)
- `projects/polaris.envrc` — `POLARIS_*`
- `projects/clickhouse.envrc` — `CLICKHOUSE_CLOUD_*` (consumed by the existing
  `dbt-fusion-clickhouse-demo` repo)
- `projects/shadowtraffic.envrc` — `LICENSE_*` (ShadowTraffic trial license)

### Full inventory accounting
To honor "slim `secrets.zsh` to the global tier only," every currently-exported
var must land in exactly one destination. The migration's first step is a
line-by-line audit of `secrets.zsh` producing a mapping table; any var that is
**dead/stale** (e.g. commented-out `DBT_CLOUD_*`, `DBT_HOST`, old `POLARIS_*`)
is explicitly listed as **retired** rather than silently dropped. No var may be
left unassigned.

## Repo `.envrc` conventions

- **Personal repos:** the `.envrc` (`source_dotfiles_env <name>`) is non-secret
  and may be committed.
- **dbt OSS repos** (e.g. dbt-snowflake): do **not** commit a personal helper
  call. Keep `.envrc` local and ignored — add `.envrc` to `~/.gitignore_global`
  (it is **not** there today; the migration adds it) so it is never staged in
  any repo. Secret values are never in the repo regardless.
- **Tension to resolve:** a global `.envrc` ignore also un-stages `.envrc` in
  the personal repos where committing it is desired. Those repos must override
  with a negation pattern (`!.envrc`) in their local `.gitignore`, or use
  `git add -f .envrc`. The migration plan picks one convention and documents it.
  (`direnv allow` writes only to direnv's own state dir, never the repo, so it
  is unaffected either way.)

Example repo `.envrc`:

```sh
# dbt-snowflake repo
source_dotfiles_env snowflake
```

```sh
# a repo that exercises multiple adapters
source_dotfiles_env all-warehouses
```

## Phase-2 seam (1Password forward-compatibility)

The only thing Phase 2 changes is the **body** of each
`projects/<name>.envrc`:

```sh
# Phase 1
export SNOWFLAKE_PASSWORD='<literal-value>'

# Phase 2 (later spike)
from_op SNOWFLAKE_PASSWORD=op://Vault/snowflake-ci/password
```

The repo `.envrc`, the `direnvrc` `source_dotfiles_env` helper, and the tier
structure are unchanged. Phase 1 is the substrate Phase 2 slots into, not
throwaway work.

## Migration plan (high level)

1. **Audit `secrets.zsh` line by line** into a mapping table (var → tier/file,
   or "retired"). No var left unassigned.
2. Create `dotfiles_env/projects/`.
3. Author the per-platform, aggregator, per-repo `.envrc` files; move vars out
   of `secrets.zsh` per the mapping table.
4. Slim `secrets.zsh` to the global tier only.
5. Confirm/relocate `bigquery-service-key.json` out of the public `dotfiles`
   repo (see BigQuery note).
6. Add per-repo `.envrc` hooks; `direnv allow` each repo.
7. Add `.envrc` to `~/.gitignore_global`; pick and document the personal-repo
   override convention (`!.envrc` vs `git add -f`).

## Verification

- **Collision fix proven:** `env | grep SNOWFLAKE` lists the vars **inside** the
  Snowflake repo and is **empty** in a plain `~` shell.
- Each migrated repo: `direnv allow`, then confirm its expected vars are present
  and unrelated vars are absent.
- Global tier: a fresh `~` shell still has `GITHUB_TOKEN`, `ANTHROPIC_API_KEY`,
  etc.
- **Reload guarantee:** editing a `projects/*.envrc` file triggers a direnv
  reload in repos that source it. The stdlib chain `source_dotfiles_env` →
  `source_env_if_exists` → `source_env` calls `watch_file` on each sourced path
  (and the aggregator's nested `source_env_if_exists` calls watch each platform
  file), so direnv watches files outside the repo too — no manual `direnv
  reload` needed after editing creds.

## Alternatives considered

- **Symlink `.env` files from `dotfiles_env` into each repo.** Rejected:
  risk of accidentally committing the secret (git follows the link target if not
  ignored), link points outside the repo (footgun on archive/worktree). The
  `source_dotfiles_env` helper achieves the same separation with no secret file
  in the repo at all.
- **One `adapter-testing.envrc` blob.** Rejected as the default: reintroduces
  cross-warehouse bloat in any repo that loads it. The aggregator
  (`all-warehouses.envrc`) gives the same convenience on demand without the
  always-on bloat.
- **1Password / SOPS now.** Deferred to Phase 2 per phased decision; this design
  is built to make that migration a localized change.

## Follow-up checklist (out of scope, do manually)

- [ ] Rotate `ANTHROPIC_API_KEY`
- [ ] Rotate both GitHub PATs (`GITHUB_TOKEN`, the MCP PAT)
- [ ] Rotate warehouse passwords (Snowflake, Redshift, Synapse secret)
- [ ] Rotate `MOTHERDUCK_TOKEN`, `DBT_DATABRICKS_TOKEN`, `DBRX_TOKEN`
- [ ] Phase 2: spike 1Password `op` + direnv (`from_op`) integration

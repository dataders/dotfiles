# dbt Wizard config consolidation & cross-agent overlap

**Date:** 2026-06-01
**Status:** Approved (pending spec review + user sign-off)

## Problem

`wizard` (dbt Wizard, a fork of the OpenAI Codex CLI built by dbt Labs) keeps its
settings under `DBT_WIZARD_HOME = ~/.dbt/wizard/`. Because `~/.dbt` is a symlink to
`dotfiles/.dbt` and **all of `.dbt/` is gitignored**, none of Wizard's settings are
source-controlled. Meanwhile the Claude Code and Codex configs already share a
canonical instructions file (`dotfiles/AGENTS.md`) and Codex has a curated, tracked
command-approval rules file. Wizard duplicates none of this: it has no global
instructions, an untracked 3-line rules file, untracked model config, and zero MCP
servers.

Goal: source-control Wizard's non-secret settings and make them overlap with the
Claude/Codex configs as much as possible, using the existing dotfiles symlink
convention rather than ad hoc copies.

## Background facts (verified)

- `wizard` binary: `~/.local/bin/wizard` (alias of `dbt-wizard`), v0.1.1-beta.51.
  Self-describes as "forked from OpenAI's open-source Codex CLI, so it inherits many
  CLI mechanics including flags, config schema, MCP server config, and `--config`/`-c`
  overrides."
- Config paths (from `wizard doctor` and embedded docs):
  - Home config dir: `~/.dbt/wizard/`
  - Home config file: `~/.dbt/wizard/config.toml` (Codex-schema: model, MCP, sandbox,
    approval, profiles)
  - Wizard-managed per-project state: `~/.dbt/wizard/wizard_config.toml`
    (`[global]` + `[projects.*]`)
  - Rules dir: `~/.dbt/wizard/rules/` (`*.rules`, same `prefix_rule(...)` DSL as Codex)
  - Global instructions: `AGENTS.md` is supported (Codex `project_doc` mechanism;
    home-level doc read from `$DBT_WIZARD_HOME/AGENTS.md`).
- `~/.dbt` → `dotfiles/.dbt`; `.dbt/` is gitignored (`.gitignore:6`). The wizard files
  therefore physically live in the repo but are untracked.
- `providers.json` contains **no secrets** (verified: no `sk-`/`token`/`api_key`/`secret`).
- Precedent: the already-tracked `dotfiles/.codex/config.toml` mixes durable settings
  with machine state (project-trust lists, marketplace timestamps, hook hashes). So
  tracking Wizard's `config.toml` + `wizard_config.toml` as-is (state included) is
  consistent with how Codex is handled — no portable-vs-state split needed.

## Inventory & disposition of `~/.dbt/wizard/`

| Path | Size | Disposition |
|---|---|---|
| `config.toml` | 4 KB | **Track** (canonical in repo, symlink back) |
| `wizard_config.toml` | 4 KB | **Track** (canonical in repo, symlink back) |
| `providers.json` | 8 KB | **Track** (canonical in repo, symlink back) |
| `rules/default.rules` | 4 KB | **Track via shared file** (symlink to Codex rules) |
| `AGENTS.md` | — (new) | **Track via shared file** (symlink to `dotfiles/AGENTS.md`) |
| `auth.json` | 4 KB | **Never track** — secret |
| `provider-auth.json` | 8 KB | **Never track** — secret |
| `*.sqlite`, `*-wal`, `*-shm` | ~50 MB | Never track — state DBs |
| `log/`, `logs_*.sqlite` | ~40 MB | Never track — logs |
| `sessions/`, `litellm/`, `shell_snapshots/` | ~2 MB | Never track — runtime |
| `.tmp/`, `tmp/` | 52 MB | Never track — scratch |
| `history.jsonl`, `installation_id`, `version.json`, `.personality_migration` | small | Never track — machine/session state |
| `skills/.system/` | 144 KB | Never track — install-managed system skills (regenerated) |

The `.dbt/` gitignore stays intact; only the named sources under `dotfiles/wizard/`
(plus the two shared files) become tracked. This is safer than gitignore-negation,
which risks accidentally committing `auth.json`.

## Design

### Component 1 — canonical source dir `dotfiles/wizard/`

New tracked directory holding the real files:

```
dotfiles/wizard/config.toml
dotfiles/wizard/wizard_config.toml
dotfiles/wizard/providers.json
```

Migration: copy current `~/.dbt/wizard/{config.toml,wizard_config.toml,providers.json}`
content into `dotfiles/wizard/`, then let `links.sh` replace the originals with symlinks.

### Component 2 — `links.tsv` entries

Add (group `agents`, visibility `public`):

```
repo:wizard/config.toml          home:.dbt/wizard/config.toml          agents  public  Wizard general config (Codex schema)
repo:wizard/wizard_config.toml   home:.dbt/wizard/wizard_config.toml   agents  public  Wizard per-project state
repo:wizard/providers.json       home:.dbt/wizard/providers.json       agents  public  Wizard model provider catalog
repo:.codex/rules/default.rules  home:.dbt/wizard/rules/default.rules  agents  public  Shared Codex/Wizard command-approval rules
repo:AGENTS.md                   home:.dbt/wizard/AGENTS.md            agents  public  Shared global agent instructions
```

Resolution check: `home:.dbt/wizard/X` resolves via `~/.dbt`→`dotfiles/.dbt` to
`dotfiles/.dbt/wizard/X`, a symlink (inside the gitignored area) pointing at the tracked
source. Only the `repo:` sources are tracked.

### Component 3 — shared command-approval rules (Codex + Wizard)

1. Clean `dotfiles/.codex/rules/default.rules`: remove the ~40 auto-appended one-off
   `prefix_rule(...)` lines at the bottom (machine-specific worktree paths, `kill <PID>`,
   the multi-line `gh pr create` blob, duplicate single-line allows). Keep the curated
   durable block (the `forbidden` set + structured `allow` rules with justifications).
2. Fold in Wizard's allows so the shared file serves both tools:
   - `prefix_rule(pattern=["wizard"], decision="allow")`
   - `prefix_rule(pattern=["pkill","-f","^wizard$"], decision="allow")`
   - `prefix_rule(pattern=["rm","-rf","dbt_packages","target"], decision="allow")`
     (consistent with existing `rm -rf target` allow; sits under the general `rm -rf`
     forbidden as a specific override)
3. Symlink `~/.dbt/wizard/rules/default.rules` → this file (Component 2).

Tradeoff: cleaning the Codex rules means some previously auto-approved one-off commands
will prompt again. Accepted — that is the intent of the cleanup; durable rules retained.

### Component 4 — shared global instructions

Symlink `~/.dbt/wizard/AGENTS.md` → `dotfiles/AGENTS.md` (Component 2). Wizard reads it
as its home-level project doc. All three agents (Claude via `CLAUDE.md` import, Codex via
`.codex/AGENTS.md` pointer, Wizard via direct symlink) now share one instructions file.
`dotfiles/AGENTS.md` content is left unchanged (the trailing `@RTK.md` line is a
pre-existing condition shared with Codex/Claude; out of scope here).

### Component 5 — MCP overlap (mirror all Codex MCP servers)

Port every `[mcp_servers.*]` block from `dotfiles/.codex/config.toml` into
`dotfiles/wizard/config.toml`, preserving Wizard's existing keys (`model`,
`model_reasoning_effort`, project trust). Includes:

- Remotes (Runlayer `url` + optional `bearer_token_env_var`): `github` (with its
  `tools.*.approval_mode` sub-tables), `notion-runlayer`, `slack`, `dbt`, `grep`,
  `salesforce`, `runlayer-docs`, `google_sheets`, `google-sheets`.
- Local stdio: `serena`, `community-slack`, `parallel-search`, `strudel`.

Adjustments:
- `serena`: keep `--context=codex` (Wizard is a Codex fork; `codex` context is the safe
  match). Revisit if Wizard ships a dedicated context.
- Do **not** copy Codex's `[plugins.*]`, `[marketplaces.*]`, `[hooks.*]`, `[projects.*]`,
  `[notice.*]`, `[tui.*]` — those are Codex-runtime-specific / machine state, not MCP.

Note: Claude's `mcp.json` (JSON) and Codex/Wizard `config.toml` (TOML) cannot be a single
shared file (format mismatch), so MCP overlap is achieved by mirroring, not unification.
Runlayer remotes require existing Okta-granted access (the user already uses them in Codex).

## Verification

- `./links.sh dry-run` then `./links.sh check` and `./links.sh doctor` — confirm the 5
  new symlinks resolve and no critical `~/.dbt/*` symlinks are disturbed.
- `wizard doctor` — confirm `config.toml parse ok`, MCP server count > 0, rules load,
  AGENTS.md picked up.
- `git status` — confirm only `dotfiles/wizard/*`, `links.tsv`, the cleaned
  `.codex/rules/default.rules`, and this spec are staged; `auth.json`/state/logs remain
  untracked; no unrelated working-tree drift swept in.
- Run the links test suite (`tests/test_links.py`) and update fixtures if it enumerates
  tracked links.

## Out of scope

- RTK hook wiring for Wizard (hook-based command rewriting; Wizard hooks not configured).
- Fixing the `@RTK.md` import inside `dotfiles/AGENTS.md`.
- Unifying MCP definitions into a single cross-format source.
- Tracking install-managed `skills/.system/` content.

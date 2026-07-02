# Chrome extension internal-settings export — design

**Date:** 2026-07-02
**Status:** Approved (design); pending implementation plan
**Repo:** `~/Developer/dotfiles` (public)

## Problem

The existing Chrome sync tooling (`chrome/profiles.toml` + `bin/chrome-sync-check`,
see `docs/superpowers/specs/2026-07-02-chrome-profile-sync-design.md`) tracks
whether an extension is *installed* per profile, but not that extension's own
internal configuration — e.g. Dark Reader's per-site dark-mode rules, uBlock
Origin Lite's filter-list selections. The user wants those settings backed up
and source-controlled so they can be restored onto a new machine or a new
profile "at a later date." Initial extension list: uBlock Origin Lite, Dark
Reader, 1Password, Privacy Badger, Reddit Enhancement Suite, Tab Wrangler.

## Also in scope: a bug found in the existing tool

While investigating this feature, direct inspection of the real profiles
found that `bin/chrome-sync-check` reads the wrong file for the installed
extensions list:

```
Default  Preferences         num extensions: 0
Default  Secure Preferences  num extensions: 32
Profile 1 Preferences        num extensions: 0
Profile 1 Secure Preferences num extensions: 16
Profile 2 Preferences        num extensions: 0
Profile 2 Secure Preferences num extensions: 11
```

On this Chrome version, `extensions.settings` lives in `Secure Preferences`,
not `Preferences`. This was masked in the shipped tests and the first live
run because `chrome/profiles.toml` had zero `[[extensions]]` entries — an
empty "missing" set is empty either way. As soon as a real extension entry
is added, `chrome-sync-check` would wrongly report it as missing even when
installed. The implementation plan for this feature includes fixing
`load_preferences` (or adding a second loader) to read `Secure Preferences`
for the extensions list, since it's a small, related, already-diagnosed fix
touching the same script.

## Background: how extension settings are actually stored

Confirmed by inspecting `Local Extension Settings/<extension-id>/` in a real
profile (uBlock Origin Lite = `ddkjiahejlhfcafbddmgiahcphecmpfh`, Dark Reader
= `eimadpbcbfnmbkopoojfekhnkhdbieeh`, found via `Secure Preferences`
`manifest.name`):

- Each extension's `chrome.storage.local` data lives in its own **LevelDB**
  database at `<profile>/Local Extension Settings/<id>/` — `.log`/`.ldb`/
  `MANIFEST-*`/`LOCK` files, actively written to while Chrome runs.
- **This is a live, lockable database, not a static file.** While Chrome is
  running, the `LOCK` file is held (confirmed via `lsof`); a naive symlink or
  direct read/write across 3 profiles sharing one store would mean multiple
  Chrome processes contending for one exclusive lock — the tool this design
  produces requires Chrome to be **fully quit** before reading, and never
  writes to it.
- **With Chrome quit, the lock is free** (confirmed: `lsof` on the `LOCK`
  file returns nothing once Chrome exits) and the database becomes readable.
- Per Chromium's `LeveldbValueStore` implementation, each row is
  `key -> JSON-serialized value` for that extension's flat
  `chrome.storage.local` namespace — no extension-ID prefixing needed since
  each extension already gets its own directory/database. **This is an
  internal, undocumented format** that could change across Chrome versions;
  treated here as a best-effort read, not a stable contract.
- Reading it from Python requires a LevelDB binding. `plyvel` is the
  standard choice, but it's a C-extension that links against a native
  `libleveldb` — attempted via `uv run --with plyvel python3 -c "import
  plyvel"` and it failed to build because `leveldb` isn't installed via
  Homebrew on this machine yet (`brew list leveldb` → "No such keg"). This
  is a one-time `brew install leveldb` (added to the repo's `Brewfile`),
  not a blocker, but **not yet done** — it happens during implementation,
  not as part of this design step, since it's a real (if low-risk,
  reversible) system change.
- Not all extensions necessarily support a self-service "export settings"
  button (uBlock Origin Lite's minimal MV3 settings surface is uncertain
  here) — reading `chrome.storage.local` directly sidesteps that
  per-extension uncertainty entirely, at the cost of requiring Chrome closed
  and a new native dependency.

## Design

### 1. Scope

- **In scope:** read-only export of `chrome.storage.local` for the 6 named
  extensions, across whichever of the 3 profiles each is installed in.
- **Out of scope:** import/restore ("at a later date" per the user — writing
  back into a live LevelDB is riskier than reading one and deserves its own
  design when actually needed), and the `Secure Preferences` bug fix is
  scoped into the *implementation plan* for convenience (same script, already
  diagnosed) but is conceptually independent of the export feature itself.

### 2. New script: `bin/chrome-extension-settings-export`

A separate script from `bin/chrome-sync-check` — this is a one-shot export
action, not a drift check, so it has a different responsibility and doesn't
belong in the same file.

1. **Dependency handling:** this is the first script in the repo needing a
   third-party package. Rather than the stdlib-only `uv run python3`
   pattern used elsewhere, this script uses `uv run --script` with inline
   PEP 723 metadata:

   ```python
   #!/usr/bin/env -S uv run --script
   # /// script
   # requires-python = ">=3.12"
   # dependencies = ["plyvel"]
   # ///
   ```

   **Needs verification during implementation:** confirm `uv run --script`
   actually resolves and builds `plyvel` correctly via this shebang
   invocation shape (vs. the `uv run python3 <path>` shape used by other
   `bin/` scripts, which does *not* parse inline metadata) once `leveldb` is
   installed via Homebrew.
2. **Chrome-must-be-quit check:** don't shell out to `ps`/`lsof` to guess
   whether Chrome is running — just attempt to open each target LevelDB
   read-only (`plyvel.DB(path, create_if_missing=False)`); if Chrome is still
   holding the lock, this raises an `IOError`. Catch it and print a clear
   "quit Chrome and retry" error naming the profile/extension, then exit 1.
   This is the authoritative check (no TOCTOU race against a separate
   process-listing check).
3. **Manifest-driven export:** reads `chrome/profiles.toml`'s existing
   `[profiles]` table (email → resolved directory, same logic as
   `chrome-sync-check`) plus a new `[[extension_settings]]` table:

   ```toml
   [[extension_settings]]
   name = "Dark Reader"
   id = "eimadpbcbfnmbkopoojfekhnkhdbieeh"
   profiles = ["personal", "dbtlabs", "fivetran"]
   ```

   For each entry × each scoped, resolved profile: if
   `<profile>/Local Extension Settings/<id>/` doesn't exist, print
   "not installed in `<profile-name>`, skipping" and continue (not an
   error — matches `chrome-sync-check`'s tolerant style for
   profiles/extensions that don't apply everywhere). Otherwise, open the
   LevelDB read-only, iterate all key/value pairs, and build a dict:
   - key: UTF-8 decoded.
   - value: `json.loads()`; on failure (`UnicodeDecodeError` or
     `json.JSONDecodeError`), fall back to
     `{"__raw_base64__": base64.b64encode(value).decode()}` so nothing is
     silently lost or corrupted by an unexpected internal format.
4. **Output — staging, not the committed path:** writes pretty-printed,
   key-sorted JSON to
   `chrome/extension-settings/.staging/<profile>/<id>.json` — a **gitignored**
   directory, never the final committed location. The script never decides
   public vs. private; that's a human judgment call (§4).
5. **Optional filters:** `--extension NAME` and `--profile NAME` to
   re-export a subset (e.g. after changing just Dark Reader's rules),
   mirroring the `--repo` filter style in `bin/github-notification-sweep`.

### 3. Bug fix folded into the same plan

In `bin/chrome-sync-check`, `load_preferences` (or a sibling loader) needs
to read `Secure Preferences` for the `extensions.settings` key instead of
(or in addition to — TBD in the plan, likely instead of, since `Preferences`
apparently no longer carries this key on current Chrome) `Preferences`.
Existing tests fabricate their own `Preferences` fixture and pass regardless
of this bug, since the manifest under test always defines the extension
itself — the fix must also update those fixtures to write to `Secure
Preferences` so the tests actually exercise the real file Chrome uses.
Settings diffing (`pref_path` walking) is unaffected — that's for Chrome's
own settings, not extension state, and the bug is specific to the
extensions list.

### 4. Manual triage workflow (safety)

Because `dotfiles` is public and we don't know a given extension's storage
contents until we look, promotion out of the gitignored staging directory
is **always a manual human step**, never automated by the script:

1. Run `bin/chrome-extension-settings-export`.
2. Open each `chrome/extension-settings/.staging/<profile>/<id>.json` and
   look for anything that resembles a session token, device identifier, or
   other account-adjacent secret (most likely candidate: 1Password).
3. Move the file to either:
   - `chrome/extension-settings/<profile>/<id>.json` (public dotfiles), or
   - `~/Developer/dotfiles_env/chrome/extension-settings/<profile>/<id>.json`
     (private) if anything looks sensitive.
4. Commit from whichever repo it landed in.

This workflow is documented in `chrome/README.md`, not enforced by the
script — the script's only responsibility is producing a safe-to-inspect
staging copy.

### 5. File layout

```
dotfiles/chrome/profiles.toml                          # extended with [[extension_settings]]
dotfiles/bin/chrome-extension-settings-export           # new script
dotfiles/chrome/extension-settings/.staging/            # gitignored scratch output
dotfiles/chrome/extension-settings/<profile>/<id>.json  # promoted, public-safe exports (once triaged)
dotfiles/Brewfile                                       # + leveldb
```

## Recovery / failure modes

- **Chrome running:** every target LevelDB open fails with a clear
  per-profile/per-extension error; nothing partially written for that
  target (each extension × profile is an independent open/read/write, so
  one locked target doesn't abort the whole run — others still export).
- **Extension not installed in a scoped profile:** skipped with a message,
  not an error (matches `chrome-sync-check`'s tolerance for "not every
  profile has every tracked extension").
- **Value isn't valid JSON:** falls back to a `__raw_base64__` wrapper
  rather than crashing or dropping the key.
- **`plyvel`/`leveldb` not installed:** the inline PEP 723 metadata handles
  `plyvel` (uv fetches it automatically); `leveldb` itself must be installed
  via Homebrew first (`brew install leveldb`, added to the `Brewfile`) —
  this is a one-time manual/implementation-time setup step, not something
  the script auto-installs.

## Scope / non-goals (YAGNI)

- **No import/restore.** Explicitly deferred ("at a later date"); writing
  into a live LevelDB is a different risk profile from reading one and
  warrants its own design when needed.
- **No automatic public/private classification.** A human looks at the
  content once per extension/profile; the script never guesses.
- **No drift-checking against this data.** Same reasoning as the original
  `chrome-sync-check` design — there's no safe way to read this while
  Chrome is running, so there's no live state to continuously diff against;
  this is a point-in-time backup tool, not a sync-check.
- **No scheduled/automatic runs.** Manual, run when the user wants a fresh
  backup before a settings change or a machine migration.

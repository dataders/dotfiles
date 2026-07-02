# Chrome multi-profile sync

Keeps extensions and select settings consistent across the three Chrome
profiles on this Mac — personal (`swanson.anders@gmail.com`), dbt Labs
(`anders.swanson@dbtlabs.com`), and Fivetran
(`anders.swanson@fivetran.com`) — using `profiles.toml` as the single
source of truth.

Full design rationale, schema, and script behavior:
[`docs/superpowers/specs/2026-07-02-chrome-profile-sync-design.md`](../docs/superpowers/specs/2026-07-02-chrome-profile-sync-design.md).

## Why this works the way it does

This Mac can't safely have Chrome state *written* to it outside of one
narrow channel, so the tooling here is deliberately read-only plus
human-in-the-loop, not automatic enforcement:

- **The Mac is MDM-managed (Jamf).** Chrome's policy file
  (`/Library/Managed Preferences/<user>/com.google.Chrome.plist`) is
  root-owned and already carries an org-pushed policy. Writing our own
  policy entries there would need `sudo`, could be overwritten on the next
  Jamf check-in, and risks colliding with an org policy.
- **Chrome's per-profile `Preferences` file has tamper protection.** Since
  Chrome ~20, many keys — including the installed-extensions list — are
  guarded by a pref-hash-seed check. Editing this file directly is likely to
  get silently reverted by Chrome on next launch.
- **There's no supported unmanaged policy channel anymore.** Modern Chrome
  only honors policy from MDM-managed sources, so there's no safe way to
  force-install extensions or force-set settings outside Jamf's channel.

Given that, the only sound design is: keep the *desired* state in a
manifest, compare it against the *actual* state read-only, and hand the
user a shortcut for the one action that still requires a manual click
(installing an extension from the Web Store).

## How it works

1. **`profiles.toml`** — the manifest. Maps friendly profile names to
   Google account emails (not Chrome's `Profile 1`/`Profile 2` directory
   names, which aren't stable across profile recreation), and lists desired
   extensions and settings, each scoped to which profiles they apply to.
2. **`bin/chrome-sync-check`** — resolves each manifest profile to its
   actual Chrome profile directory via `Local State`, then reads each
   profile's `Secure Preferences` (installed-extensions list — this is
   where it actually lives on current Chrome, not `Preferences`) and
   `Preferences` (Chrome-level settings) read-only to report
   missing/untracked extensions and setting mismatches. Every profile
   prints a line: either `<name>: in sync` or a breakdown of what's
   missing/untracked/mismatched.
3. **`bin/chrome-sync-check --open-missing`** — same check, plus opens the
   Chrome Web Store listing for any missing extension in the right
   profile's window, so installing it is a single click. This only covers
   extensions; setting mismatches are reported, not auto-fixed, since there's
   no reliable deep link into `chrome://settings` for an arbitrary toggle.

The manifest is the only thing you hand-edit day to day — add an extension
or setting once, then run the check script against all three profiles.

## Backing up extension internal settings

Separate from the drift-check above: some extensions' own configuration
(theme rules, filter lists, per-site overrides) lives in the extension's
own storage, not anywhere `chrome-sync-check` looks. This is a point-in-time
backup for restoring onto a new machine or profile later, not an ongoing
sync mechanism — there's no safe way to read this while Chrome is running,
so there's nothing to continuously diff against.

Two mechanisms, depending on the extension:

**Native export (Dark Reader, uBlock Origin Lite, Privacy Badger).** These
have a usable "export settings" feature in their own UI. Export manually,
then commit the file directly under `chrome/extension-settings/<profile>/<id>.json`
(or the private `dotfiles_env` equivalent — see below). No script involved.

Note: Privacy Badger's own export bundles its multi-megabyte *learned*
tracker data (`action_map`, `snitch_map`, `tracking_map`) along with the
554-byte `settings_map` that's your actual explicit configuration. Extract
just `settings_map` before committing — the learned data regenerates on
its own as you browse, so backing it up isn't useful and bloats the repo.

**`bin/chrome-extension-settings-export` (Tab Wrangler, Reddit Enhancement
Suite).** For extensions with no adequate native export. Reads
`chrome.storage` directly via the `leveldbutil` CLI (bundled with the
`leveldb` Homebrew formula) — **requires Chrome fully quit** (it tries to
`flock()` the LevelDB `LOCK` file first and reports a clear error if
something still holds it, rather than guessing from running processes).

Each `[[extension_settings]]` manifest entry needs a `storage` field
(`"local"` or `"sync"` — which of `Local Extension Settings` /
`Sync Extension Settings` the extension actually uses; check both if
unsure, since it varies per extension) and a `keys` allowlist. The
allowlist matters: raw extension storage mixes real settings with
runtime/telemetry data — e.g. Dark Reader's storage includes full tab and
browsing history under `TabManager-state`, and Tab Wrangler's real settings
(`maxTabs`, `whitelist`, etc.) live in `chrome.storage.sync` while
`chrome.storage.local` holds only per-tab activity timestamps. Only
allowlisted keys are ever written out.

Run: `bin/chrome-extension-settings-export` (optionally `--extension NAME`
/ `--profile NAME` to limit scope). Output lands in the gitignored
`chrome/extension-settings/.staging/<profile>/<id>.json` — never a
committed location directly.

**Promotion is always a manual step**, since `dotfiles` is public and we
don't know what a given extension's storage or export actually contains
until we look — even values that read as generic "settings" from the key
name (e.g. a disabled-sites list) can reveal identifying personal-life
details (which insurance company, which tax software, which telehealth
provider) once you see the actual values. Open each staged file, check it,
then move it to either:

- `chrome/extension-settings/<profile>/<id>.json` (public dotfiles), or
- `~/Developer/dotfiles_env/chrome/extension-settings/<profile>/<id>.json`
  (private) if anything looks more identifying than a generic toggle.

If a committed version already exists, diff the staged copy against it
before overwriting — a later export surfacing something newly sensitive
must not silently replace a file already known to be safe.

Import/restore isn't built yet — writing back into a live LevelDB is
riskier than reading one and is deferred until actually needed.

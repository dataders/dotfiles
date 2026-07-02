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
   profile's `Preferences` JSON (read-only) to report missing/untracked
   extensions and setting mismatches. Every profile prints a line: either
   `<name>: in sync` or a breakdown of what's missing/untracked/mismatched.
3. **`bin/chrome-sync-check --open-missing`** — same check, plus opens the
   Chrome Web Store listing for any missing extension in the right
   profile's window, so installing it is a single click. This only covers
   extensions; setting mismatches are reported, not auto-fixed, since there's
   no reliable deep link into `chrome://settings` for an arbitrary toggle.

The manifest is the only thing you hand-edit day to day — add an extension
or setting once, then run the check script against all three profiles.

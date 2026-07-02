# Chrome multi-profile extension/settings sync — design

**Date:** 2026-07-02
**Status:** Approved (design); pending implementation plan
**Repo:** `~/Developer/dotfiles` (public)

## Problem

The user runs three Chrome profiles on one Mac — personal, dbt Labs, and
Fivetran — and wants a single source-controlled file that lets them keep
extensions and select settings consistent across all three, instead of
manually replicating each change three times.

## Background: constraints discovered before designing

Confirmed by inspecting this machine's actual Chrome state:

- **Profiles:** `Default` → `swanson.anders@gmail.com` (personal), `Profile 1`
  → `anders.swanson@dbtlabs.com` (dbt Labs), `Profile 2` →
  `anders.swanson@fivetran.com` (Fivetran). Directory names (`Profile 1`,
  `Profile 2`) are assigned by Chrome and are **not stable identifiers** — they
  can shift if profiles are removed/recreated. The account email in
  `Local State` → `profile.info_cache.<dir>.user_name` is the stable key.
- **This Mac is MDM-managed (Jamf).** `/Library/Managed Preferences/<user>/com.google.Chrome.plist`
  already carries an org-pushed policy (a force-installed extension, applied
  identically across Chrome, Brave, Edge, Chromium, and other browsers on this
  machine). That file is root-owned and periodically rewritten by Jamf.
  Writing our own entries into it would require `sudo`, could be silently
  clobbered on the next Jamf check-in, and risks conflicting with or
  overriding an org policy. **Out of scope.**
- **Chrome's per-profile `Preferences` JSON has tamper protection.** Since
  Chrome ~20, many preference keys (including the extension list and several
  security-relevant settings) are guarded by a pref-hash-seed mechanism.
  Directly editing this file — even just for the local user, no MDM involved
  — risks Chrome detecting the change as tampering and silently reverting it
  on next launch. **Direct writes are out of scope**; reading it is fine (no
  protection on reads).
- **No supported unmanaged policy channel remains.** Older Chrome versions
  allowed testing policies via the unmanaged `~/Library/Preferences/com.google.Chrome.plist`
  domain; modern Chrome only honors policies from MDM-managed sources. There
  is no safe, non-MDM way to force-install extensions or force-set settings.
- **Extensions currently show 0 installed in any profile's `Preferences`** —
  this is closer to a fresh baseline than reconciling heavily-diverged
  profiles.

**Implication:** there is no safe way to *write* Chrome state on this
machine outside of the Jamf-owned channel. The only sound design is
**read-only inspection + a manifest as source of truth + human-in-the-loop
install**, not automatic enforcement.

## Design

### 1. Manifest (`chrome/profiles.toml`)

Single source of truth, committed to dotfiles.

```toml
[profiles]
personal = "swanson.anders@gmail.com"
dbtlabs  = "anders.swanson@dbtlabs.com"
fivetran = "anders.swanson@fivetran.com"

[[extensions]]
name = "uBlock Origin"
id = "cjpalhdlnbpafiamejdnhcphjbkeiagm"
profiles = ["personal", "dbtlabs", "fivetran"]

[[settings]]
name = "Always show bookmarks bar"
pref_path = "bookmark_bar.show_on_all_tabs"
value = true
profiles = ["personal", "dbtlabs", "fivetran"]
```

- `[profiles]` maps a friendly name to the Google account email, not a
  directory name — resolved to an actual profile directory at runtime (see
  §2) so the manifest survives profile re-creation/reordering.
- `[[extensions]]` entries list a Chrome Web Store extension ID and which
  profiles should have it.
- `[[settings]]` entries name a dotted JSON path (`pref_path`) into the
  profile's `Preferences` file and a desired value, for read-only comparison
  only (see Background — no write path exists).
- `pref_path` values are discovered empirically: toggle the setting once in
  Chrome's UI, diff `Preferences` before/after to find the key. This is
  manual, one-time, per setting — documented in the script's `--help` or a
  short comment in the manifest.

### 2. Check script (`bin/chrome-sync-check`)

Python, `uv run python3` shebang (matching `bin/github-notification-sweep`
convention). Read-only.

1. Read `~/Library/Application Support/Google/Chrome/Local State`, build a
   map of account email → profile directory name
   (`profile.info_cache.<dir>.user_name`).
2. For each `[profiles]` entry in the manifest, resolve to a directory. If an
   email from the manifest isn't found in `Local State`, report it clearly
   (profile not present on this machine) rather than crashing.
3. For each resolved profile, read its `Preferences` JSON:
   - **Extensions:** compare `extensions.settings` keys (extension IDs)
     against the manifest's `[[extensions]]` entries scoped to that profile.
     Report missing (in manifest, not installed) and untracked (installed,
     not in manifest) extensions.
   - **Settings:** for each `[[settings]]` entry scoped to that profile, walk
     `pref_path` and compare against `value`. Report mismatches. A path that
     doesn't exist in `Preferences` is reported as "unset" (not the same as
     "wrong value" — Chrome may not write a key until first touched).
4. Print a per-profile report to stdout, plain text, grouped by profile name
   in manifest order, in this shape:

   ```
   personal (swanson.anders@gmail.com):
     missing extensions:    uBlock Origin (cjpalhdlnbpafiamejdnhcphjbkeiagm)
     untracked extensions:  Grammarly (kbfnbcaeplbcioakkpcpgfkobkghlhen)
     setting mismatches:    Always show bookmarks bar (want true, got false)
   ```

   A profile with nothing to report prints `<name>: in sync`. Exit code 0
   always for the check-only path (this is a report, not a CI gate); a
   non-zero exit is reserved for hard failures (e.g. `Local State` missing
   or unparseable — see Recovery below).
5. **Comparison semantics for settings:** compare the value at `pref_path`
   to the manifest's `value` with strict type-and-value equality (Python
   `==` after JSON-decoding both sides — so `true`/`1`/`"true"` are *not*
   treated as equivalent). A path that doesn't exist in `Preferences` is
   reported as "unset", distinct from "wrong value".

**Needs verification during implementation** (stated here as working
assumptions, not confirmed facts): the exact `extensions.settings` key
shape in `Preferences` (ID → dict with an `install_time`/`state`-style
schema) should be checked against the actual installed Chrome version
before the check logic is finalized, the same way the tamper-protection
claim above already flags Chrome's preference handling as version-sensitive.

### 3. Install helper (`--open-missing` flag on the same script)

For every missing extension found in step 3, open the Web Store listing in
the *correct* profile's window so the user just clicks "Add to Chrome".

**Needs verification during implementation:** the naive approach —
`open -a "Google Chrome" --args --profile-directory="<dir>" "<url>"` — is
**known to be unreliable when Chrome is already running**: it typically just
focuses/reuses the existing window and ignores both `--profile-directory`
and the URL, per multiple independently-reported cases. Since the user
routinely has all three profiles open, this is the common case, not an edge
case. The implementation must test, in order of preference:

1. `open -n -a "Google Chrome" --args --profile-directory="<dir>" "<url>"`
   (`-n` forces a new instance) — verify this actually lands on the intended
   profile rather than the last-focused one.
2. Invoking the Chrome binary directly
   (`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --profile-directory="<dir>" "<url>"`)
   as a fallback if `-n` proves unreliable.

If neither reliably targets the right profile while other profiles are
open, the fallback behavior is to print the URL and profile name instead of
attempting to open it, and let the user open it manually — this degrades
`--open-missing` to a slightly more convenient version of the plain report,
which is still strictly better than a broken/misleading auto-open. This
must be manually verified against the installed Chrome version before
`--open-missing` ships; the check-only path (§2) has no such dependency and
can ship independently.

No install automation beyond opening the listing — Chrome does not allow
scripted, non-policy extension installation, and forcing it through policy
is the exact risk ruled out in Background.

Settings mismatches are **reported only**, with the setting's human name
(from `name`) — no auto-open, since there's no single deep-link URL pattern
that reliably lands on the exact toggle across all `chrome://settings`
pages.

### 4. File layout

```
dotfiles/chrome/profiles.toml       # manifest, source of truth
dotfiles/bin/chrome-sync-check      # read-only check + --open-missing
```

Not wired into `links.tsv`/PATH — invoked directly from the repo like the
other `bin/` scripts (`bin/github-notification-sweep`, `bin/moonlander-keylog`).

## Recovery / failure modes

- **Chrome closed vs. open, for the check path (§2):** reading `Preferences`
  while Chrome is running is safe (no lock contention for reads); no special
  handling needed since this is read-only. This does **not** extend to the
  install helper (§3) — see its own verification requirement above, since
  launching/focusing Chrome while it's already running is exactly where the
  naive approach breaks.
- **`Local State` missing or unparseable:** hard failure — without it no
  profile can be resolved at all. Print a clear error and exit non-zero
  (the one case where this tool exits non-zero; see §2 step 4).
- **Manifest references a profile not on this machine:** reported as a
  warning per profile, not a hard failure — keeps the manifest portable
  across machines (e.g. a future work laptop) even if not every profile
  exists everywhere.
- **`pref_path` typo or Chrome version changes the key:** shows up as a
  perpetual "unset" mismatch for that setting; no crash. Discovered
  empirically same as initial setup.

## Resolved during spec review

- The `open -a "Google Chrome" --args --profile-directory=...` command as
  originally drafted is **not** reliable when Chrome is already running (the
  common case here) — flagged above as a verify-during-implementation item
  with `-n` and direct-binary fallbacks, rather than left as an assumed fact.
- Report output format and settings-comparison semantics were unspecified;
  now pinned down in §2 to avoid two implementers converging on different
  shapes.

## Scope / non-goals (YAGNI)

- **No writing to `Preferences` or any Chrome policy file.** Ruled out in
  Background for both the MDM-conflict and tamper-protection reasons.
- **No bookmarks/history/passwords sync.** Out of scope — Chrome's own
  Google-account sync already covers per-account data; this tool is only for
  cross-account (cross-profile) alignment of extensions/settings that
  Google sync doesn't unify.
- **No scheduled/automatic runs.** The user runs `bin/chrome-sync-check`
  manually when they want a drift report; no LaunchAgent.
- **No settings auto-open.** Only extensions get the `--open-missing`
  Web Store shortcut (see §3).

# Chrome extension internal-settings export — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Also see @superpowers:test-driven-development for the write-test-first discipline within each task.

**Goal:** Fix a real bug in `bin/chrome-sync-check` (wrong file for the extensions list), then build `bin/chrome-extension-settings-export` — a read-only tool that dumps `chrome.storage.local` for manifest-tracked extensions (uBlock Origin Lite, Dark Reader, 1Password, Privacy Badger, Reddit Enhancement Suite, Tab Wrangler) to a gitignored staging directory, for later manual triage into the public or private dotfiles repo.

**Architecture:** A new standalone script using `plyvel` (LevelDB bindings) via `uv run --script` with inline PEP 723 dependency metadata — the first non-stdlib-only script in this repo. It requires Chrome fully quit (detected by attempting to open the target LevelDB and catching the resulting `OSError` if still locked, not by guessing via `ps`). Output always goes to a gitignored staging path; promotion to a committed location is a manual human step, documented but not automated.

**Tech Stack:** Python 3.12, `plyvel` (new dependency, resolved per-invocation via PEP 723), `tomllib`/`argparse`/`json`/`base64` (stdlib), `unittest` + `subprocess` black-box tests matching the existing `tests/test_chrome_sync_check.py` style, with `plyvel`-built LevelDB fixtures standing in for Chrome's real storage.

**Specs:**
- `docs/superpowers/specs/2026-07-02-chrome-extension-settings-export-design.md` (this plan's primary spec — read first)
- `docs/superpowers/specs/2026-07-02-chrome-profile-sync-design.md` (background on the existing `chrome-sync-check` tool this plan also patches)

**Important — read before starting:** Task 1 is an environment-verification spike, not app code. Several assumptions in the spec are explicitly flagged "needs verification during implementation." Task 1 checks them against your real machine. **If any assumption turns out false, stop after Task 1 and report back with findings rather than improvising a fix and continuing** — the later tasks' code was written assuming the spec's stated behavior holds.

---

## Task 1: Environment spike — leveldb, plyvel, and the real storage format

**Files:**
- Modify: `Brewfile` (add `leveldb`)

This task does not write application code. It sets up the one new system
dependency this feature needs, and empirically checks the assumptions the
rest of this plan is built on.

- [ ] **Step 1: Check whether Chrome is currently running**

Run: `pgrep -x "Google Chrome"`

If this prints a PID, Chrome is running. **Stop and ask the user to quit
Chrome**, then continue once it prints nothing (no output, exit code 1).
Do not proceed to Step 4 below with Chrome open — the whole point of this
check is to test the closed-Chrome behavior for real.

- [ ] **Step 2: Add `leveldb` to the Brewfile and install it**

Open `Brewfile` and add a line `brew "leveldb"` near other `brew` entries
(match the file's existing grouping style — look at how other libraries are
grouped before picking a spot; don't reorder unrelated lines).

Run: `brew install leveldb`
Expected: installs successfully (or reports already installed).

- [ ] **Step 3: Verify `plyvel` builds now**

Run: `/opt/homebrew/bin/uv run --with plyvel python3 -c "import plyvel; print(plyvel.__version__)"`
Expected: prints a version string, no build errors. (Earlier, before
`leveldb` was installed, this failed with `fatal error: 'leveldb/db.h'
file not found` — confirm that's resolved.)

This confirms `plyvel` builds, but **not** the actual invocation shape
`bin/chrome-extension-settings-export` will use — `--with plyvel` is a
different mechanism from the inline PEP 723 metadata + `uv run --script`
shebang that script commits to in Task 4. Verify that shape specifically,
since it's the one thing the spec flags as unverified and this Task 1 spike
exists to check:

```bash
cat > /tmp/plyvel-shebang-check.py <<'EOF'
#!/usr/bin/env -S /opt/homebrew/bin/uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["plyvel"]
# ///
import plyvel
print(plyvel.__version__)
EOF
chmod +x /tmp/plyvel-shebang-check.py
/tmp/plyvel-shebang-check.py
rm /tmp/plyvel-shebang-check.py
```

Expected: prints a version string when executed directly (not via `uv run
python3 <path>` or `--with`) — confirming the shebang shape Task 4's real
script uses actually resolves `plyvel` on its own. If this fails while Step
3's `--with plyvel` form succeeded, that's a real, narrower problem with the
`--script`/PEP 723 shebang specifically — stop and report it rather than
falling back to a different dependency mechanism without discussion (it
would mean Task 4 onward needs a different approach than the spec assumed).

- [ ] **Step 4: Empirically verify the storage format against real data**

With Chrome confirmed quit (Step 1), run this one-off script — it only
prints key names and value *types*, never full value content (some of this
is the user's real extension data; keep the output structural, not a raw
data dump):

```bash
/opt/homebrew/bin/uv run --with plyvel python3 -c "
import json
import plyvel

path = '/Users/dataders/Library/Application Support/Google/Chrome/Default/Local Extension Settings/eimadpbcbfnmbkopoojfekhnkhdbieeh'
db = plyvel.DB(path, create_if_missing=False)
count = 0
json_ok = 0
for key, value in db:
    count += 1
    try:
        json.loads(value.decode('utf-8'))
        json_ok += 1
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    if count <= 5:
        print(repr(key.decode('utf-8', errors='replace')), '-> value type OK:', True)
db.close()
print(f'{count} total keys, {json_ok} decoded as JSON')
"
```

Expected: opens without error (confirms the lock is free once Chrome is
quit, and confirms `plyvel.DB(..., create_if_missing=False)` is the right
call), prints some keys, and most/all values decode as JSON (confirms the
flat `key -> JSON value` assumption from the spec's Background section).

**If this fails to open, or most values are NOT valid JSON:** stop here.
Report back exactly what happened (error message, or what the values
actually look like) rather than guessing a workaround — the decode logic in
later tasks assumes this holds.

- [ ] **Step 5: Verify the locked-Chrome failure mode**

Open Chrome (any way — e.g. `open -a "Google Chrome"`), wait a few seconds
for it to fully launch, then run:

```bash
/opt/homebrew/bin/uv run --with plyvel python3 -c "
import plyvel
try:
    db = plyvel.DB('/Users/dataders/Library/Application Support/Google/Chrome/Default/Local Extension Settings/eimadpbcbfnmbkopoojfekhnkhdbieeh', create_if_missing=False)
    print('opened without error (unexpected if Chrome is running)')
except OSError as exc:
    print('got OSError as expected:', exc)
"
```

Expected: `OSError` is raised and printed (confirms the spec's assumption
that a locked LevelDB raises a catchable `OSError`/`IOError` rather than
hanging or crashing the interpreter). Quit Chrome again afterward so it's
not running for the rest of this plan's manual testing.

- [ ] **Step 6: Commit the Brewfile change**

```bash
git add Brewfile
git commit -m "chore(chrome): add leveldb for extension settings export"
```

- [ ] **Step 7: Report findings**

In your final report, explicitly confirm or refute each of: (a) `leveldb`
installs and `plyvel` builds, (b) the `uv run --script` + inline PEP 723
shebang shape resolves `plyvel` on its own (Step 3's second check), (c) the
flat `key -> JSON value` format holds, (d) a locked DB raises `OSError`. If
any is false, use status `BLOCKED` and describe exactly what you observed
instead — do not continue to further
tasks in that case.

---

## Task 2: Fix `chrome-sync-check`'s `Secure Preferences` bug

**Files:**
- Modify: `bin/chrome-sync-check`
- Modify: `tests/test_chrome_sync_check.py`

The installed-extensions list is read from `Preferences`, but on real
Chrome installs it lives in `Secure Preferences`. This task points the
loader at the right file and updates the existing tests' fixtures to match
(they currently pass by writing extension data into `Preferences`, which
means they don't actually exercise the file real Chrome uses).

- [ ] **Step 1: Update the test fixture helper**

In `tests/test_chrome_sync_check.py`, find the `write_preferences` helper
method:

```python
    def write_preferences(self, chrome_dir, dirname, prefs):
        profile_dir = chrome_dir / dirname
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "Preferences").write_text(json.dumps(prefs))
```

This method is used by every test that needs to set extension state
(`test_missing_extension_is_reported`, `test_installed_extension_is_in_sync`,
`test_untracked_extension_uses_manifest_name_when_available`,
`test_untracked_extension_falls_back_to_id_without_manifest_name`, both
`--open-missing` tests). Add a second helper alongside it for the file
extensions actually live in, and change every one of those tests' calls to
write extension data via the new helper instead of `write_preferences`
where they're setting `{"extensions": {...}}`. Note: `test_unset_setting_is_reported`
/ `test_wrong_value_setting_is_reported` / `test_matching_setting_is_in_sync`
set **settings** (e.g. `bookmark_bar`), not extensions — leave those
untouched, they should keep using `write_preferences`.

Add:

```python
    def write_secure_preferences(self, chrome_dir, dirname, prefs):
        profile_dir = chrome_dir / dirname
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "Secure Preferences").write_text(json.dumps(prefs))
```

Then change these four tests to call `self.write_secure_preferences(...)`
instead of `self.write_preferences(...)` for their extensions payload
(their settings/general `Preferences` content, if any, stays via
`write_preferences`):

- `test_missing_extension_is_reported`
- `test_installed_extension_is_in_sync`
- `test_untracked_extension_uses_manifest_name_when_available`
- `test_untracked_extension_falls_back_to_id_without_manifest_name`
- `test_open_missing_invokes_open_binary_per_missing_extension`
- `test_no_open_missing_flag_does_not_invoke_open_binary`

Each of these currently has exactly one `self.write_preferences(chrome_dir,
"Default", {"extensions": {...}})`-shaped call (or similar) — replace
`write_preferences` with `write_secure_preferences` in that one call per
test, leaving everything else in the test unchanged.

- [ ] **Step 2: Run tests to verify they now fail**

Run: `/opt/homebrew/bin/uv run python3 -m unittest tests/test_chrome_sync_check.py -v`
Expected: the extension-related tests now FAIL, since `bin/chrome-sync-check`
still reads `Preferences` and the fixtures now only populate
`Secure Preferences`. The 3 settings tests and the ordering/skeleton tests
should still pass.

- [ ] **Step 3: Fix the script**

In `bin/chrome-sync-check`, find `load_preferences`:

```python
def load_preferences(chrome_dir, dirname):
    path = pathlib.Path(chrome_dir) / dirname / "Preferences"
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}
```

Add a sibling loader:

```python
def load_secure_preferences(chrome_dir, dirname):
    path = pathlib.Path(chrome_dir) / dirname / "Secure Preferences"
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}
```

In `build_report`, find this line (inside the per-profile loop):

```python
        prefs = load_preferences(chrome_dir, dirname)
        missing, untracked = diff_extensions(prefs, extensions, name)
        mismatches = diff_settings(prefs, settings, name)
```

Change it to load both files, using `Secure Preferences` for extensions and
`Preferences` for settings (settings diffing is unaffected by this bug —
Chrome-level settings like `bookmark_bar.show_on_all_tabs` are not part of
this issue):

```python
        prefs = load_preferences(chrome_dir, dirname)
        secure_prefs = load_secure_preferences(chrome_dir, dirname)
        missing, untracked = diff_extensions(secure_prefs, extensions, name)
        mismatches = diff_settings(prefs, settings, name)
```

`diff_extensions`, `installed_extensions`, and `extension_display_name` all
take a `prefs`-shaped dict as their argument already — passing
`secure_prefs` instead requires no changes to those functions themselves.

- [ ] **Step 4: Run tests to verify they pass**

Run: `/opt/homebrew/bin/uv run python3 -m unittest tests/test_chrome_sync_check.py -v`
Expected: PASS (13/13, same count as before — no tests added or removed,
just repointed).

- [ ] **Step 5: Sanity-check against the real machine**

Run: `/opt/homebrew/bin/uv run python3 bin/chrome-sync-check`
Expected: still prints `personal: in sync` / `dbtlabs: in sync` /
`fivetran: in sync` (the manifest still has no `[[extensions]]` entries, so
there's nothing to report either way — this just confirms the script still
runs cleanly against real data, not that it detects anything new yet).

- [ ] **Step 6: Commit**

```bash
git add bin/chrome-sync-check tests/test_chrome_sync_check.py
git commit -m "fix(chrome): read extensions list from Secure Preferences"
```

---

## Task 3: Gitignore the staging directory

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add the ignore line**

Open the repo root `.gitignore` and add this line (put it near the other
tool-specific entries, e.g. next to the `keylog-*.csv` / `moonlander/keymaps/`
block, with a one-line comment matching that block's style):

```
# Chrome extension-settings export staging area (never commit unreviewed)
chrome/extension-settings/.staging/
```

- [ ] **Step 2: Verify it works**

```bash
mkdir -p chrome/extension-settings/.staging/personal
echo '{}' > chrome/extension-settings/.staging/personal/test.json
git status --porcelain chrome/
```

Expected: no output (the new files don't show up as untracked).

```bash
rm -rf chrome/extension-settings/.staging
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore(chrome): gitignore extension-settings export staging dir"
```

---

## Task 4: `chrome-extension-settings-export` skeleton

**Files:**
- Create: `bin/chrome-extension-settings-export`
- Create: `tests/test_chrome_extension_settings_export.py`

This task establishes the CLI, manifest/profile resolution (reusing the
same logic pattern as `chrome-sync-check`), and the "extension not
installed in this profile" skip path. No actual LevelDB reading yet — that
lands in Task 5. Because this task's tests don't touch LevelDB at all, they
run with the plain `uv run python3` invocation (no `--with plyvel` needed
yet) — but the *script* still needs the PEP 723 header and `--script`
shebang now, since Task 5 will add the `import plyvel` line and it must
already be resolvable via the shebang by then.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_chrome_extension_settings_export.py`:

```python
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "chrome-extension-settings-export"


class ChromeExtensionSettingsExportTests(unittest.TestCase):
    def write_local_state(self, chrome_dir, profile_emails):
        info_cache = {
            dirname: {"user_name": email} for dirname, email in profile_emails.items()
        }
        (chrome_dir / "Local State").write_text(
            json.dumps({"profile": {"info_cache": info_cache}})
        )

    def write_manifest(self, root, text):
        manifest_path = root / "profiles.toml"
        manifest_path.write_text(text)
        return manifest_path

    def run_export(self, manifest_path, chrome_dir, out_dir, *extra):
        env = os.environ.copy()
        env.update(
            {
                "CHROME_EXTENSION_EXPORT_MANIFEST": str(manifest_path),
                "CHROME_EXTENSION_EXPORT_CHROME_DIR": str(chrome_dir),
                "CHROME_EXTENSION_EXPORT_OUT_DIR": str(out_dir),
            }
        )
        return subprocess.run(
            [str(SCRIPT), *extra],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_extension_not_installed_is_skipped_not_an_error(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            out_dir = tmp / "out"
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[extension_settings]]\n'
                'name = "Dark Reader"\n'
                'id = "eimadpbcbfnmbkopoojfekhnkhdbieeh"\n'
                'profiles = ["personal"]\n',
            )

            result = self.run_export(manifest, chrome_dir, out_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("not installed, skipping", result.stdout)
            self.assertFalse(out_dir.exists())

    def test_profile_not_found_on_machine_is_skipped(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            out_dir = tmp / "out"
            self.write_local_state(chrome_dir, {})
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[extension_settings]]\n'
                'name = "Dark Reader"\n'
                'id = "eimadpbcbfnmbkopoojfekhnkhdbieeh"\n'
                'profiles = ["personal"]\n',
            )

            result = self.run_export(manifest, chrome_dir, out_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("profile not found on this machine, skipping", result.stdout)

    def test_missing_manifest_is_a_hard_failure(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            out_dir = tmp / "out"
            self.write_local_state(chrome_dir, {})

            result = self.run_export(tmp / "does-not-exist.toml", chrome_dir, out_dir)

            self.assertEqual(result.returncode, 1)
            self.assertIn("manifest", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/opt/homebrew/bin/uv run python3 -m unittest tests/test_chrome_extension_settings_export.py -v`
Expected: FAIL — `bin/chrome-extension-settings-export` does not exist.

- [ ] **Step 3: Write the script skeleton**

Create `bin/chrome-extension-settings-export`:

```python
#!/usr/bin/env -S /opt/homebrew/bin/uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["plyvel"]
# ///
"""Export chrome.storage.local settings for manifest-tracked extensions.

Read-only: requires Chrome fully quit. Writes only to a staging directory —
never decides public vs. private placement, that's a manual step. See
docs/superpowers/specs/2026-07-02-chrome-extension-settings-export-design.md.
"""
import argparse
import json
import os
import pathlib
import sys
import tomllib

DEFAULT_CHROME_DIR = pathlib.Path.home() / "Library/Application Support/Google/Chrome"
DEFAULT_MANIFEST = pathlib.Path(__file__).resolve().parent.parent / "chrome" / "profiles.toml"
DEFAULT_OUT_DIR = (
    pathlib.Path(__file__).resolve().parent.parent
    / "chrome" / "extension-settings" / ".staging"
)


def load_manifest(path):
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def load_local_state(chrome_dir):
    path = pathlib.Path(chrome_dir) / "Local State"
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def email_to_dir(local_state):
    info_cache = local_state.get("profile", {}).get("info_cache", {})
    return {
        info.get("user_name"): dirname
        for dirname, info in info_cache.items()
        if info.get("user_name")
    }


def main(argv):
    parser = argparse.ArgumentParser(
        description="Export chrome.storage.local settings for manifest-tracked extensions to staged JSON."
    )
    parser.add_argument("--extension", action="append", help="limit to extension name; repeatable")
    parser.add_argument("--profile", action="append", help="limit to profile name; repeatable")
    args = parser.parse_args(argv)

    manifest_path = os.environ.get("CHROME_EXTENSION_EXPORT_MANIFEST", str(DEFAULT_MANIFEST))
    chrome_dir = os.environ.get("CHROME_EXTENSION_EXPORT_CHROME_DIR", str(DEFAULT_CHROME_DIR))
    out_dir = pathlib.Path(os.environ.get("CHROME_EXTENSION_EXPORT_OUT_DIR", str(DEFAULT_OUT_DIR)))

    try:
        manifest = load_manifest(manifest_path)
    except (FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        print(f"error: could not read manifest {manifest_path}: {exc}", file=sys.stderr)
        return 1

    try:
        local_state = load_local_state(chrome_dir)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"error: could not read chrome state in {chrome_dir}: {exc}", file=sys.stderr)
        return 1

    email_map = email_to_dir(local_state)
    profiles = manifest.get("profiles", {})
    extension_settings = manifest.get("extension_settings", [])

    extension_filter = set(args.extension) if args.extension else None
    profile_filter = set(args.profile) if args.profile else None

    for ext in extension_settings:
        if extension_filter and ext["name"] not in extension_filter:
            continue
        for profile_name in ext.get("profiles", []):
            if profile_filter and profile_name not in profile_filter:
                continue

            email = profiles.get(profile_name)
            if email is None:
                print(f"{ext['name']}/{profile_name}: profile not in manifest, skipping")
                continue

            dirname = email_map.get(email)
            if dirname is None:
                print(f"{ext['name']}/{profile_name}: profile not found on this machine, skipping")
                continue

            storage_dir = pathlib.Path(chrome_dir) / dirname / "Local Extension Settings" / ext["id"]
            if not storage_dir.is_dir():
                print(f"{ext['name']}/{profile_name}: not installed, skipping")
                continue

            # Actual export lands in Task 5.
            print(f"{ext['name']}/{profile_name}: found storage at {storage_dir} (export not yet implemented)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

Make it executable:

```bash
chmod +x bin/chrome-extension-settings-export
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/opt/homebrew/bin/uv run python3 -m unittest tests/test_chrome_extension_settings_export.py -v`
Expected: PASS (3 tests). Note: this invocation does NOT need `--with
plyvel` — these tests don't create any LevelDB fixtures, and the script
itself doesn't import `plyvel` yet (that's Task 5), even though the shebang
already declares the dependency.

- [ ] **Step 5: Commit**

```bash
git add bin/chrome-extension-settings-export tests/test_chrome_extension_settings_export.py
git commit -m "feat(chrome): add chrome-extension-settings-export skeleton"
```

---

## Task 5: LevelDB export and the locked-Chrome failure path

**Files:**
- Modify: `bin/chrome-extension-settings-export`
- Modify: `tests/test_chrome_extension_settings_export.py`

**From here on, every test run for this file needs `--with plyvel`** since
the tests now build real LevelDB fixtures:
`/opt/homebrew/bin/uv run --with plyvel python3 -m unittest tests/test_chrome_extension_settings_export.py -v`

- [ ] **Step 1: Write the failing tests**

Add `import plyvel` to the top of `tests/test_chrome_extension_settings_export.py`
(alongside the existing imports), then add this helper method to the
`ChromeExtensionSettingsExportTests` class:

```python
    def write_extension_storage(self, chrome_dir, dirname, ext_id, entries):
        """entries: dict of {key: raw bytes value}"""
        storage_dir = chrome_dir / dirname / "Local Extension Settings" / ext_id
        storage_dir.mkdir(parents=True, exist_ok=True)
        db = plyvel.DB(str(storage_dir), create_if_missing=True)
        for key, value in entries.items():
            db.put(key.encode("utf-8"), value)
        db.close()
        return storage_dir
```

Append these tests (before the final `if __name__ == "__main__":` block):

```python
    def test_exports_extension_storage_to_staging(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            out_dir = tmp / "out"
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            self.write_extension_storage(
                chrome_dir,
                "Default",
                "eimadpbcbfnmbkopoojfekhnkhdbieeh",
                {"enabled": b"true", "brightness": b"50"},
            )
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[extension_settings]]\n'
                'name = "Dark Reader"\n'
                'id = "eimadpbcbfnmbkopoojfekhnkhdbieeh"\n'
                'profiles = ["personal"]\n',
            )

            result = self.run_export(manifest, chrome_dir, out_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            dest = out_dir / "personal" / "eimadpbcbfnmbkopoojfekhnkhdbieeh.json"
            self.assertTrue(dest.exists())
            data = json.loads(dest.read_text())
            self.assertEqual(data, {"enabled": True, "brightness": 50})
            self.assertIn("wrote", result.stdout)

    def test_locked_database_is_reported_not_crashed(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            out_dir = tmp / "out"
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            storage_dir = self.write_extension_storage(
                chrome_dir, "Default", "eimadpbcbfnmbkopoojfekhnkhdbieeh", {"a": b"1"}
            )
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[extension_settings]]\n'
                'name = "Dark Reader"\n'
                'id = "eimadpbcbfnmbkopoojfekhnkhdbieeh"\n'
                'profiles = ["personal"]\n',
            )

            lock_holder = plyvel.DB(str(storage_dir), create_if_missing=False)
            try:
                result = self.run_export(manifest, chrome_dir, out_dir)
            finally:
                lock_holder.close()

            self.assertEqual(result.returncode, 1)
            self.assertIn("chrome still running", result.stderr.lower())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/opt/homebrew/bin/uv run --with plyvel python3 -m unittest tests/test_chrome_extension_settings_export.py -v`
Expected: FAIL — no LevelDB reading implemented yet.

- [ ] **Step 3: Implement the export**

In `bin/chrome-extension-settings-export`, add `import plyvel` to the
imports (alongside `tomllib`). Add this function above `main`:

```python
def export_extension(storage_dir):
    db = plyvel.DB(str(storage_dir), create_if_missing=False)
    try:
        data = {}
        for key, value in db:
            data[key.decode("utf-8", errors="replace")] = json.loads(value)
        return data
    finally:
        db.close()
```

Replace the placeholder line in `main`'s loop:

```python
            # Actual export lands in Task 5.
            print(f"{ext['name']}/{profile_name}: found storage at {storage_dir} (export not yet implemented)")
```

with:

```python
            try:
                data = export_extension(storage_dir)
            except OSError as exc:
                print(
                    f"error: {ext['name']}/{profile_name}: could not open storage "
                    f"(is Chrome still running? quit it and retry): {exc}",
                    file=sys.stderr,
                )
                had_lock_conflict = True
                continue

            dest_dir = out_dir / profile_name
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{ext['id']}.json"
            dest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
            print(f"{ext['name']}/{profile_name}: wrote {dest} ({len(data)} keys)")
```

Just above the `for ext in extension_settings:` loop, add:

```python
    had_lock_conflict = False
```

And change the function's final `return 0` to:

```python
    return 1 if had_lock_conflict else 0
```

Note: `json.loads(value)` here takes `value` (bytes) directly —
`json.loads` accepts `bytes` in Python 3.6+, decoding UTF-8 internally, so
no manual `.decode()` is needed before parsing. The base64 fallback for
non-JSON values is added in Task 6, not here.

- [ ] **Step 4: Run tests to verify they pass**

Run: `/opt/homebrew/bin/uv run --with plyvel python3 -m unittest tests/test_chrome_extension_settings_export.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add bin/chrome-extension-settings-export tests/test_chrome_extension_settings_export.py
git commit -m "feat(chrome): export extension storage via LevelDB, detect locked Chrome"
```

---

## Task 6: Non-JSON value fallback

**Files:**
- Modify: `bin/chrome-extension-settings-export`
- Modify: `tests/test_chrome_extension_settings_export.py`

- [ ] **Step 1: Write the failing test**

Add `import base64` to the test file's imports. Append this test:

```python
    def test_non_json_value_falls_back_to_base64(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            out_dir = tmp / "out"
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            raw_value = b"\xff\xfe not valid json or utf-8"
            self.write_extension_storage(
                chrome_dir,
                "Default",
                "eimadpbcbfnmbkopoojfekhnkhdbieeh",
                {"weird_key": raw_value},
            )
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[extension_settings]]\n'
                'name = "Dark Reader"\n'
                'id = "eimadpbcbfnmbkopoojfekhnkhdbieeh"\n'
                'profiles = ["personal"]\n',
            )

            result = self.run_export(manifest, chrome_dir, out_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            dest = out_dir / "personal" / "eimadpbcbfnmbkopoojfekhnkhdbieeh.json"
            data = json.loads(dest.read_text())
            self.assertEqual(
                base64.b64decode(data["weird_key"]["__raw_base64__"]), raw_value
            )
```

- [ ] **Step 2: Run tests to verify it fails**

Run: `/opt/homebrew/bin/uv run --with plyvel python3 -m unittest tests/test_chrome_extension_settings_export.py -v`
Expected: FAIL — `export_extension` currently calls `json.loads(value)`
directly with no fallback, so this raises `json.JSONDecodeError` and the
script crashes instead of degrading gracefully.

- [ ] **Step 3: Implement the fallback**

In `bin/chrome-extension-settings-export`, add `import base64` to the
imports. Add this function above `export_extension`:

```python
def decode_value(raw):
    try:
        return json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"__raw_base64__": base64.b64encode(raw).decode("ascii")}
```

In `export_extension`, change:

```python
            data[key.decode("utf-8", errors="replace")] = json.loads(value)
```

to:

```python
            data[key.decode("utf-8", errors="replace")] = decode_value(value)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/opt/homebrew/bin/uv run --with plyvel python3 -m unittest tests/test_chrome_extension_settings_export.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add bin/chrome-extension-settings-export tests/test_chrome_extension_settings_export.py
git commit -m "feat(chrome): fall back to base64 for non-JSON extension storage values"
```

---

## Task 7: `--extension`/`--profile` filters

**Files:**
- Modify: `tests/test_chrome_extension_settings_export.py` (no script changes expected — the filters were already implemented in Task 4's skeleton; this task verifies them)

- [ ] **Step 1: Write the tests**

Append these tests:

```python
    def test_extension_filter_limits_export(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            out_dir = tmp / "out"
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            self.write_extension_storage(
                chrome_dir, "Default", "eimadpbcbfnmbkopoojfekhnkhdbieeh", {"a": b"1"}
            )
            self.write_extension_storage(
                chrome_dir, "Default", "ddkjiahejlhfcafbddmgiahcphecmpfh", {"b": b"2"}
            )
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[extension_settings]]\n'
                'name = "Dark Reader"\n'
                'id = "eimadpbcbfnmbkopoojfekhnkhdbieeh"\n'
                'profiles = ["personal"]\n\n'
                '[[extension_settings]]\n'
                'name = "uBlock Origin Lite"\n'
                'id = "ddkjiahejlhfcafbddmgiahcphecmpfh"\n'
                'profiles = ["personal"]\n',
            )

            result = self.run_export(manifest, chrome_dir, out_dir, "--extension", "Dark Reader")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((out_dir / "personal" / "eimadpbcbfnmbkopoojfekhnkhdbieeh.json").exists())
            self.assertFalse((out_dir / "personal" / "ddkjiahejlhfcafbddmgiahcphecmpfh.json").exists())

    def test_profile_filter_limits_export(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            out_dir = tmp / "out"
            self.write_local_state(
                chrome_dir, {"Default": "personal@example.com", "Profile 1": "work@example.com"}
            )
            self.write_extension_storage(
                chrome_dir, "Default", "eimadpbcbfnmbkopoojfekhnkhdbieeh", {"a": b"1"}
            )
            self.write_extension_storage(
                chrome_dir, "Profile 1", "eimadpbcbfnmbkopoojfekhnkhdbieeh", {"a": b"2"}
            )
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "personal@example.com"\n'
                'dbtlabs = "work@example.com"\n\n'
                '[[extension_settings]]\n'
                'name = "Dark Reader"\n'
                'id = "eimadpbcbfnmbkopoojfekhnkhdbieeh"\n'
                'profiles = ["personal", "dbtlabs"]\n',
            )

            result = self.run_export(manifest, chrome_dir, out_dir, "--profile", "personal")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((out_dir / "personal" / "eimadpbcbfnmbkopoojfekhnkhdbieeh.json").exists())
            self.assertFalse((out_dir / "dbtlabs").exists())
```

- [ ] **Step 2: Run tests**

Run: `/opt/homebrew/bin/uv run --with plyvel python3 -m unittest tests/test_chrome_extension_settings_export.py -v`
Expected: PASS already (8 tests total) — the filters were built into Task
4's skeleton (`extension_filter`/`profile_filter` checks at the top of the
loop body) and haven't been touched since. This task is a regression guard,
not new functionality. If it fails, fix the filter checks in `main` to
compare against `ext["name"]` / `profile_name` as shown in Task 4's code.

- [ ] **Step 3: Commit**

```bash
git add tests/test_chrome_extension_settings_export.py
git commit -m "test(chrome): lock in --extension/--profile export filters"
```

---

## Task 8: Real manifest entries for the 6 tracked extensions

**Files:**
- Modify: `chrome/profiles.toml`

Extension IDs and current install footprint, confirmed by inspecting the
real `Secure Preferences` on this machine:

| Extension | ID | Installed in |
|---|---|---|
| uBlock Origin Lite | `ddkjiahejlhfcafbddmgiahcphecmpfh` | personal, dbtlabs |
| Dark Reader | `eimadpbcbfnmbkopoojfekhnkhdbieeh` | personal, dbtlabs, fivetran |
| 1Password | `aeblfdkhhhdcdjpifhhbdiojplfjncoa` | personal |
| Privacy Badger | `pkehgijcmpdhfbdbbnkijodmdjhbjlgp` | personal, dbtlabs |
| Reddit Enhancement Suite | `kbmfpngjjgdllneeigpgjifpgocmfgmb` | personal |
| Tab Wrangler | `egnjhciaieeiiohknchakcodbpgjnchh` | personal, dbtlabs |

List `profiles = ["personal", "dbtlabs", "fivetran"]` for all six entries
regardless of current install footprint (matching the existing
`[[extensions]]` table's philosophy of tracking *desired* scope, not just
today's snapshot) — the export script already skips cleanly with "not
installed, skipping" for any profile/extension combination that isn't
actually present.

- [ ] **Step 1: Add the entries**

Open `chrome/profiles.toml`. After the existing commented-out example block
(the `# [[extensions]]` / `# [[settings]]` comment lines), add:

```toml

[[extension_settings]]
name = "uBlock Origin Lite"
id = "ddkjiahejlhfcafbddmgiahcphecmpfh"
profiles = ["personal", "dbtlabs", "fivetran"]

[[extension_settings]]
name = "Dark Reader"
id = "eimadpbcbfnmbkopoojfekhnkhdbieeh"
profiles = ["personal", "dbtlabs", "fivetran"]

[[extension_settings]]
name = "1Password"
id = "aeblfdkhhhdcdjpifhhbdiojplfjncoa"
profiles = ["personal", "dbtlabs", "fivetran"]

[[extension_settings]]
name = "Privacy Badger"
id = "pkehgijcmpdhfbdbbnkijodmdjhbjlgp"
profiles = ["personal", "dbtlabs", "fivetran"]

[[extension_settings]]
name = "Reddit Enhancement Suite"
id = "kbmfpngjjgdllneeigpgjifpgocmfgmb"
profiles = ["personal", "dbtlabs", "fivetran"]

[[extension_settings]]
name = "Tab Wrangler"
id = "egnjhciaieeiiohknchakcodbpgjnchh"
profiles = ["personal", "dbtlabs", "fivetran"]
```

- [ ] **Step 2: Verify the manifest still parses correctly**

Run:

```bash
/opt/homebrew/bin/uv run python3 -c "
import tomllib
with open('chrome/profiles.toml', 'rb') as f:
    m = tomllib.load(f)
assert len(m['extension_settings']) == 6, m['extension_settings']
print('OK,', len(m['extension_settings']), 'extension_settings entries')
"
```

Expected: `OK, 6 extension_settings entries`

- [ ] **Step 3: Run the existing manifest test**

Run: `/opt/homebrew/bin/uv run python3 -m unittest tests/test_chrome_profiles_manifest.py -v`
Expected: still PASSES — that test only checks `[profiles]` and that
`extensions`/`settings` (not `extension_settings`) are empty, so it's
unaffected by this change.

- [ ] **Step 4: Do a real (but Chrome-must-be-quit) export as a smoke test**

Confirm Chrome is quit (`pgrep -x "Google Chrome"` prints nothing; if not,
quit it first). Then run:

```bash
/opt/homebrew/bin/uv run bin/chrome-extension-settings-export
```

Expected: prints a line per extension × profile combination — either
"wrote ... (N keys)" for ones actually installed, or "not installed,
skipping" for ones that aren't (per the table above, e.g. 1Password should
skip for dbtlabs and fivetran). Exit code 0. Check that
`chrome/extension-settings/.staging/` now has real files:

```bash
find chrome/extension-settings/.staging -type f
git status --porcelain chrome/
```

Expected: files exist under `.staging/`, but `git status` shows nothing
(confirms Task 3's gitignore entry is working end-to-end with real data,
not just the synthetic test from that task).

Leave these staged files in place — do not delete them and do not commit
them. They're for the user's own manual triage per the spec's §4 workflow,
which is outside this plan's scope (this plan builds the tool; the user
decides what to promote and where).

- [ ] **Step 5: Commit**

```bash
git add chrome/profiles.toml
git commit -m "feat(chrome): track 6 extensions for internal-settings export"
```

---

## Task 9: Document the new tool in `chrome/README.md`

**Files:**
- Modify: `chrome/README.md`

- [ ] **Step 1: Add a new section**

Open `chrome/README.md`. After the existing "## How it works" section (its
numbered list ends with the `--open-missing` bullet), add:

```markdown

## Exporting extension internal settings

`bin/chrome-extension-settings-export` is a separate, one-shot backup tool
— not part of the drift-check above. It reads an extension's own
`chrome.storage.local` data directly from its LevelDB storage (this is
undocumented, internal Chrome format, treated as best-effort) and writes it
to a gitignored staging directory, for restoring onto a new machine or
profile later.

**Requires Chrome fully quit.** The extension's storage is locked while
Chrome runs; the script detects this (rather than guessing) by trying to
open the database and reporting a clear error if it's still locked.

Run: `bin/chrome-extension-settings-export` (optionally `--extension NAME`
/ `--profile NAME` to limit scope). Output lands in
`chrome/extension-settings/.staging/<profile>/<id>.json` — never directly
in a committed location.

**Promotion is always a manual step**, since this repo is public and we
don't know what a given extension actually stores until we look:

1. Open each staged JSON file and check for anything that looks like a
   session token, device ID, or other account-adjacent secret (most likely
   candidate among the tracked extensions: 1Password).
2. If a committed version already exists at
   `chrome/extension-settings/<profile>/<id>.json`, diff the staged copy
   against it before overwriting — a later export surfacing something newly
   sensitive must not silently replace a file already known to be safe.
3. Move the file to `chrome/extension-settings/<profile>/<id>.json` (public)
   or `~/Developer/dotfiles_env/chrome/extension-settings/<profile>/<id>.json`
   (private) if anything looked sensitive, then commit from whichever repo
   it landed in.

Import/restore isn't built yet — writing back into a live LevelDB is
riskier than reading one and is deferred until actually needed.
```

- [ ] **Step 2: Proofread against the actual script behavior**

Re-read `bin/chrome-extension-settings-export` and confirm every claim in
the new README section matches what the code actually does (flag names,
output path, the "not installed" vs. "locked" distinction). Fix any
mismatch before committing.

- [ ] **Step 3: Commit**

```bash
git add chrome/README.md
git commit -m "docs(chrome): document chrome-extension-settings-export"
```

---

## Final check

- [ ] Run the full test suite: `/opt/homebrew/bin/uv run --with plyvel python3 -m unittest discover tests -v`
  Expected: all tests pass except the pre-existing, unrelated
  `test_shadowtraffic_clickhouse.py` failures (confirmed unrelated to this
  work in the prior feature's final review).
- [ ] Confirm `git status` is clean except for the intentional, gitignored
  `chrome/extension-settings/.staging/` contents from Task 8's smoke test.
- [ ] Remind the user: the staged exports from Task 8 are sitting in
  `chrome/extension-settings/.staging/` waiting for their manual review —
  this plan does not promote or commit any of them.

# Chrome multi-profile extension/settings sync — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Also see @superpowers:test-driven-development for how each task's write-test-first steps should be run.

**Goal:** Build `chrome/profiles.toml` (manifest) and `bin/chrome-sync-check` (read-only drift report + best-effort extension-install helper) so the user can keep extensions/settings consistent across their 3 Chrome profiles (personal, dbt Labs, Fivetran).

**Architecture:** A single Python script (`bin/chrome-sync-check`, `uv run python3` shebang, no third-party deps — `tomllib` is stdlib on the repo's Python 3.12) reads the TOML manifest and Chrome's own `Local State` + per-profile `Preferences` JSON files read-only, diffs them, and prints a per-profile report. `--open-missing` additionally shells out to `open` to launch Chrome Web Store pages for missing extensions. Every external dependency (manifest path, Chrome's user-data dir, the `open` binary) is overridable via env vars so tests never touch the real `~/Library/Application Support/Google/Chrome`, following the existing pattern in `bin/github-notification-sweep` (`GH_NOTIFICATION_SWEEP_GH` override) and `tests/test_github_notification_sweep.py` (subprocess black-box tests with a fake binary).

**Tech Stack:** Python 3.12 stdlib only (`argparse`, `json`, `tomllib`, `subprocess`, `pathlib`), `unittest` + `subprocess` for black-box tests (matching `tests/test_serena_link.py` / `tests/test_github_notification_sweep.py` conventions).

**Spec:** `docs/superpowers/specs/2026-07-02-chrome-profile-sync-design.md` — read this first for the *why* (Jamf-managed policy layer, Chrome's tamper-protected `Preferences`, no safe write path) if anything below seems unnecessarily indirect.

---

## Task 1: Manifest file

**Files:**
- Create: `chrome/profiles.toml`
- Test: `tests/test_chrome_profiles_manifest.py`

- [ ] **Step 1: Write the failing test**

```python
import pathlib
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "chrome" / "profiles.toml"


class ChromeProfilesManifestTests(unittest.TestCase):
    def test_parses_and_has_expected_profiles(self):
        with open(MANIFEST, "rb") as fh:
            manifest = tomllib.load(fh)

        self.assertEqual(
            manifest["profiles"],
            {
                "personal": "swanson.anders@gmail.com",
                "dbtlabs": "anders.swanson@dbtlabs.com",
                "fivetran": "anders.swanson@fivetran.com",
            },
        )
        # Empty until the user opts specific extensions/settings in.
        self.assertEqual(manifest.get("extensions", []), [])
        self.assertEqual(manifest.get("settings", []), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/homebrew/bin/uv run python3 -m unittest tests/test_chrome_profiles_manifest.py -v`
Expected: FAIL — `chrome/profiles.toml` does not exist (`FileNotFoundError`).

- [ ] **Step 3: Write the manifest**

Create `chrome/profiles.toml`:

```toml
# Source of truth for keeping extensions/settings consistent across Chrome
# profiles. bin/chrome-sync-check reads this file read-only and never
# writes to it or to Chrome's own state.
#
# See chrome/README.md and
# docs/superpowers/specs/2026-07-02-chrome-profile-sync-design.md for the
# full design and why this can't just be a synced Preferences file.

[profiles]
personal = "swanson.anders@gmail.com"
dbtlabs  = "anders.swanson@dbtlabs.com"
fivetran = "anders.swanson@fivetran.com"

# Add entries as you decide what should be synced, e.g.:
#
# [[extensions]]
# name = "uBlock Origin"
# id = "cjpalhdlnbpafiamejdnhcphjbkeiagm"
# profiles = ["personal", "dbtlabs", "fivetran"]
#
# [[settings]]
# name = "Always show bookmarks bar"
# pref_path = "bookmark_bar.show_on_all_tabs"
# value = true
# profiles = ["personal", "dbtlabs", "fivetran"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/homebrew/bin/uv run python3 -m unittest tests/test_chrome_profiles_manifest.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add chrome/profiles.toml tests/test_chrome_profiles_manifest.py
git commit -m "feat(chrome): add profiles.toml manifest for extension/settings sync"
```

---

## Task 2: Script skeleton — config loading and error handling

**Files:**
- Create: `bin/chrome-sync-check`
- Create: `tests/test_chrome_sync_check.py`

This task establishes the CLI, env-var overrides, and the two hard-failure
cases (missing manifest, missing `Local State`). No extension/settings diff
logic yet — that's Tasks 3–4.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_chrome_sync_check.py`:

```python
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "chrome-sync-check"


class ChromeSyncCheckTests(unittest.TestCase):
    def write_local_state(self, chrome_dir, profile_emails):
        """profile_emails: dict of {dirname: email}"""
        info_cache = {
            dirname: {"user_name": email} for dirname, email in profile_emails.items()
        }
        (chrome_dir / "Local State").write_text(
            json.dumps({"profile": {"info_cache": info_cache}})
        )

    def write_preferences(self, chrome_dir, dirname, prefs):
        profile_dir = chrome_dir / dirname
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "Preferences").write_text(json.dumps(prefs))

    def write_manifest(self, root, text):
        manifest_path = root / "profiles.toml"
        manifest_path.write_text(text)
        return manifest_path

    def run_check(self, manifest_path, chrome_dir, *extra, open_bin=None):
        env = os.environ.copy()
        env.update(
            {
                "CHROME_SYNC_CHECK_MANIFEST": str(manifest_path),
                "CHROME_SYNC_CHECK_CHROME_DIR": str(chrome_dir),
            }
        )
        if open_bin is not None:
            env["CHROME_SYNC_CHECK_OPEN"] = str(open_bin)
        return subprocess.run(
            [str(SCRIPT), *extra],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_missing_manifest_is_a_hard_failure(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            self.write_local_state(chrome_dir, {})

            result = self.run_check(tmp / "does-not-exist.toml", chrome_dir)

            self.assertEqual(result.returncode, 1)
            self.assertIn("manifest", result.stderr.lower())

    def test_missing_local_state_is_a_hard_failure(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            manifest = self.write_manifest(tmp, "[profiles]\n")

            result = self.run_check(manifest, chrome_dir)

            self.assertEqual(result.returncode, 1)
            self.assertIn("chrome state", result.stderr.lower())

    def test_empty_manifest_profiles_exits_clean(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            self.write_local_state(chrome_dir, {})
            manifest = self.write_manifest(tmp, "[profiles]\n")

            result = self.run_check(manifest, chrome_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/opt/homebrew/bin/uv run python3 -m unittest tests/test_chrome_sync_check.py -v`
Expected: FAIL — `bin/chrome-sync-check` does not exist.

- [ ] **Step 3: Write the script skeleton**

Create `bin/chrome-sync-check`:

```python
#!/usr/bin/env -S /opt/homebrew/bin/uv run python3
"""Report drift between chrome/profiles.toml and installed Chrome extensions/settings.

Read-only: never writes to Chrome's Preferences or policy files. See
docs/superpowers/specs/2026-07-02-chrome-profile-sync-design.md for why.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import tomllib

DEFAULT_CHROME_DIR = pathlib.Path.home() / "Library/Application Support/Google/Chrome"
DEFAULT_MANIFEST = pathlib.Path(__file__).resolve().parent.parent / "chrome" / "profiles.toml"
DEFAULT_OPEN = "open"


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


def build_report(manifest, chrome_dir):
    profiles = manifest.get("profiles", {})

    local_state = load_local_state(chrome_dir)
    email_map = email_to_dir(local_state)

    lines = []
    open_targets = []

    for name, email in profiles.items():
        dirname = email_map.get(email)
        if dirname is None:
            lines.append(f"{name}: profile not found on this machine (email {email})")
            continue
        # Extension/settings diffing lands in later tasks; for now every
        # resolved profile reports in sync.
        lines.append(f"{name}: in sync")

    return lines, open_targets


def main(argv):
    parser = argparse.ArgumentParser(
        description="Report drift between chrome/profiles.toml and installed Chrome extensions/settings."
    )
    parser.add_argument(
        "--open-missing",
        action="store_true",
        help=(
            "open the Chrome Web Store listing for each missing extension in its "
            "target profile. Best-effort: verify it lands on the right profile "
            "before relying on it while other profiles are open (see the design spec)."
        ),
    )
    args = parser.parse_args(argv)

    manifest_path = os.environ.get("CHROME_SYNC_CHECK_MANIFEST", str(DEFAULT_MANIFEST))
    chrome_dir = os.environ.get("CHROME_SYNC_CHECK_CHROME_DIR", str(DEFAULT_CHROME_DIR))
    open_bin = os.environ.get("CHROME_SYNC_CHECK_OPEN", DEFAULT_OPEN)

    try:
        manifest = load_manifest(manifest_path)
    except (FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        print(f"error: could not read manifest {manifest_path}: {exc}", file=sys.stderr)
        return 1

    try:
        lines, open_targets = build_report(manifest, chrome_dir)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"error: could not read chrome state in {chrome_dir}: {exc}", file=sys.stderr)
        return 1

    print("\n".join(lines))

    if args.open_missing and open_targets:
        pass  # wired up in Task 6

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

Make it executable:

```bash
chmod +x bin/chrome-sync-check
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/opt/homebrew/bin/uv run python3 -m unittest tests/test_chrome_sync_check.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add bin/chrome-sync-check tests/test_chrome_sync_check.py
git commit -m "feat(chrome): add chrome-sync-check skeleton with config loading"
```

---

## Task 3: Extension diffing

**Files:**
- Modify: `bin/chrome-sync-check`
- Modify: `tests/test_chrome_sync_check.py`

- [ ] **Step 1: Write the failing tests**

Append to the `ChromeSyncCheckTests` class in `tests/test_chrome_sync_check.py`:

```python
    def test_missing_extension_is_reported(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            self.write_preferences(chrome_dir, "Default", {"extensions": {"settings": {}}})
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[extensions]]\n'
                'name = "uBlock Origin"\n'
                'id = "cjpalhdlnbpafiamejdnhcphjbkeiagm"\n'
                'profiles = ["personal"]\n',
            )

            result = self.run_check(manifest, chrome_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("personal (me@example.com):", result.stdout)
            self.assertIn(
                "missing extensions:    uBlock Origin (cjpalhdlnbpafiamejdnhcphjbkeiagm)",
                result.stdout,
            )

    def test_installed_extension_is_in_sync(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            self.write_preferences(
                chrome_dir,
                "Default",
                {"extensions": {"settings": {"cjpalhdlnbpafiamejdnhcphjbkeiagm": {}}}},
            )
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[extensions]]\n'
                'name = "uBlock Origin"\n'
                'id = "cjpalhdlnbpafiamejdnhcphjbkeiagm"\n'
                'profiles = ["personal"]\n',
            )

            result = self.run_check(manifest, chrome_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("personal: in sync", result.stdout)

    def test_untracked_extension_uses_manifest_name_when_available(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            self.write_preferences(
                chrome_dir,
                "Default",
                {
                    "extensions": {
                        "settings": {
                            "abcabcabcabcabcabcabcabcabcabca": {
                                "manifest": {"name": "Grammarly"}
                            }
                        }
                    }
                },
            )
            manifest = self.write_manifest(tmp, '[profiles]\npersonal = "me@example.com"\n')

            result = self.run_check(manifest, chrome_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(
                "untracked extensions:  Grammarly (abcabcabcabcabcabcabcabcabcabca)",
                result.stdout,
            )

    def test_untracked_extension_falls_back_to_id_without_manifest_name(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            self.write_preferences(
                chrome_dir,
                "Default",
                {"extensions": {"settings": {"abcabcabcabcabcabcabcabcabcabca": {}}}},
            )
            manifest = self.write_manifest(tmp, '[profiles]\npersonal = "me@example.com"\n')

            result = self.run_check(manifest, chrome_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(
                "untracked extensions:  abcabcabcabcabcabcabcabcabcabca", result.stdout
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/opt/homebrew/bin/uv run python3 -m unittest tests/test_chrome_sync_check.py -v`
Expected: FAIL — new assertions don't match (no extension diffing yet).

- [ ] **Step 3: Implement extension diffing**

In `bin/chrome-sync-check`, add these functions above `build_report`:

```python
def load_preferences(chrome_dir, dirname):
    path = pathlib.Path(chrome_dir) / dirname / "Preferences"
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}


def installed_extensions(prefs):
    return set(prefs.get("extensions", {}).get("settings", {}).keys())


def extension_display_name(prefs, ext_id):
    entry = prefs.get("extensions", {}).get("settings", {}).get(ext_id, {})
    name = entry.get("manifest", {}).get("name")
    if name and not name.startswith("__MSG_"):
        return f"{name} ({ext_id})"
    return ext_id


def diff_extensions(prefs, extensions, profile_name):
    installed = installed_extensions(prefs)
    scoped = [ext for ext in extensions if profile_name in ext.get("profiles", [])]
    missing = [ext for ext in scoped if ext["id"] not in installed]
    tracked_ids = {ext["id"] for ext in scoped}
    untracked = sorted(installed - tracked_ids)
    return missing, untracked
```

Replace `build_report` with:

```python
def build_report(manifest, chrome_dir):
    profiles = manifest.get("profiles", {})
    extensions = manifest.get("extensions", [])

    local_state = load_local_state(chrome_dir)
    email_map = email_to_dir(local_state)

    lines = []
    open_targets = []

    for name, email in profiles.items():
        dirname = email_map.get(email)
        if dirname is None:
            lines.append(f"{name}: profile not found on this machine (email {email})")
            continue

        prefs = load_preferences(chrome_dir, dirname)
        missing, untracked = diff_extensions(prefs, extensions, name)

        if not missing and not untracked:
            lines.append(f"{name}: in sync")
            continue

        lines.append(f"{name} ({email}):")
        if missing:
            rendered = ", ".join(f"{ext['name']} ({ext['id']})" for ext in missing)
            lines.append(f"  missing extensions:    {rendered}")
            open_targets.extend((dirname, ext) for ext in missing)
        if untracked:
            rendered = ", ".join(extension_display_name(prefs, ext_id) for ext_id in untracked)
            lines.append(f"  untracked extensions:  {rendered}")

    return lines, open_targets
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/opt/homebrew/bin/uv run python3 -m unittest tests/test_chrome_sync_check.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add bin/chrome-sync-check tests/test_chrome_sync_check.py
git commit -m "feat(chrome): diff installed vs. manifest extensions per profile"
```

---

## Task 4: Settings diffing

**Files:**
- Modify: `bin/chrome-sync-check`
- Modify: `tests/test_chrome_sync_check.py`

- [ ] **Step 1: Write the failing tests**

Append to `ChromeSyncCheckTests`:

```python
    def test_unset_setting_is_reported(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            self.write_preferences(chrome_dir, "Default", {})
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[settings]]\n'
                'name = "Always show bookmarks bar"\n'
                'pref_path = "bookmark_bar.show_on_all_tabs"\n'
                'value = true\n'
                'profiles = ["personal"]\n',
            )

            result = self.run_check(manifest, chrome_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(
                "setting mismatches:    Always show bookmarks bar (want true, got unset)",
                result.stdout,
            )

    def test_wrong_value_setting_is_reported(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            self.write_preferences(
                chrome_dir, "Default", {"bookmark_bar": {"show_on_all_tabs": False}}
            )
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[settings]]\n'
                'name = "Always show bookmarks bar"\n'
                'pref_path = "bookmark_bar.show_on_all_tabs"\n'
                'value = true\n'
                'profiles = ["personal"]\n',
            )

            result = self.run_check(manifest, chrome_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(
                "setting mismatches:    Always show bookmarks bar (want true, got false)",
                result.stdout,
            )

    def test_matching_setting_is_in_sync(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            self.write_preferences(
                chrome_dir, "Default", {"bookmark_bar": {"show_on_all_tabs": True}}
            )
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[settings]]\n'
                'name = "Always show bookmarks bar"\n'
                'pref_path = "bookmark_bar.show_on_all_tabs"\n'
                'value = true\n'
                'profiles = ["personal"]\n',
            )

            result = self.run_check(manifest, chrome_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("personal: in sync", result.stdout)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/opt/homebrew/bin/uv run python3 -m unittest tests/test_chrome_sync_check.py -v`
Expected: FAIL — no settings diffing yet.

- [ ] **Step 3: Implement settings diffing**

In `bin/chrome-sync-check`, add above `build_report`:

```python
def get_pref_path(prefs, pref_path):
    node = prefs
    for part in pref_path.split("."):
        if not isinstance(node, dict) or part not in node:
            return False, None
        node = node[part]
    return True, node


def diff_settings(prefs, settings, profile_name):
    mismatches = []
    for setting in settings:
        if profile_name not in setting.get("profiles", []):
            continue
        found, actual = get_pref_path(prefs, setting["pref_path"])
        want = json.dumps(setting["value"])
        if not found:
            mismatches.append(f"{setting['name']} (want {want}, got unset)")
        elif actual != setting["value"]:
            mismatches.append(f"{setting['name']} (want {want}, got {json.dumps(actual)})")
    return mismatches
```

In `build_report`, add `settings = manifest.get("settings", [])` next to the
`extensions = ...` line, compute `mismatches = diff_settings(prefs, settings, name)`
right after `missing, untracked = diff_extensions(...)`, include it in the
in-sync check (`if not missing and not untracked and not mismatches:`), and
after the `untracked` block add:

```python
        if mismatches:
            lines.append(f"  setting mismatches:    {', '.join(mismatches)}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/opt/homebrew/bin/uv run python3 -m unittest tests/test_chrome_sync_check.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add bin/chrome-sync-check tests/test_chrome_sync_check.py
git commit -m "feat(chrome): diff settings against manifest with strict value comparison"
```

---

## Task 5: Multi-profile ordering and "not found" handling

**Files:**
- Modify: `tests/test_chrome_sync_check.py` (no script changes expected — this task verifies existing behavior; if it fails, fix `build_report` to preserve manifest order, which `tomllib` + `dict` already guarantee)

- [ ] **Step 1: Write the failing test**

Append to `ChromeSyncCheckTests`:

```python
    def test_multi_profile_report_preserves_manifest_order_and_flags_missing_profile(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            self.write_local_state(
                chrome_dir,
                {"Default": "personal@example.com", "Profile 1": "work@example.com"},
            )
            self.write_preferences(chrome_dir, "Default", {})
            self.write_preferences(chrome_dir, "Profile 1", {})
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'fivetran = "notonthismachine@example.com"\n'
                'personal = "personal@example.com"\n'
                'dbtlabs = "work@example.com"\n',
            )

            result = self.run_check(manifest, chrome_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            lines = [l for l in result.stdout.splitlines() if l]
            self.assertEqual(
                lines,
                [
                    "fivetran: profile not found on this machine (email notonthismachine@example.com)",
                    "personal: in sync",
                    "dbtlabs: in sync",
                ],
            )
```

- [ ] **Step 2: Run test**

Run: `/opt/homebrew/bin/uv run python3 -m unittest tests/test_chrome_sync_check.py -v`
Expected: PASS already, since `tomllib` preserves table-array/table declaration
order into a regular `dict` and Python dicts preserve insertion order — this
test is a regression guard, not new functionality. If it fails, the fix is to
ensure `build_report` iterates `profiles.items()` directly (it already does)
rather than e.g. sorting keys.

- [ ] **Step 3: Commit**

```bash
git add tests/test_chrome_sync_check.py
git commit -m "test(chrome): lock in manifest-order + not-found profile reporting"
```

---

## Task 6: `--open-missing`

**Files:**
- Modify: `bin/chrome-sync-check`
- Modify: `tests/test_chrome_sync_check.py`

Per the spec, the exact `open` invocation that reliably targets a specific
profile while Chrome is already running is **unverified** — this task wires
up the current best-known approach (`open -n -a "Google Chrome" --args
--profile-directory=... <url>`) behind the `CHROME_SYNC_CHECK_OPEN`
override, and the test only checks that chrome-sync-check *invokes* the
configured binary with the right arguments — not that Chrome itself opens
the right window (that requires manual verification on the real machine,
called out in the spec and in this task's last step).

- [ ] **Step 1: Write the failing test**

Append to `ChromeSyncCheckTests`:

```python
    def test_open_missing_invokes_open_binary_per_missing_extension(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            self.write_preferences(chrome_dir, "Default", {"extensions": {"settings": {}}})
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[extensions]]\n'
                'name = "uBlock Origin"\n'
                'id = "cjpalhdlnbpafiamejdnhcphjbkeiagm"\n'
                'profiles = ["personal"]\n',
            )

            fake_open = tmp / "fake-open"
            log = tmp / "open.log"
            fake_open.write_text(
                "#!/usr/bin/env bash\n"
                'printf "%s\\n" "$*" >> "' + str(log) + '"\n'
            )
            fake_open.chmod(0o755)

            result = self.run_check(manifest, chrome_dir, "--open-missing", open_bin=fake_open)

            self.assertEqual(result.returncode, 0, result.stderr)
            logged = log.read_text()
            self.assertIn("-n -a Google Chrome --args --profile-directory=Default", logged)
            self.assertIn(
                "https://chromewebstore.google.com/detail/cjpalhdlnbpafiamejdnhcphjbkeiagm",
                logged,
            )

    def test_no_open_missing_flag_does_not_invoke_open_binary(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            self.write_preferences(chrome_dir, "Default", {"extensions": {"settings": {}}})
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[extensions]]\n'
                'name = "uBlock Origin"\n'
                'id = "cjpalhdlnbpafiamejdnhcphjbkeiagm"\n'
                'profiles = ["personal"]\n',
            )
            fake_open = tmp / "fake-open"
            log = tmp / "open.log"
            fake_open.write_text(
                "#!/usr/bin/env bash\n"
                'printf "%s\\n" "$*" >> "' + str(log) + '"\n'
            )
            fake_open.chmod(0o755)

            result = self.run_check(manifest, chrome_dir, open_bin=fake_open)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(log.exists())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/opt/homebrew/bin/uv run python3 -m unittest tests/test_chrome_sync_check.py -v`
Expected: FAIL — `--open-missing` currently does nothing (`pass` placeholder from Task 2).

- [ ] **Step 3: Implement `open_missing` and wire it up**

In `bin/chrome-sync-check`, add above `main`:

```python
def open_missing(open_targets, open_bin):
    for dirname, ext in open_targets:
        # URL pattern is unverified (see spec §3 and Step 6 below) — the
        # /detail/<id> path has historically worked without needing the
        # slugged name, but confirm it resolves before relying on it.
        url = f"https://chromewebstore.google.com/detail/{ext['id']}"
        subprocess.run(
            [open_bin, "-n", "-a", "Google Chrome", "--args", f"--profile-directory={dirname}", url],
            check=False,
        )
```

In `main`, replace:

```python
    if args.open_missing and open_targets:
        pass  # wired up in Task 6
```

with:

```python
    if args.open_missing and open_targets:
        open_missing(open_targets, open_bin)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/opt/homebrew/bin/uv run python3 -m unittest tests/test_chrome_sync_check.py -v`
Expected: PASS (13 tests)

- [ ] **Step 5: Commit**

```bash
git add bin/chrome-sync-check tests/test_chrome_sync_check.py
git commit -m "feat(chrome): add --open-missing to launch Web Store pages for missing extensions"
```

- [ ] **Step 6: Manual verification (not automatable — do this yourself on the real machine)**

Two things are unverified assumptions in this task's implementation, not
confirmed facts — both need checking together, since a failure could come
from either one:

1. The Web Store URL pattern `https://chromewebstore.google.com/detail/<id>`
   actually resolves to the extension's listing (no slug/name segment
   required).
2. The `open`/`--profile-directory` mechanism actually lands the tab in the
   correct profile's window rather than the currently-focused one.

Add one real, low-risk extension entry to `chrome/profiles.toml` temporarily
(or use an existing one you don't mind reinstalling), run
`bin/chrome-sync-check --open-missing` with **all three Chrome profile
windows already open**, and confirm both: the URL loads the right listing,
and it opens in the correct profile's window rather than the
currently-focused one. If either fails, per the spec's fallback: don't
chase further workarounds automatically — note the failure and downgrade `--open-missing`
to printing the URL + profile name instead of invoking `open` (a small
follow-up change, not part of this plan). Remove the temporary manifest
entry afterward if you added one.

---

## Final check

- [ ] Run the full test suite once more: `/opt/homebrew/bin/uv run python3 -m unittest discover tests -v`
  Expected: all tests pass, including the pre-existing `test_links.py`,
  `test_serena_link.py`, `test_github_notification_sweep.py`, and
  `test_shadowtraffic_clickhouse.py`.
- [ ] Confirm `bin/chrome-sync-check` (no args, no env overrides) runs
  cleanly against your real Chrome profiles and reports `in sync` for all
  three (manifest currently has no extensions/settings entries, so this
  should be a no-op report).

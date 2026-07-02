import fcntl
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

    def fake_leveldbutil(self, tmp):
        """A fake `leveldbutil dump <file>` that cats a sibling `<file>.dump`
        fixture instead of actually reading LevelDB files -- lets tests
        supply arbitrary dump-format text without needing a real LevelDB
        writer available."""
        script = tmp / "fake-leveldbutil"
        script.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            'if [[ "$1" != "dump" ]]; then\n'
            '  echo "unexpected leveldbutil invocation: $*" >&2\n'
            "  exit 1\n"
            "fi\n"
            'cat "$2.dump"\n'
        )
        script.chmod(0o755)
        return script

    def write_storage_file(self, storage_dir, filename, dump_text):
        """Creates an (empty, content-irrelevant) .log/.ldb file plus its
        `.dump` fixture consumed by fake_leveldbutil, and a real LOCK file
        so check_not_locked has something to open."""
        storage_dir.mkdir(parents=True, exist_ok=True)
        (storage_dir / filename).write_text("")
        (storage_dir / f"{filename}.dump").write_text(dump_text)
        lock_path = storage_dir / "LOCK"
        if not lock_path.exists():
            lock_path.write_text("")

    def run_export(self, manifest_path, chrome_dir, out_dir, *extra, leveldbutil=None):
        env = os.environ.copy()
        env.update(
            {
                "CHROME_EXTENSION_EXPORT_MANIFEST": str(manifest_path),
                "CHROME_EXTENSION_EXPORT_CHROME_DIR": str(chrome_dir),
                "CHROME_EXTENSION_EXPORT_OUT_DIR": str(out_dir),
            }
        )
        if leveldbutil is not None:
            env["CHROME_EXTENSION_EXPORT_LEVELDBUTIL"] = str(leveldbutil)
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
                'name = "Tab Wrangler"\n'
                'id = "egnjhciaieeiiohknchakcodbpgjnchh"\n'
                'storage = "sync"\n'
                'keys = ["maxTabs"]\n'
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
                'name = "Tab Wrangler"\n'
                'id = "egnjhciaieeiiohknchakcodbpgjnchh"\n'
                'storage = "sync"\n'
                'keys = ["maxTabs"]\n'
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

    def test_exports_allowlisted_keys_from_log_dump_only(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            out_dir = tmp / "out"
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            fake = self.fake_leveldbutil(tmp)

            storage_dir = (
                chrome_dir / "Default" / "Sync Extension Settings"
                / "egnjhciaieeiiohknchakcodbpgjnchh"
            )
            self.write_storage_file(
                storage_dir,
                "000001.log",
                "--- offset 0; sequence 10\n"
                "  put 'maxTabs' '8'\n"
                "  put 'tabTimes' '{\"1\": 123}'\n"
                "  put 'whitelist' '[\"example.com\"]'\n"
                "  del 'whitelist'\n",
            )
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[extension_settings]]\n'
                'name = "Tab Wrangler"\n'
                'id = "egnjhciaieeiiohknchakcodbpgjnchh"\n'
                'storage = "sync"\n'
                'keys = ["maxTabs", "whitelist"]\n'
                'profiles = ["personal"]\n',
            )

            result = self.run_export(manifest, chrome_dir, out_dir, leveldbutil=fake)

            self.assertEqual(result.returncode, 0, result.stderr)
            dest = out_dir / "personal" / "egnjhciaieeiiohknchakcodbpgjnchh.json"
            data = json.loads(dest.read_text())
            # tabTimes isn't in the allowlist -- excluded even though present.
            # whitelist was put then deleted in the same file -- excluded.
            self.assertEqual(data, {"maxTabs": 8})

    def test_merges_ldb_and_log_by_global_sequence(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            out_dir = tmp / "out"
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            fake = self.fake_leveldbutil(tmp)

            storage_dir = (
                chrome_dir / "Default" / "Local Extension Settings"
                / "kbmfpngjjgdllneeigpgjifpgocmfgmb"
            )
            # .ldb represents older, already-compacted state (lower sequence).
            self.write_storage_file(
                storage_dir,
                "000001.ldb",
                "'RESoptions.hover' @ 5 : val => 'false'\n"
                "'RESoptions.notifications' @ 6 : val => 'true'\n",
            )
            # .log has a newer write (higher sequence) overriding one key.
            self.write_storage_file(
                storage_dir,
                "000002.log",
                "--- offset 0; sequence 20\n"
                "  put 'RESoptions.hover' 'true'\n",
            )
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[extension_settings]]\n'
                'name = "Reddit Enhancement Suite"\n'
                'id = "kbmfpngjjgdllneeigpgjifpgocmfgmb"\n'
                'storage = "local"\n'
                'keys = ["RESoptions.hover", "RESoptions.notifications"]\n'
                'profiles = ["personal"]\n',
            )

            result = self.run_export(manifest, chrome_dir, out_dir, leveldbutil=fake)

            self.assertEqual(result.returncode, 0, result.stderr)
            dest = out_dir / "personal" / "kbmfpngjjgdllneeigpgjifpgocmfgmb.json"
            data = json.loads(dest.read_text())
            # hover: the .log's later (higher-sequence) write wins over .ldb.
            self.assertEqual(data, {"RESoptions.hover": True, "RESoptions.notifications": True})

    def test_non_json_value_falls_back_to_raw_text(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            out_dir = tmp / "out"
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            fake = self.fake_leveldbutil(tmp)

            storage_dir = (
                chrome_dir / "Default" / "Sync Extension Settings"
                / "egnjhciaieeiiohknchakcodbpgjnchh"
            )
            self.write_storage_file(
                storage_dir,
                "000001.log",
                "--- offset 0; sequence 1\n"
                "  put 'weird' 'not valid json'\n",
            )
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[extension_settings]]\n'
                'name = "Tab Wrangler"\n'
                'id = "egnjhciaieeiiohknchakcodbpgjnchh"\n'
                'storage = "sync"\n'
                'keys = ["weird"]\n'
                'profiles = ["personal"]\n',
            )

            result = self.run_export(manifest, chrome_dir, out_dir, leveldbutil=fake)

            self.assertEqual(result.returncode, 0, result.stderr)
            dest = out_dir / "personal" / "egnjhciaieeiiohknchakcodbpgjnchh.json"
            data = json.loads(dest.read_text())
            self.assertEqual(data, {"weird": {"__raw_text__": "not valid json"}})

    def test_sync_storage_type_reads_sync_extension_settings_dir(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            out_dir = tmp / "out"
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            fake = self.fake_leveldbutil(tmp)

            # Put a matching directory under "Local" too, to prove the
            # script reads "Sync" specifically when storage = "sync".
            local_dir = (
                chrome_dir / "Default" / "Local Extension Settings"
                / "egnjhciaieeiiohknchakcodbpgjnchh"
            )
            self.write_storage_file(
                local_dir, "000001.log",
                "--- offset 0; sequence 1\n  put 'maxTabs' '999'\n",
            )
            sync_dir = (
                chrome_dir / "Default" / "Sync Extension Settings"
                / "egnjhciaieeiiohknchakcodbpgjnchh"
            )
            self.write_storage_file(
                sync_dir, "000001.log",
                "--- offset 0; sequence 1\n  put 'maxTabs' '8'\n",
            )
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[extension_settings]]\n'
                'name = "Tab Wrangler"\n'
                'id = "egnjhciaieeiiohknchakcodbpgjnchh"\n'
                'storage = "sync"\n'
                'keys = ["maxTabs"]\n'
                'profiles = ["personal"]\n',
            )

            result = self.run_export(manifest, chrome_dir, out_dir, leveldbutil=fake)

            self.assertEqual(result.returncode, 0, result.stderr)
            dest = out_dir / "personal" / "egnjhciaieeiiohknchakcodbpgjnchh.json"
            data = json.loads(dest.read_text())
            self.assertEqual(data, {"maxTabs": 8})

    def test_locked_storage_is_reported_not_crashed(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            out_dir = tmp / "out"
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})

            storage_dir = (
                chrome_dir / "Default" / "Sync Extension Settings"
                / "egnjhciaieeiiohknchakcodbpgjnchh"
            )
            storage_dir.mkdir(parents=True)
            lock_path = storage_dir / "LOCK"
            lock_path.write_text("")
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[extension_settings]]\n'
                'name = "Tab Wrangler"\n'
                'id = "egnjhciaieeiiohknchakcodbpgjnchh"\n'
                'storage = "sync"\n'
                'keys = ["maxTabs"]\n'
                'profiles = ["personal"]\n',
            )

            fd = os.open(lock_path, os.O_RDWR)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                result = self.run_export(manifest, chrome_dir, out_dir)
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)

            self.assertEqual(result.returncode, 1)
            self.assertIn("chrome still running", result.stderr.lower())

    def test_extension_filter_limits_export(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            chrome_dir = tmp / "Chrome"
            chrome_dir.mkdir()
            out_dir = tmp / "out"
            self.write_local_state(chrome_dir, {"Default": "me@example.com"})
            fake = self.fake_leveldbutil(tmp)

            tw_dir = (
                chrome_dir / "Default" / "Sync Extension Settings"
                / "egnjhciaieeiiohknchakcodbpgjnchh"
            )
            self.write_storage_file(
                tw_dir, "000001.log",
                "--- offset 0; sequence 1\n  put 'maxTabs' '8'\n",
            )
            res_dir = (
                chrome_dir / "Default" / "Local Extension Settings"
                / "kbmfpngjjgdllneeigpgjifpgocmfgmb"
            )
            self.write_storage_file(
                res_dir, "000001.log",
                "--- offset 0; sequence 1\n  put 'RESoptions.hover' 'true'\n",
            )
            manifest = self.write_manifest(
                tmp,
                '[profiles]\n'
                'personal = "me@example.com"\n\n'
                '[[extension_settings]]\n'
                'name = "Tab Wrangler"\n'
                'id = "egnjhciaieeiiohknchakcodbpgjnchh"\n'
                'storage = "sync"\n'
                'keys = ["maxTabs"]\n'
                'profiles = ["personal"]\n\n'
                '[[extension_settings]]\n'
                'name = "Reddit Enhancement Suite"\n'
                'id = "kbmfpngjjgdllneeigpgjifpgocmfgmb"\n'
                'storage = "local"\n'
                'keys = ["RESoptions.hover"]\n'
                'profiles = ["personal"]\n',
            )

            result = self.run_export(
                manifest, chrome_dir, out_dir, "--extension", "Tab Wrangler", leveldbutil=fake
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((out_dir / "personal" / "egnjhciaieeiiohknchakcodbpgjnchh.json").exists())
            self.assertFalse((out_dir / "personal" / "kbmfpngjjgdllneeigpgjifpgocmfgmb.json").exists())


if __name__ == "__main__":
    unittest.main()

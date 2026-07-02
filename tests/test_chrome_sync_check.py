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


if __name__ == "__main__":
    unittest.main()

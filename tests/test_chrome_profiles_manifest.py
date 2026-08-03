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
        tracked_names = {ext["name"] for ext in manifest["extensions"]}
        self.assertEqual(
            tracked_names,
            {
                "uBlock Origin Lite", "Dark Reader", "1Password",
                "1Password Nightly", "Privacy Badger",
                "Reddit Enhancement Suite", "Tab Wrangler",
            },
        )
        # No Chrome-level settings tracked yet.
        self.assertEqual(manifest.get("settings", []), [])


if __name__ == "__main__":
    unittest.main()

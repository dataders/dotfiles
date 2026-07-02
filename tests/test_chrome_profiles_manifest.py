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

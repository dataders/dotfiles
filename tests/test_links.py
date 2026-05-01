import os
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class LinksScriptTests(unittest.TestCase):
    def run_links(self, mode, tmpdir):
        env = os.environ.copy()
        env.update(
            {
                "DOTFILES_ROOT": str(ROOT),
                "DOTFILES_HOME": str(tmpdir / "home"),
                "DOTFILES_ENV": str(tmpdir / "dotfiles_env"),
                "DOTFILES_DEVELOPER": str(tmpdir / "Developer"),
            }
        )
        return subprocess.run(
            ["zsh", str(ROOT / "links.sh"), mode],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_manifest_contains_core_private_and_workspace_links(self):
        manifest = (ROOT / "links.tsv").read_text()

        self.assertIn("repo:.config/starship.toml\thome:.config/starship.toml", manifest)
        self.assertIn("env:.dbt/profiles.yml\thome:.dbt/profiles.yml", manifest)
        self.assertIn(
            "repo:workspaces/fs/settings.json\tdeveloper:fs/.vscode/settings.json",
            manifest,
        )

    def test_dry_run_does_not_create_links(self):
        with tempfile.TemporaryDirectory() as path:
            tmpdir = pathlib.Path(path)
            result = self.run_links("dry-run", tmpdir)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("DRY-RUN", result.stdout)
            self.assertFalse((tmpdir / "home/.config/starship.toml").exists())

    def test_apply_check_and_unlink_are_manifest_driven(self):
        with tempfile.TemporaryDirectory() as path:
            tmpdir = pathlib.Path(path)

            apply_result = self.run_links("apply", tmpdir)
            self.assertEqual(apply_result.returncode, 0, apply_result.stderr)

            starship_target = tmpdir / "home/.config/starship.toml"
            self.assertTrue(starship_target.is_symlink())
            self.assertEqual(os.readlink(starship_target), str(ROOT / ".config/starship.toml"))

            dbt_target = tmpdir / "home/.dbt/profiles.yml"
            self.assertTrue(dbt_target.is_symlink())
            self.assertEqual(
                os.readlink(dbt_target),
                str(tmpdir / "dotfiles_env/.dbt/profiles.yml"),
            )

            workspace_target = tmpdir / "Developer/fs/.vscode/settings.json"
            self.assertTrue(workspace_target.is_symlink())
            self.assertEqual(
                os.readlink(workspace_target),
                str(ROOT / "workspaces/fs/settings.json"),
            )

            check_result = self.run_links("check", tmpdir)
            self.assertEqual(check_result.returncode, 0, check_result.stdout + check_result.stderr)

            unlink_result = self.run_links("unlink", tmpdir)
            self.assertEqual(unlink_result.returncode, 0, unlink_result.stderr)
            self.assertFalse(starship_target.exists())
            self.assertFalse(dbt_target.exists())
            self.assertFalse(workspace_target.exists())


if __name__ == "__main__":
    unittest.main()

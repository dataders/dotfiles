import os
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class LinksScriptTests(unittest.TestCase):
    def run_links(self, mode, tmpdir, platform="Darwin", manifest=None, repo_root=ROOT):
        env = os.environ.copy()
        env.pop("DOTFILES_MANIFEST", None)
        env.update(
            {
                "DOTFILES_ROOT": str(repo_root),
                "DOTFILES_HOME": str(tmpdir / "home"),
                "DOTFILES_ENV": str(tmpdir / "dotfiles_env"),
                "DOTFILES_DEVELOPER": str(tmpdir / "Developer"),
                "DOTFILES_PLATFORM": platform,
            }
        )
        if manifest is not None:
            env["DOTFILES_MANIFEST"] = manifest
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
        manifest = (ROOT / "links.tsv").read_text() + (ROOT / "links.shared.tsv").read_text()

        self.assertIn("repo:.config/starship.toml\thome:.config/starship.toml", manifest)
        self.assertIn(
            "repo:wizard/config.toml\thome:.dbt/wizard/config.toml",
            manifest,
        )
        self.assertIn(
            "repo:AGENTS.md\thome:.dbt/wizard/AGENTS.md",
            manifest,
        )
        self.assertIn(
            "repo:.codex/rules/default.rules\thome:.dbt/wizard/rules/default.rules",
            manifest,
        )
        self.assertIn("env:.dbt/profiles.yml\thome:.dbt/profiles.yml", manifest)
        self.assertIn(
            "repo:workspaces/fs/settings.json\tdeveloper:fs/.vscode/settings.json",
            manifest,
        )
        self.assertIn(
            "repo:bin/shadowtraffic-clickhouse\thome:.local/bin/shadowtraffic-clickhouse",
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
            self.assertTrue((tmpdir / "home/.codex/config.toml").is_file())
            self.assertFalse((tmpdir / "home/.claude.json").exists())

    def test_linux_links_use_shared_and_linux_manifests(self):
        with tempfile.TemporaryDirectory() as path:
            tmpdir = pathlib.Path(path)
            home = tmpdir / "home"

            result = self.run_links("apply", tmpdir, platform="Linux")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((home / ".zshrc").resolve(), ROOT / "remote/.zshrc")
            self.assertFalse((home / "Library").exists())
            self.assertEqual((home / ".codex/skills/worktrunk").resolve(), ROOT / ".ai/skills/worktrunk")
            config = home / ".codex/config.toml"
            self.assertFalse(config.is_symlink())
            self.assertEqual(config.read_bytes(), (ROOT / "remote/.codex-config.toml").read_bytes())
            check = self.run_links("check", tmpdir, manifest="remote/links.tsv")
            self.assertEqual(check.returncode, 0, check.stderr)

    def test_local_copy_migration_preserves_state(self):
        with tempfile.TemporaryDirectory() as path:
            tmpdir = pathlib.Path(path)
            home = tmpdir / "home"
            (home / ".codex").mkdir(parents=True)
            target = home / ".codex/config.toml"
            source = ROOT / ".codex/config.toml"
            target.symlink_to(source)

            result = self.run_links("apply", tmpdir)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(target.is_symlink())
            self.assertEqual(target.read_bytes(), source.read_bytes())
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            target.write_text("changed locally\n")

            result = self.run_links("apply", tmpdir)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(target.read_text(), "changed locally\n")

    def test_detach_recovers_removed_legacy_file_from_git(self):
        with tempfile.TemporaryDirectory() as path:
            tmpdir = pathlib.Path(path)
            repo = tmpdir / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", repo], check=True)
            source = repo / ".claude.json"
            saved_state = '{"accountMarker": "preserve"}\n'
            source.write_text(saved_state)
            subprocess.run(["git", "add", source.name], cwd=repo, check=True)
            commit = [
                "git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.com",
                "-c", "core.hooksPath=/dev/null", "commit", "-q", "--no-gpg-sign",
            ]
            subprocess.run([*commit, "-m", "Add legacy state"], cwd=repo, check=True)
            subprocess.run(["git", "rm", "-q", source.name], cwd=repo, check=True)
            subprocess.run([*commit, "-m", "Remove legacy state"], cwd=repo, check=True)
            manifest = repo / "migration.tsv"
            manifest.write_text("repo:.claude.json\thome:.claude.json\tagents\tdetach\tLegacy state\n")
            home = tmpdir / "home"
            home.mkdir()
            target = home / ".claude.json"
            target.symlink_to(source)

            result = self.run_links("apply", tmpdir, manifest=str(manifest), repo_root=repo)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(target.is_symlink())
            self.assertEqual(target.read_text(), saved_state)

    def test_apply_preserves_existing_skill_directory(self):
        with tempfile.TemporaryDirectory() as path:
            tmpdir = pathlib.Path(path)
            skill = tmpdir / "home/.claude/skills/worktrunk"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("installed locally\n")

            result = self.run_links("apply", tmpdir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(str(skill), result.stderr)
            self.assertEqual((skill / "SKILL.md").read_text(), "installed locally\n")


if __name__ == "__main__":
    unittest.main()

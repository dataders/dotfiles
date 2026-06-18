import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class SerenaLinkTests(unittest.TestCase):
    def run_link(self, repo_path, root, developer, *extra):
        env = os.environ.copy()
        env.update(
            {
                "DOTFILES_ROOT": str(root),
                "DOTFILES_DEVELOPER": str(developer),
                "DOTFILES_MANIFEST": str(root / "links.tsv"),
            }
        )
        return subprocess.run(
            ["zsh", str(ROOT / "bin" / "serena-link"), str(repo_path), *extra],
            cwd=ROOT, env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )

    def _sandbox(self, tmp):
        root = tmp / "dotfiles"
        (root / "serena" / "projects").mkdir(parents=True)
        (root / "links.tsv").write_text("")
        developer = tmp / "Developer"
        developer.mkdir()
        return root, developer

    def test_stub_created_and_rows_appended(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            root, developer = self._sandbox(tmp)
            repo = developer / "foo"
            repo.mkdir()
            r = self.run_link(repo, root, developer, "--lang", "python")
            self.assertEqual(r.returncode, 0, r.stderr)
            yml = (root / "serena/projects/foo/project.yml").read_text()
            self.assertIn('project_name: "foo"', yml)
            self.assertIn("- python", yml)
            self.assertTrue((root / "serena/projects/foo/memories").is_dir())
            manifest = (root / "links.tsv").read_text()
            self.assertIn(
                "repo:serena/projects/foo/project.yml\tdeveloper:foo/.serena/project.yml\tagents\tpublic\tserena per-repo config",
                manifest,
            )
            self.assertIn(
                "repo:serena/projects/foo/memories\tdeveloper:foo/.serena/memories\tagents\tpublic\tserena per-repo memories",
                manifest,
            )

    def test_existing_project_yml_is_moved(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            root, developer = self._sandbox(tmp)
            repo = developer / "bar"
            (repo / ".serena").mkdir(parents=True)
            (repo / ".serena" / "project.yml").write_text('project_name: "bar"\nlanguages:\n- rust\n')
            r = self.run_link(repo, root, developer)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((repo / ".serena" / "project.yml").exists())
            self.assertIn("- rust", (root / "serena/projects/bar/project.yml").read_text())

    def test_empty_memories_dir_removed(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            root, developer = self._sandbox(tmp)
            repo = developer / "baz"
            (repo / ".serena" / "memories").mkdir(parents=True)
            r = self.run_link(repo, root, developer, "--lang", "go")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((repo / ".serena" / "memories").exists())

    def test_collision_guard(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            root, developer = self._sandbox(tmp)
            repo = developer / "dup"
            repo.mkdir()
            self.assertEqual(self.run_link(repo, root, developer, "--lang", "python").returncode, 0)
            r2 = self.run_link(repo, root, developer, "--lang", "python")
            self.assertNotEqual(r2.returncode, 0)
            self.assertIn("already exists", r2.stderr)

    def test_refuses_worktree_checkout(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            _, developer = self._sandbox(tmp)
            wt_root = tmp / ".claude" / "worktrees" / "x" / "dotfiles"
            (wt_root / "serena" / "projects").mkdir(parents=True)
            (wt_root / "links.tsv").write_text("")
            repo = developer / "wtrepo"
            repo.mkdir()
            r = self.run_link(repo, wt_root, developer, "--lang", "python")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("worktree", r.stderr.lower())


if __name__ == "__main__":
    unittest.main()

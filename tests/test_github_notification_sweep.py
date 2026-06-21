import os
import pathlib
import plistlib
import subprocess
import tempfile
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "github-notification-sweep"
PLIST = ROOT / "Library" / "LaunchAgents" / "com.dataders.github-notification-sweep.plist"


class GithubNotificationSweepTests(unittest.TestCase):
    def fake_gh(self, tmpdir, responses):
        fake = tmpdir / "gh"
        log = tmpdir / "gh.log"
        cases = "\n".join(
            f"""\
            if [[ "$args" == *{pattern!r}* ]]; then
              cat <<'JSON'
            {body}
            JSON
              exit 0
            fi
            """
            for pattern, body in responses
        )
        fake.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            'args="$*"\n'
            'printf "%s\\n" "$args" >> "$GH_FAKE_LOG"\n'
            f"{textwrap.dedent(cases)}\n"
            'echo "unexpected gh api call: $args" >&2\n'
            "exit 9\n"
        )
        fake.chmod(0o755)
        return fake, log

    def run_sweep(self, fake, log, *args):
        env = os.environ.copy()
        env.update(
            {
                "GH_NOTIFICATION_SWEEP_GH": str(fake),
                "GH_FAKE_LOG": str(log),
            }
        )
        return subprocess.run(
            [str(SCRIPT), *args],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_apply_marks_ci_notification_done_when_pr_head_moved(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            notification = (
                '{"id":"123","reason":"ci_activity","repository":{"full_name":"o/r"},'
                '"subject":{"title":"CI failed","type":"CheckSuite",'
                '"url":"https://api.github.com/repos/o/r/check-suites/1"}}'
            )
            fake, log = self.fake_gh(
                tmp,
                [
                    ("/notifications?all=false&participating=false", notification),
                    (
                        "https://api.github.com/repos/o/r/check-suites/1",
                        '{"head_sha":"old","pull_requests":[{"number":7}]}',
                    ),
                    ("/repos/o/r/pulls/7", '{"number":7,"state":"open","merged":false,"head":{"sha":"new"}}'),
                    ("/notifications/threads/123", "{}"),
                ],
            )

            result = self.run_sweep(fake, log, "--apply")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("marked done 123 o/r", result.stdout)
            self.assertIn("PR #7 moved from old to new", result.stdout)
            self.assertIn("--method DELETE /notifications/threads/123", log.read_text())

    def test_default_mode_is_dry_run_for_merged_pr(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            notification = (
                '{"id":"456","reason":"ci_activity","repository":{"full_name":"o/r"},'
                '"subject":{"title":"CI failed","type":"WorkflowRun",'
                '"url":"https://api.github.com/repos/o/r/actions/runs/88"}}'
            )
            fake, log = self.fake_gh(
                tmp,
                [
                    ("/notifications?all=false&participating=false", notification),
                    (
                        "https://api.github.com/repos/o/r/actions/runs/88",
                        '{"head_sha":"abc","pull_requests":[{"number":8}]}',
                    ),
                    ("/repos/o/r/pulls/8", '{"number":8,"state":"closed","merged":true,"head":{"sha":"abc"}}'),
                ],
            )

            result = self.run_sweep(fake, log)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("would mark done 456 o/r", result.stdout)
            self.assertIn("PR #8 merged", result.stdout)
            self.assertNotIn("--method DELETE", log.read_text())

    def test_current_pr_head_is_kept(self):
        with tempfile.TemporaryDirectory() as p:
            tmp = pathlib.Path(p)
            notification = (
                '{"id":"789","reason":"ci_activity","repository":{"full_name":"o/r"},'
                '"subject":{"title":"CI failed","type":"CheckSuite",'
                '"url":"https://api.github.com/repos/o/r/check-suites/2"}}'
            )
            fake, log = self.fake_gh(
                tmp,
                [
                    ("/notifications?all=false&participating=false", notification),
                    (
                        "https://api.github.com/repos/o/r/check-suites/2",
                        '{"head_sha":"same","pull_requests":[{"number":9}]}',
                    ),
                    ("/repos/o/r/pulls/9", '{"number":9,"state":"open","merged":false,"head":{"sha":"same"}}'),
                ],
            )

            result = self.run_sweep(fake, log)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("0 stale CI notifications", result.stdout)
            self.assertNotIn("--method DELETE", log.read_text())

    def test_launchagent_is_manifest_managed(self):
        manifest = (ROOT / "links.tsv").read_text()

        self.assertIn(
            "repo:Library/LaunchAgents/com.dataders.github-notification-sweep.plist"
            "\thome:Library/LaunchAgents/com.dataders.github-notification-sweep.plist",
            manifest,
        )

        with PLIST.open("rb") as fh:
            plist = plistlib.load(fh)

        self.assertEqual(plist["Label"], "com.dataders.github-notification-sweep")
        self.assertEqual(plist["ProgramArguments"][0], "/Users/dataders/Developer/dotfiles/bin/github-notification-sweep")
        self.assertIn("StartInterval", plist)


if __name__ == "__main__":
    unittest.main()

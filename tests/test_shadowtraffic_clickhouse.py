import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "shadowtraffic-clickhouse"


class ShadowTrafficClickHouseTests(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [str(SCRIPT), *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_help_exposes_lifecycle_commands(self):
        result = self.run_script("help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("setup", result.stdout)
        self.assertIn("start [--for DURATION] [--then stop|destroy]", result.stdout)
        self.assertIn("stop", result.stdout)
        self.assertIn("destroy", result.stdout)

    def test_symlink_invocation_still_finds_repo_artifacts(self):
        with tempfile.TemporaryDirectory() as path:
            link = pathlib.Path(path) / "shadowtraffic-clickhouse"
            link.symlink_to(SCRIPT)

            result = subprocess.run(
                [str(link), "sql"],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CREATE TABLE IF NOT EXISTS shadowtraffic.events", result.stdout)

    def test_duration_parser_accepts_seconds_minutes_hours_and_bare_seconds(self):
        cases = {
            "45s": "45",
            "2m": "120",
            "1h": "3600",
            "90": "90",
        }

        for duration, seconds in cases.items():
            with self.subTest(duration=duration):
                result = self.run_script("duration-seconds", duration)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), seconds)

    def test_clickhouse_init_sql_declares_shadowtraffic_events_table(self):
        result = self.run_script("sql")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CREATE DATABASE IF NOT EXISTS shadowtraffic", result.stdout)
        self.assertIn("CREATE TABLE IF NOT EXISTS shadowtraffic.events", result.stdout)
        self.assertIn("event_time DateTime64(3, 'UTC')", result.stdout)
        self.assertIn("ENGINE = MergeTree", result.stdout)

    def test_dbt_source_yaml_points_at_shadowtraffic_events(self):
        result = self.run_script("source-yml")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("name: shadowtraffic", result.stdout)
        self.assertIn("schema: shadowtraffic", result.stdout)
        self.assertIn("name: events", result.stdout)

    def test_compose_file_keeps_license_out_of_repo_and_mounts_config(self):
        compose = ROOT / "shadowtraffic-clickhouse" / "compose.yml"
        text = compose.read_text()

        self.assertIn("shadowtraffic/shadowtraffic:latest", text)
        self.assertIn("SHADOWTRAFFIC_LICENSE_ENV", text)
        self.assertNotIn("LICENSE_SIGNATURE", text)
        self.assertIn("./shadowtraffic/config.json:/home/config.json:ro", text)


if __name__ == "__main__":
    unittest.main()

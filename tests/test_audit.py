import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
AUDITOR = PROJECT / "audit.py"


class AuditTests(unittest.TestCase):
    def run_audit(self, home: Path, entries: list[str]) -> subprocess.CompletedProcess[str]:
        manifest = home / "allowlist.txt"
        manifest.write_text("\n".join(entries) + "\n", encoding="utf-8")
        return subprocess.run(
            [
                "python3",
                "-B",
                str(AUDITOR),
                "--home",
                str(home),
                "--manifest",
                str(manifest),
                "--report",
                "-",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_valid_json_passes_without_modifying_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / "settings.json"
            original = b'{"editor.tabSize": 2}\n'
            config.write_bytes(original)

            result = self.run_audit(home, ["settings.json"])

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("| OK | `settings.json` | checks passed |", result.stdout)
            self.assertEqual(config.read_bytes(), original)

    def test_invalid_json_fails_and_reports_location(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / "settings.json").write_text("{broken", encoding="utf-8")

            result = self.run_audit(home, ["settings.json"])

            self.assertEqual(result.returncode, 1)
            self.assertIn("invalid JSON at line 1", result.stdout)

    def test_agent_requires_description(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            agent = home / "agents" / "sample.agent.md"
            agent.parent.mkdir()
            agent.write_text("---\nname: Sample\n---\nBody\n", encoding="utf-8")

            result = self.run_audit(home, ["agents/*.agent.md"])

            self.assertEqual(result.returncode, 1)
            self.assertIn("frontmatter requires a non-empty description", result.stdout)

    def test_duplicate_agent_names_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            agents = home / "agents"
            agents.mkdir()
            for filename in ("one.agent.md", "two.agent.md"):
                (agents / filename).write_text(
                    '---\nname: "Same Agent"\ndescription: "test"\n---\nBody\n',
                    encoding="utf-8",
                )

            result = self.run_audit(home, ["agents/*.agent.md"])

            self.assertEqual(result.returncode, 1)
            self.assertIn("agent name duplicates", result.stdout)

    def test_parent_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)

            result = self.run_audit(home, ["../outside.json"])

            self.assertEqual(result.returncode, 1)
            self.assertIn("allowlist entries must stay under home", result.stdout)


if __name__ == "__main__":
    unittest.main()
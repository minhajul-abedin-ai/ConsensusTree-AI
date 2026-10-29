import subprocess
import tempfile
import unittest
from pathlib import Path

from consensustree.gitdiff import diff_snapshot
from consensustree.verification import run_unittest
from consensustree.cli import main


class Version2Tests(unittest.TestCase):
    def test_git_diff_no_network(self):
        with tempfile.TemporaryDirectory() as d:
            def git(*args):
                subprocess.run(["git", "-C", d, *args], check=True, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            git("init", "-q")
            git("-c", "user.name=Tester", "-c", "user.email=test@example.com", "commit", "--allow-empty", "-qm", "Initial")
            p = Path(d) / "module.py"
            p.write_text("value = 2\n")
            git("add", ".")
            git("-c", "user.name=Tester", "-c", "user.email=test@example.com", "commit", "-qm", "Second")
            snap = diff_snapshot(d)
            self.assertIn("+value = 2", snap.text)
            self.assertEqual(snap.files, ["module.py"])
            self.assertEqual(main(["pr-review", d, "--dry-run"]), 0)

    def test_tests_never_execute_without_opt_in(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "--unsafe-execute"):
                run_unittest(d)
            self.assertEqual(main(["verify", d]), 1)

    def test_explicit_test_execution(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "tests").mkdir()
            (Path(d) / "tests" / "test_simple.py").write_text(
                "import unittest\nclass T(unittest.TestCase):\n def test_true(self):\n  self.assertTrue(True)\n")
            result = run_unittest(d, consent=True)
            self.assertTrue(result["passed"])
            self.assertEqual(result["exit_code"], 0)

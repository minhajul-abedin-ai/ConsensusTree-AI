import tempfile
import unittest
from pathlib import Path

from consensustree.cli import main


class CLITests(unittest.TestCase):
    def test_demo_without_api_keys(self):
        with tempfile.TemporaryDirectory() as d:
            md = Path(d, "demo.md")
            js = Path(d, "demo.json")
            self.assertEqual(main(["demo", "--output", str(md), "--json", str(js)]), 0)
            self.assertIn("DEMO ONLY", md.read_text())
            self.assertIn('"demo": true', js.read_text())

    def test_dry_run_never_requires_api_keys(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d, "app.py")
            source.write_text("print('hello')\n")
            self.assertEqual(main(["review", d, "--dry-run"]), 0)
            self.assertFalse(Path(d, "consensustree-report.md").exists())

    def test_unknown_provider_model_pair(self):
        self.assertEqual(main(["ask", "Question", "--models", "unknown:model"]), 1)


if __name__ == "__main__":
    unittest.main()

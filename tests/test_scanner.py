import tempfile
import unittest
from pathlib import Path

from consensustree.scanner import scan


class ScannerTests(unittest.TestCase):
    def test_only_safe_bounded_source(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "src").mkdir()
            (base / "node_modules").mkdir()
            (base / ".hg").mkdir()
            (base / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
            (base / "src" / "passwords.py").write_text("password='x'\n", encoding="utf-8")
            (base / ".env").write_text("API_KEY=BAD\n", encoding="utf-8")
            (base / "node_modules" / "lib.js").write_text("x\n", encoding="utf-8")
            (base / ".hg" / "config.json").write_text("x\n", encoding="utf-8")
            (base / "src" / "image.png").write_bytes(b"\x89PNG")
            snapshot = scan(base)
            self.assertEqual(snapshot.files, ["src/app.py"])
            self.assertIn("   1 | x = 1", snapshot.text)
            self.assertNotIn("BAD", snapshot.text)

    def test_exclude_patterns(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "app.py").write_text("print(1)")
            (base / "tests.py").write_text("print(2)")
            snapshot = scan(base, exclude=["tests.py"])
            self.assertEqual(snapshot.files, ["app.py"])

    def test_truncation_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "app.py").write_text("print('x')\n" * 400)
            snap = scan(base, max_chars=500)
            self.assertTrue(snap.truncated)
            self.assertEqual(snap.files, ["app.py"])

    def test_missing_path(self):
        with self.assertRaises(ValueError):
            scan("/path/that/should/not/exist/consensustree")

    def test_single_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "project.py")
            path.write_text("a = 1\n")
            self.assertEqual(scan(path).files, ["project.py"])


if __name__ == "__main__":
    unittest.main()

import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("validate_pairs", Path(__file__).with_name("validate_pairs.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
D = "a" * 64


class PairTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual([], module.validate({"records": [{"case_id": "one", "arm": a, "case_sha256": D} for a in ("baseline", "council")]}))

    def test_missing_arm(self):
        self.assertTrue(module.validate({"records": [{"case_id": "one", "arm": "baseline", "case_sha256": D}]}))

    def test_duplicate_arm(self):
        rows = [{"case_id": "one", "arm": a, "case_sha256": D} for a in ("baseline", "baseline", "council")]
        self.assertTrue(any("duplicate" in x for x in module.validate({"records": rows})))

    def test_mismatched_digest(self):
        rows = [{"case_id": "one", "arm": a, "case_sha256": d} for a, d in (("baseline", D), ("council", "b" * 64))]
        self.assertTrue(any("mismatched" in x for x in module.validate({"records": rows})))

    def test_bad_input(self):
        self.assertTrue(module.validate({"records": []}))
        self.assertTrue(module.validate({"records": [42]}))


if __name__ == "__main__":
    unittest.main()

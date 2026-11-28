import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("production_pairs_manifest", Path(__file__).with_name("production_pairs_manifest.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def sample(**overrides):
    case = {"id": "synthetic-1", "source_sha256": "a" * 64,
            "baseline": "fictional response", "council": {"execution": "synthetic"},
            "completion": "complete"}
    case.update(overrides)
    return {"benchmark_type": "production_Council_vs_single_model", "cases": [case]}


class AdapterTests(unittest.TestCase):
    def test_converts_both_arms(self):
        rows = module.convert(sample())["records"]
        self.assertEqual(["baseline", "council"], [r["arm"] for r in rows])
        self.assertEqual({"a" * 64}, {r["case_sha256"] for r in rows})

    def test_missing_arm_fails(self):
        with self.assertRaisesRegex(ValueError, "missing baseline"):
            module.convert(sample(baseline=None))

    def test_blank_response_arm_fails(self):
        for arm in ("baseline", "council"):
            with self.subTest(arm=arm):
                with self.assertRaisesRegex(ValueError, "missing baseline or council output"):
                    module.convert(sample(**{arm: "  \n  "}))

    def test_empty_structured_response_arm_fails(self):
        for arm in ("baseline", "council"):
            for empty in ({}, []):
                with self.subTest(arm=arm, empty_type=type(empty).__name__):
                    with self.assertRaisesRegex(ValueError, "missing baseline or council output"):
                        module.convert(sample(**{arm: empty}))

    def test_incomplete_council_rejected(self):
        for status in ("partial", None, "failed"):
            with self.subTest(status=status):
                with self.assertRaisesRegex(ValueError, "council execution not complete"):
                    module.convert(sample(completion=status))

    def test_scalar_response_arm_fails(self):
        for arm in ("baseline", "council"):
            for invalid in (False, True, 0, 1, 1.5):
                with self.subTest(arm=arm, invalid=invalid):
                    with self.assertRaisesRegex(ValueError, "missing baseline or council output"):
                        module.convert(sample(**{arm: invalid}))

    def test_multiple_cases_preserve_pairing_order(self):
        data = sample()
        second = dict(data["cases"][0], id="synthetic-2", source_sha256="b" * 64)
        data["cases"].append(second)
        rows = module.convert(data)["records"]
        self.assertEqual(
            [("synthetic-1", "baseline", "a" * 64),
             ("synthetic-1", "council", "a" * 64),
             ("synthetic-2", "baseline", "b" * 64),
             ("synthetic-2", "council", "b" * 64)],
            [(row["case_id"], row["arm"], row["case_sha256"]) for row in rows],
        )

    def test_invalid_digest_fails(self):
        with self.assertRaisesRegex(ValueError, "invalid source_sha256"):
            module.convert(sample(source_sha256="not-a-hash"))

    def test_duplicate_case_fails(self):
        data = sample()
        data["cases"].append(dict(data["cases"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate id"):
            module.convert(data)

    def test_wrong_benchmark_fails(self):
        data = sample()
        data["benchmark_type"] = "other"
        with self.assertRaises(ValueError):
            module.convert(data)


if __name__ == "__main__":
    unittest.main()

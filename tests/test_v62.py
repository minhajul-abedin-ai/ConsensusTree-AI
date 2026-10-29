"""v6.2 release gates: structural completeness, citation integrity, provider input safety.

These tests verify deterministic logic and mock-based transport boundaries. They
DO NOT establish whether any AI-generated bug claim is true.
"""
import tempfile
import unittest
from pathlib import Path

from consensustree.core import Council
from consensustree.grounding import audit_report_references
from consensustree.hierarchy import HierarchicalCouncil
from consensustree.providers import ModelSpec, ProviderError
from consensustree.report import to_markdown
from consensustree.scanner import scan


class MockModel:
    def __init__(self, fail=()):
        self.calls = 0
        self.fail = set(fail)

    def complete(self, spec, system, user):
        n = self.calls
        self.calls += 1
        if n in self.fail:
            raise ProviderError("simulated provider failure")
        return "Issue in `app.py:2` and nonexistent `missing.py:8`."


class TestVersion62(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "app.py").write_text("x = 1\nprint(x)\n", encoding="utf-8")
        self.model = ModelSpec("ollama", "fixture")

    def test_normal_council_marked_complete_but_not_fact_checked(self):
        report = Council([self.model], client=MockModel()).review(self.root)
        gate = report.execution["completion"]
        self.assertEqual(gate["status"], "complete")
        self.assertEqual(gate["successful_specialists"], 3)
        self.assertTrue(gate["chair_completed"])
        self.assertIn("unverified", gate["meaning"])

    def test_missing_specialist_marked_partial(self):
        report = Council([self.model], client=MockModel(fail={1})).review(self.root)
        gate = report.execution["completion"]
        self.assertEqual(gate["status"], "partial")
        self.assertEqual(gate["successful_specialists"], 2)
        self.assertEqual(gate["failed_steps"], 1)
        self.assertIn("INCOMPLETE COUNCIL", to_markdown(report))

    def test_failed_chair_marked_partial(self):
        report = Council([self.model], client=MockModel(fail={3})).ask("Would this work?")
        self.assertEqual(report.execution["completion"]["status"], "partial")
        self.assertFalse(report.execution["completion"]["chair_completed"])

    def test_explicit_no_synthesis_is_complete_without_chair(self):
        report = Council([self.model], client=MockModel(), synthesize=False).ask("Would this work?")
        self.assertEqual(report.execution["completion"]["status"], "complete")
        self.assertFalse(report.execution["completion"]["chair_required"])

    def test_hierarchy_complete(self):
        report = HierarchicalCouncil([self.model], client=MockModel(), groups=2, max_calls=9).review_snapshot(scan(self.root))
        gate = report.execution["completion"]
        self.assertEqual(gate["status"], "complete")
        self.assertEqual(gate["expected_specialists"], 6)
        self.assertEqual(gate["expected_groups"], 2)

    def test_hierarchy_failing_group_chair_is_partial(self):
        report = HierarchicalCouncil([self.model], client=MockModel(fail={3}), groups=1, max_calls=5).review_snapshot(scan(self.root))
        self.assertEqual(report.execution["completion"]["status"], "partial")
        self.assertTrue(report.errors)

    def test_unknown_file_citation_is_not_credited(self):
        report = Council([self.model], client=MockModel()).review(self.root)
        audit = report.execution["reference_audit"]
        self.assertEqual(audit["in_snapshot"], 3)
        self.assertEqual(audit["outside_snapshot"], 3)
        self.assertEqual(audit["unrecognized_files"], 3)
        self.assertFalse(audit["fact_checked"])
        self.assertIn("Unrecognized file references", to_markdown(report))

    def test_only_unknown_file_citation_counts_as_a_reference(self):
        class Agent:
            role = "Security"
            content = "`ghost.py:999` likely has a bug"
        audit = audit_report_references(scan(self.root), [Agent()])
        self.assertEqual(audit["agents_without_line_references"], 0)
        self.assertEqual(audit["outside_snapshot"], 1)
        self.assertFalse(audit["details"][0]["recognized_file"])

    def test_existing_markdown_reference_section_not_duplicated(self):
        report = Council([self.model], client=MockModel()).review(self.root)
        self.assertEqual(to_markdown(report).count("## Source-reference integrity"), 1)

    def test_reject_model_name_with_query_string(self):
        with self.assertRaisesRegex(ValueError, "Invalid model"):
            ModelSpec("gemini", "gemini-x?key=secret")

    def test_reject_model_name_path_traversal(self):
        with self.assertRaisesRegex(ValueError, "Invalid model"):
            ModelSpec("gemini", "../another")

    def test_direct_construction_rejects_unknown_provider(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            ModelSpec("mystery", "model")

    def test_permitted_model_identifiers(self):
        for name in ("gpt-4.1-mini", "gemini-2.5-flash", "llama3.2:latest", "provider/model-v2"):
            self.assertEqual(ModelSpec("ollama", name).model, name)


if __name__ == "__main__":
    unittest.main()

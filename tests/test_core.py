import tempfile
import unittest
from pathlib import Path

from consensustree.core import Council
from consensustree.providers import ModelSpec, ProviderError
from consensustree.report import to_markdown, write_report


class FakeClient:
    def __init__(self, fail_at=()):
        self.calls = []
        self.fail_at = set(fail_at)

    def complete(self, spec, system, user):
        index = len(self.calls)
        self.calls.append((spec, system, user))
        if index in self.fail_at:
            raise ProviderError("mock rate limit")
        return f"Mock result {index}: this is a test, not an AI report."


class CouncilTests(unittest.TestCase):
    def setUp(self):
        self.models = [ModelSpec("openai", "fixture-model")] * 3

    def test_ask_three_independent_agents_and_chair(self):
        fake = FakeClient()
        council = Council(self.models, client=fake)
        report = council.ask("Should we ship a product?")
        self.assertEqual(len(fake.calls), 4)
        self.assertEqual([a.role for a in report.agents], ["Pragmatist", "Skeptic", "Strategist"])
        self.assertNotIn("Mock result 0", fake.calls[1][2], "Second agent must not see earlier results")
        self.assertIn("Mock result 0", fake.calls[3][2], "Chair must see agent reports")
        self.assertIn("Mock result 1", fake.calls[3][2])
        self.assertIn("Mock result 2", fake.calls[3][2])
        self.assertEqual(report.chair_model, "openai:fixture-model")

    def test_no_synthesis_saves_one_call(self):
        fake = FakeClient()
        report = Council(self.models, client=fake, synthesize=False).ask("Question")
        self.assertEqual(len(fake.calls), 3)
        self.assertIsNone(report.synthesis)
        self.assertIn("Not available", to_markdown(report))

    def test_individual_agent_error_yields_partial_report(self):
        fake = FakeClient(fail_at={1})
        report = Council(self.models, client=fake).ask("What is next?")
        self.assertEqual(len(report.agents), 2)
        self.assertEqual(len(report.errors), 1)
        self.assertIsNotNone(report.synthesis)

    def test_all_agent_failures_raise(self):
        with self.assertRaisesRegex(ProviderError, "No agents succeeded"):
            Council(self.models, client=FakeClient(fail_at={0, 1, 2})).ask("Question")

    def test_chair_failure_returns_incomplete_report(self):
        report = Council(self.models, client=FakeClient(fail_at={3})).ask("Question")
        self.assertEqual(len(report.agents), 3)
        self.assertIsNone(report.synthesis)
        self.assertEqual(len(report.errors), 1)

    def test_review_and_write_report(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "app.py").write_text("def f(x):\n    return 10/x\n", encoding="utf-8")
            fake = FakeClient()
            report = Council(self.models, client=fake).review(d)
            self.assertEqual(len(report.reviewed_files), 1)
            self.assertEqual([a.role for a in report.agents], ["Architecture", "Security", "Reliability"])
            self.assertIn("   2 |     return 10/x", fake.calls[0][2])
            self.assertEqual(len(fake.calls), 4)
            path = Path(d, "results.md")
            jsonpath = Path(d, "results.json")
            write_report(report, path, jsonpath)
            self.assertIn("## Council synthesis", path.read_text())
            self.assertIn('"reviewed_files"', jsonpath.read_text())

    def test_invalid_question(self):
        with self.assertRaises(ValueError):
            Council(self.models).ask("  ")

    def test_model_count_bounds(self):
        with self.assertRaises(ValueError):
            Council([])
        with self.assertRaises(ValueError):
            Council(self.models * 2)


if __name__ == "__main__":
    unittest.main()

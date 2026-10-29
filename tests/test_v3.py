import unittest
from consensustree.core import CouncilReport
from consensustree.hierarchy import HierarchicalCouncil, adaptive_group_count
from consensustree.providers import ModelSpec, ProviderError
from consensustree.report import to_markdown
from consensustree.scanner import Snapshot


class FakeClient:
    def __init__(self):
        self.calls = []

    def complete(self, spec, system, user):
        self.calls.append((system, user))
        return f"Safe fixture response number {len(self.calls)}"


class Version3Tests(unittest.TestCase):
    def setUp(self):
        self.models = [ModelSpec("openai", "fixture-model")] * 3

    def test_group_count_and_isolation(self):
        client = FakeClient()
        report = HierarchicalCouncil(self.models, client=client, groups=2, max_calls=9).ask("What to build?")
        self.assertEqual(len(client.calls), 9)
        self.assertEqual(report.execution["actual_calls"], 9)
        self.assertEqual(len(report.groups), 2)
        self.assertEqual(len(report.agents), 6)
        self.assertNotIn("Safe fixture response number 1", client.calls[1][1])
        self.assertIn("Safe fixture response number 1", client.calls[3][1])
        self.assertIn("Group 1", client.calls[-1][1])
        self.assertIn("Group deliberations", to_markdown(report))

    def test_budget_preflight_no_requests(self):
        client = FakeClient()
        with self.assertRaisesRegex(ValueError, "exceed"):
            HierarchicalCouncil(self.models, client=client, groups=4, max_calls=10)
        self.assertEqual(client.calls, [])

    def test_adaptive_is_a_heuristic(self):
        self.assertEqual(adaptive_group_count("A short question"), 1)
        self.assertEqual(adaptive_group_count("Security architecture"), 3)

    def test_review_mode(self):
        c = HierarchicalCouncil(self.models, client=FakeClient(), groups=1, max_calls=5)
        r = c.review_snapshot(Snapshot("/demo", ["app.py"], "--- FILE app.py ---\n", False))
        self.assertEqual(r.mode, "review")
        self.assertEqual(r.reviewed_files, ["app.py"])

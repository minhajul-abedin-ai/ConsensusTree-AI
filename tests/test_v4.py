import json
import tempfile
import unittest
from pathlib import Path
from consensustree.dashboard import render_dashboard, write_dashboard
from consensustree.metering import MeteredClient
from consensustree.providers import ModelSpec, ProviderError
from consensustree.cli import main

class Fixture:
    def complete(self, spec, system, user):
        return "valid response"

class Version4Tests(unittest.TestCase):
    def test_html_escapes_script_breakout_and_model_html(self):
        report = {"mode":"ask", "task":"</script><img src=x onerror=alert(1)>",
                  "agents":[{"role":"X", "model":"Y", "content":"<script>alert(1)</script>", "duration_seconds":0.1}]}
        html = render_dashboard(report)
        self.assertNotIn('</script><img src=x onerror=', html)
        self.assertNotIn('<script>alert(1)', html)
        self.assertIn('\\u003c/script\\u003e', html)
        self.assertIn('Content-Security-Policy', html)

    def test_dashboard_file_generation(self):
        with tempfile.TemporaryDirectory() as d:
            report=Path(d)/"report.json"
            report.write_text(json.dumps({"mode":"ask","task":"Demo","agents":[]}))
            dest=Path(d)/"out.html"
            self.assertEqual(main(["dashboard",str(report),"--output",str(dest)]),0)
            self.assertIn("Decision Studio",dest.read_text(encoding="utf-8"))

    def test_request_budget_enforced(self):
        client=MeteredClient(Fixture(),max_calls=1)
        spec=ModelSpec("openai","fixture")
        self.assertEqual(client.complete(spec,"S","U"),"valid response")
        with self.assertRaises(ProviderError):
            client.complete(spec,"S","U")
        self.assertEqual(client.usage()["api_calls"],1)
        self.assertTrue(client.usage()["estimated_not_billed"])

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from consensustree.benchmark import evaluate_suite
from consensustree.privacy import secret_warnings
from consensustree.plugins import load_client_plugin
from consensustree.github import pr_comment
from consensustree.cli import main

class FakeEntry:
    name = "fixture"
    value = "plugin:Client"
    def load(self):
        class Provider:
            def complete(self, spec, system, user):
                return "Fixture only"
        return Provider

class Version5Tests(unittest.TestCase):
    def test_secret_detection_does_not_disclose_value(self):
        raw = "API_KEY = 'secret-to-never-log-1234567890'"
        self.assertIn("Likely hardcoded credential", secret_warnings(raw))
        self.assertNotIn("secret-to-never-log", str(secret_warnings(raw)))

    def test_cli_blocks_sensitive_source(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/"app.py").write_text("api_key = 'secret-to-never-log-1234567890'\n")
            self.assertEqual(main(["review",d,"--dry-run"]),0)
            self.assertEqual(main(["review",d]),1)

    def test_plugin_loader_explicit_only(self):
        with patch("consensustree.plugins.entry_points",return_value=[FakeEntry()]):
            from consensustree.plugins import available_plugins
            self.assertEqual(available_plugins()[0]["name"], "fixture")
            self.assertEqual(load_client_plugin("fixture").complete(None,"", ""), "Fixture only")
            with self.assertRaises(ValueError):
                load_client_plugin("other")

    def test_github_comment_preview_does_not_send_network(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"report.md"
            f.write_text("Test findings")
            with patch("consensustree.github.urllib.request.urlopen") as mocked:
                result=pr_comment("owner/repo",4,f)
            mocked.assert_not_called()
            self.assertFalse(result["posted"])
            self.assertIn("Test findings",result["preview"])
            with self.assertRaises(ValueError):
                pr_comment("owner/../repo",4,f)

    def test_benchmark_and_traversal(self):
        root=Path(__file__).resolve().parent.parent
        output=evaluate_suite(root/"benchmarks/suite.json",root/"benchmarks/fixtures")
        self.assertEqual(output["measured_cases"],2)
        self.assertEqual(output["average_coverage"],1.0)
        self.assertTrue(output["not_a_quality_or_accuracy_score"])
        with tempfile.TemporaryDirectory() as d:
            suite=Path(d)/"suite.json"
            suite.write_text(json.dumps({"cases":[{"id":"x","report":"../escape.json"}]}))
            with self.assertRaises(ValueError):
                evaluate_suite(suite,d)

class HardeningTests(unittest.TestCase):
    def test_no_github_redirect_leaks_token(self):
        from consensustree.github import _NoRedirect
        from urllib.request import Request
        req = Request("https://api.github.com/repos/x/y/issues/1/comments", headers={"Authorization":"Bearer token"})
        self.assertIsNone(_NoRedirect().redirect_request(req, None, 302, "Moved", {}, "https://evil.example/"))

    def test_imported_evidence_label_and_checks(self):
        from consensustree.verification import load_evidence
        from consensustree.core import CouncilReport
        from consensustree.report import to_markdown
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"evidence.json"
            path.write_text(json.dumps({"verified_by":"python-unittest", "passed":True,
                                       "exit_code":0,"output":"Ran 1 test\nOK", "hidden":"untrusted"}))
            evidence=load_evidence(path)
            self.assertNotIn("hidden",evidence)
            r=CouncilReport(mode="review",task="fixture",created_utc="now",evidence=evidence)
            self.assertIn("not independently authenticated",to_markdown(r))

    def test_plugin_works_end_to_end_without_api_key(self):
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/"fixture.json"
            with patch("consensustree.plugins.entry_points",return_value=[FakeEntry()]):
                code=main(["ask","Test plugin","--plugin","fixture","--provider","openai",
                           "--output",str(Path(d)/"fixture.md"),"--json",str(dest)])
            self.assertEqual(code,0)
            data=json.loads(dest.read_text())
            self.assertEqual(len(data["agents"]),3)
            self.assertEqual(data["execution"]["metering"]["api_calls"],4)

class DeveloperExperienceTests(unittest.TestCase):
    def test_quickstart_has_no_provider_calls(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("consensustree.providers.LLMClient.complete") as model:
                self.assertEqual(main(["quickstart", "--dir", d]), 0)
            model.assert_not_called()
            for filename in ("sample.md", "sample.json", "sample.html"):
                self.assertTrue((Path(d)/filename).is_file())
            self.assertIn('"demo": true',(Path(d)/"sample.json").read_text())

    def test_doctor_no_secrets_leaked(self):
        import io
        from contextlib import redirect_stdout
        buf=io.StringIO()
        with patch.dict(os.environ,{"OPENAI_API_KEY":"THE_SUPER_SECRET_VALUE"}):
            with redirect_stdout(buf):
                self.assertEqual(main(["doctor","--json"]),0)
        self.assertNotIn("THE_SUPER_SECRET_VALUE",buf.getvalue())
        self.assertTrue(json.loads(buf.getvalue())["api_key_configured"]["openai"])

    def test_debate_conflicting_flags_rejected(self):
        self.assertEqual(main(["debate","Question","--no-synthesis"]),1)
        self.assertEqual(main(["debate","Question","--adaptive","--groups","3"]),1)

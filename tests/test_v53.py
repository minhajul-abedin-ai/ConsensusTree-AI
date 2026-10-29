"""v5.3 self-contained offline Decision Studio regression coverage."""
import json
import re
import io
from contextlib import redirect_stdout
import tempfile
import unittest
from pathlib import Path

from consensustree import __version__
from consensustree.dashboard import render_dashboard, write_dashboard
from consensustree.cli import main


class DecisionStudio53Tests(unittest.TestCase):
    def setUp(self):
        self.report = {"mode": "review", "task": "Review repo", "agents": [
            {"role": "Security", "model": "fixture", "content": "Review carefully", "duration_seconds": 0.0}
        ], "synthesis": "**Recommendation:** Test locally."}

    def test_version(self):
        self.assertEqual(__version__, "6.3.0rc1")

    def test_cli_version_uses_package_version(self):
        with self.assertRaises(SystemExit) as cm:
            with redirect_stdout(io.StringIO()) as out:
                main(['--version'])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn('ConsensusTree AI ' + __version__, out.getvalue())

    def test_offline_resource_and_hash_csp(self):
        html = render_dashboard(self.report)
        self.assertIn('Decision Studio', html)
        self.assertIn('Open report', html)
        self.assertIn('data-view="evidence"', html)
        self.assertIn('data-view="council"', html)
        self.assertNotIn("'unsafe-inline'", html)
        self.assertRegex(html, r"script-src 'sha256-[A-Za-z0-9+/=]+'")
        self.assertRegex(html, r"style-src 'sha256-[A-Za-z0-9+/=]+'")
        self.assertNotIn('https://', html)
        self.assertNotIn('http://', html)

    def test_script_breakouts_and_unsafe_values_remain_encoded(self):
        report = dict(self.report)
        report['task'] = '</script><img src=x onerror=alert(1)> & hello'
        report['agents'] = [{"role": "<svg onload=alert(1)>", "model": "fake", "content":
            "</script><script>window.injected=1</script>", "duration_seconds": 0.0}]
        html = render_dashboard(report)
        self.assertNotIn('</script><img', html)
        self.assertNotIn('<script>window.injected', html)
        self.assertIn('\\u003c/script\\u003e', html)
        self.assertIn('\\u0026', html)

    def test_reject_bad_payload(self):
        for item in ([], None, {}, {"mode": "unknown", "task": "a", "agents": []},
                     {"mode": "ask", "task": [], "agents": []},
                     {"mode": "ask", "task": "A", "agents": None}):
            with self.subTest(item=item), self.assertRaises(ValueError):
                render_dashboard(item)

    def test_reject_nonfinite_data(self):
        bad = dict(self.report, execution={"duration_seconds": float("nan")})
        with self.assertRaises(ValueError):
            render_dashboard(bad)

    def test_save_report_and_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'in.json'
            output = Path(tmp) / 'out.html'
            source.write_text(json.dumps(self.report))
            write_dashboard(source, output)
            self.assertTrue(output.exists())
            self.assertIn('Test locally.', output.read_text(encoding='utf-8'))

    def test_quickstart_still_works_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(main(['quickstart', '--dir', tmp]), 0)
            self.assertIn('Decision Studio', (Path(tmp) / 'sample.html').read_text(encoding='utf-8'))
            self.assertTrue(json.loads((Path(tmp) / 'sample.json').read_text())['demo'])

    def test_showcase_fixture_is_disclosed(self):
        fixture = Path(__file__).resolve().parents[1] / 'examples' / 'showcase_report.json'
        showcase = json.loads(fixture.read_text())
        self.assertTrue(showcase['demo'])
        self.assertEqual(showcase['execution']['actual_calls'], 0)
        self.assertEqual(len(showcase['groups']), 2)
        self.assertIn('FIXTURE', showcase['task'])
        self.assertIn('FIXTURE', render_dashboard(showcase))


if __name__ == '__main__':
    unittest.main()

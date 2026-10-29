"""Regressions for defects confirmed in the v6.2.3 code audit.

No real API requests, external secrets or security certification are involved.
"""
import contextlib
import io
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from consensustree.cli import main
from consensustree.core import Council
from consensustree.hierarchy import HierarchicalCouncil
from consensustree.providers import ModelSpec
from consensustree.gitdiff import diff_snapshot
from consensustree.scanner import scan
from consensustree.studio import StudioState, _studio_template

FAKE_CREDENTIAL = 'password = "this-is-only-a-fake-test-token"'


class ScannerPrivacyRegression(unittest.TestCase):
    def test_uppercase_sensitive_directories_are_excluded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ('SECRETS', 'Credentials', 'my-Secrets', 'PRIVATE'):
                d = root / name
                d.mkdir()
                (d/'config.py').write_text('EXCLUDED_MARKER = 999\n')
            (root/'app.py').write_text('safe = True\n')
            snapshot = scan(root)
            self.assertEqual(snapshot.files, ['app.py'])
            self.assertNotIn('EXCLUDED_MARKER', snapshot.text)

    @unittest.skipUnless(shutil.which('git'), 'Git not installed')
    def test_git_scanning_filters_case_variants(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            subprocess.run(['git','init','-q',str(root)],check=True)
            d=root/'SECRETS';d.mkdir()
            (d/'key.py').write_text('DO_NOT_SEND = 1\n')
            (root/'good.py').write_text('safe=True\n')
            snapshot=scan(root)
            self.assertEqual(snapshot.files, ['good.py'])

    @unittest.skipUnless(shutil.which('git'), 'Git not installed')
    def test_git_diff_omits_uppercase_sensitive_directories(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            def git(*args):
                subprocess.run(['git','-C',str(root),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
            git('init','-q');git('config','user.email','test@example.invalid');git('config','user.name','Test')
            (root/'SECRETS').mkdir()
            (root/'SECRETS'/'credentials.py').write_text('BLOCKED_MARKER = 1\n')
            (root/'main.py').write_text('x=1\n')
            git('add','.');git('commit','-qm','initial')
            (root/'SECRETS'/'credentials.py').write_text('BLOCKED_MARKER = 2\n')
            (root/'main.py').write_text('x=2\n')
            git('add','.');git('commit','-qm','later')
            result=diff_snapshot(root)
            self.assertEqual(result.files,['main.py'])
            self.assertNotIn('BLOCKED_MARKER',result.text)

    def test_direct_file_target_inside_sensitive_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            secret=Path(temp)/'SECRETS'
            secret.mkdir()
            file=secret/'otherwise-normal.py'
            file.write_text('PRIVATE_MARKER = 1\n')
            with self.assertRaisesRegex(ValueError,'sensitive'):
                scan(file)

    def test_bounded_scan_discloses_omitted_eligible_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for i in range(3):
                (root/f'safe{i}.py').write_text(f'x={i}\n')
            snap=scan(root,max_files=1)
            self.assertEqual(len(snap.files),1)
            self.assertEqual(snap.eligible_files,3)
            self.assertEqual(snap.omitted_files,2)
            self.assertTrue(snap.truncated)
            state=StudioState(root)
            # The Studio uses a larger default max_files and should not omit these.
            preview=state.preview('.')
            self.assertEqual(preview['eligible_files'],3)
            self.assertEqual(preview['omitted_files'],0)


class UniformPrivacyPreflightRegression(unittest.TestCase):
    def test_ask_blocks_sensitive_question_before_plugin_load(self):
        stderr=io.StringIO()
        with patch('consensustree.cli.load_client_plugin',side_effect=AssertionError('plugin imported')):
            with contextlib.redirect_stderr(stderr):
                result=main(['ask',FAKE_CREDENTIAL,'--plugin','example','--provider','ollama'])
        self.assertEqual(result,1)
        self.assertNotIn('this-is-only-a-fake-test-token',stderr.getvalue())

    def test_debate_blocks_sensitive_question_before_plugin_load(self):
        stderr=io.StringIO()
        with patch('consensustree.cli.load_client_plugin',side_effect=AssertionError('plugin imported')):
            with contextlib.redirect_stderr(stderr):
                result=main(['debate',FAKE_CREDENTIAL,'--plugin','example','--provider','ollama'])
        self.assertEqual(result,1)
        self.assertNotIn('this-is-only-a-fake-test-token',stderr.getvalue())

    def test_sdk_basic_council_fails_before_transport(self):
        class NoCalls:
            def complete(self,*args): raise AssertionError('network touched')
        council=Council([ModelSpec('ollama','llama3.2')],client=NoCalls())
        with self.assertRaisesRegex(ValueError,'Possible credentials'):
            council.ask(FAKE_CREDENTIAL)

    def test_sdk_hierarchical_council_fails_before_transport(self):
        class NoCalls:
            def complete(self,*args): raise AssertionError('network touched')
        council=HierarchicalCouncil([ModelSpec('ollama','llama3.2')],client=NoCalls(),groups=1,max_calls=5)
        with self.assertRaisesRegex(ValueError,'Possible credentials'):
            council.ask(FAKE_CREDENTIAL)

    def test_explicit_approved_override_keeps_advanced_use_case(self):
        class LocalFixture:
            def complete(self,*args): return 'This is a mocked response, not real inference.'
        council=Council([ModelSpec('ollama','llama3.2')],client=LocalFixture(),allow_sensitive=True)
        report=council.ask(FAKE_CREDENTIAL)
        self.assertEqual(len(report.agents),3)
        self.assertFalse(report.errors)


class DashboardCorrectnessRegression(unittest.TestCase):
    def test_no_duplicate_class_attributes(self):
        template=_studio_template()
        for tag in re.findall(r'<[a-z][^<>]*>',template,flags=re.IGNORECASE):
            self.assertLessEqual(len(re.findall(r'\bclass="',tag)),1,tag[:130])

    def test_version_status_from_one_source_not_stale_literal(self):
        template=_studio_template()
        self.assertNotIn('Developer workbench · v6.1 RC1',template)
        self.assertIn('id="sidebar-version"',template)
        self.assertIn("$('sidebar-version').textContent='v'+j.version",template)


if __name__ == '__main__': unittest.main()

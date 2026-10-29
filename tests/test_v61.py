"""V6.1 regression tests for verified structural behavior, not AI accuracy."""
import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from consensustree.core import Council
from consensustree.gitdiff import diff_snapshot
from consensustree.grounding import audit_report_references
from consensustree.hierarchy import HierarchicalCouncil
from consensustree.metering import MeteredClient
from consensustree.providers import ModelSpec
from consensustree.report import to_markdown
from consensustree.scanner import Snapshot, scan
from consensustree.studio import create_server, _studio_template


class Reply:
    def __init__(self):
        self.calls=[]

    def complete(self, spec, system, user):
        self.calls.append((spec, system, user))
        return "A cited issue in `app.py:2`, but unrelated `app.py:999` is unobserved."


class Grounding61(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)
        (self.path/'app.py').write_text('x = 1\nprint(x)\n',encoding='utf-8')

    def test_one_model_still_runs_three_independent_roles(self):
        client=Reply()
        report=Council([ModelSpec('ollama','mock')],client=client).review(self.path)
        self.assertEqual([a.role for a in report.agents], ['Architecture','Security','Reliability'])
        self.assertEqual(len(client.calls),4)
        self.assertEqual(report.execution['reference_audit']['in_snapshot'],3)
        self.assertEqual(report.execution['reference_audit']['outside_snapshot'],3)
        self.assertFalse(report.execution['reference_audit']['fact_checked'])
        self.assertNotIn(str(self.path), client.calls[0][2])
        self.assertNotIn(str(self.path), client.calls[3][2])
        self.assertIn('Source-reference integrity',to_markdown(report))

    def test_two_models_rotate_without_leaking_independent_results(self):
        client=Reply()
        models=[ModelSpec('ollama','model-a'),ModelSpec('ollama','model-b')]
        report=Council(models,client=client).ask('What to ship?')
        self.assertEqual([a.model for a in report.agents],['ollama:model-a','ollama:model-b','ollama:model-a'])
        self.assertEqual(len(client.calls),4)

    def test_hierarchical_reference_audit(self):
        client=Reply()
        report=HierarchicalCouncil([ModelSpec('ollama','mock')],client=client,groups=1,max_calls=5).review_snapshot(scan(self.path))
        self.assertEqual(report.execution['reference_audit']['checked_references'],6)
        self.assertNotIn(str(self.path), client.calls[0][2])

    def test_excerpts_and_no_references(self):
        snap=scan(self.path)
        class Item: pass
        a=Item();a.role='Security';a.content='No citations provided.'
        audit=audit_report_references(snap,[a])
        self.assertEqual(audit['checked_references'],0)
        self.assertEqual(audit['agents_without_line_references'],1)

    def test_git_ignore_protects_nested_scan(self):
        if subprocess.run(['git','--version'],capture_output=True).returncode:
            self.skipTest('Git not installed')
        subprocess.run(['git','-C',str(self.path),'init','-q'],check=True)
        (self.path/'.gitignore').write_text('ignored.py\ncache/**\n',encoding='utf-8')
        (self.path/'ignored.py').write_text('sensitive = "do not send"\n')
        (self.path/'nested').mkdir()
        (self.path/'nested'/'ignored.py').write_text('do_not_send = "nested"\n')
        (self.path/'.gitignore').write_text('ignored.py\n**/ignored.py\ncache/**\n',encoding='utf-8')
        self.assertEqual(scan(self.path).files,['app.py'])
        (self.path/'nested'/'keep.py').write_text('print(1)\n', encoding='utf-8')
        self.assertEqual(scan(self.path/'nested').files,['keep.py'])

    def test_git_rev_argument_is_not_a_command_option(self):
        for rev in ('--output=/tmp/bad','-U9999', 'HEAD extra', '\nHEAD'):
            with self.subTest(rev=rev),self.assertRaises(ValueError):
                diff_snapshot(self.path,base=rev)


class Studio61(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        (self.root/'app.py').write_text('x=1\nprint(x)\n',encoding='utf-8')
        self.clients=[]
        def factory(max_calls):
            r=Reply();self.clients.append(r)
            return MeteredClient(r,max_calls)
        self.srv=create_server(self.root,0,client_factory=factory)
        self.thread=threading.Thread(target=self.srv.serve_forever,daemon=True)
        self.thread.start();self.addCleanup(self.stop)
        self.base='http://127.0.0.1:'+str(self.srv.server_port)

    def stop(self):
        self.srv.shutdown();self.srv.server_close();self.thread.join(timeout=2)

    def call(self,path,payload):
        req=urllib.request.Request(self.base+path,
                data=json.dumps(payload).encode(),method='POST',
                headers={'Content-Type':'application/json','X-CT-Token':self.srv.studio_token})
        try:
            with urllib.request.urlopen(req,timeout=5) as resp:return resp.status,json.load(resp)
        except urllib.error.HTTPError as err:return err.code,json.load(err)

    def await_done(self,jid):
        for _ in range(90):
            req=urllib.request.Request(self.base+'/api/jobs/'+jid,headers={'X-CT-Token':self.srv.studio_token})
            with urllib.request.urlopen(req,timeout=3) as r: value=json.load(r)
            if value['status']!='running': return value
            time.sleep(.05)
        self.fail('job timeout')

    def test_three_distinct_models_and_source_reference_checks(self):
        preview=self.call('/api/preview',{'path':'.'})[1]
        payload={'mode':'review','provider':'ollama','model':'mock','strategy':'basic','path':'.',
                 'fingerprint':preview['fingerprint'],'consent':True,
                 'reviewers':[{'provider':'ollama','model':'one'},
                              {'provider':'ollama','model':'two'},
                              {'provider':'ollama','model':'three'}]}
        status,started=self.call('/api/run',payload)
        self.assertEqual(status,202)
        result=self.await_done(started['job_id'])
        self.assertEqual(result['status'],'completed')
        self.assertEqual([a['model'] for a in result['report']['agents']],
                         ['ollama:one','ollama:two','ollama:three'])
        self.assertTrue(result['report']['execution']['reference_audit'])
        self.assertEqual(len(self.clients[0].calls),4)

    def test_preview_includes_exact_reviewed_excerpt(self):
        status, payload = self.call('/api/preview', {'path': '.'})
        self.assertEqual(status, 200)
        self.assertIn('app.py', payload['source_excerpt'])
        self.assertIn('   2 | print(x)', payload['source_excerpt'])
        self.assertEqual(len(payload['fingerprint']), 64)
        self.assertEqual(payload['fingerprint'], self.call('/api/preview', {'path': '.'})[1]['fingerprint'])

    def test_ask_mode_refuses_obvious_credentials(self):
        text='Check password = "'+'a'*32+'" in my config'
        code, body=self.call('/api/run',{'mode':'ask','question':text,'consent':True})
        self.assertEqual(code,400,body)
        self.assertIn('credentials',body['error'].lower())

    def test_custom_reviewers_do_not_require_unused_default_provider_key(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY':''}):
            status, result=self.call('/api/run',{'mode':'ask','question':'What is next?',
                'consent':True,'provider':'openai','model':'unused',
                'reviewers':[{'provider':'ollama','model':'local-a'}]*3})
        self.assertEqual(status,202,result)
        self.assertEqual(self.await_done(result['job_id'])['status'],'completed')

    def test_invalid_model_configuration_is_rejected_not_500(self):
        for reviewers in ([], [{}]*3, [{'provider':[],'model':'foo'}]*3, None):
            with self.subTest(reviewers=reviewers):
                status,body=self.call('/api/run',{'mode':'ask','question':'Q','consent':True,'reviewers':reviewers})
                self.assertEqual(status,400,body)

    def test_new_ui_has_advanced_model_controls_and_csp_hash(self):
        page=_studio_template()
        self.assertIn('id="custom-models"',page)
        self.assertIn('id="reference-checks"',page)
        self.assertIn('opts.reviewers=',page)
        self.assertNotIn('unsafe-inline',page)


if __name__=='__main__':
    unittest.main()

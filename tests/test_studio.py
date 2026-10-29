"""v6 local browser workbench: authentication, preview, model flow and safety."""
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from consensustree.studio import StudioState, _studio_template, create_server, _local_ollama_url
from consensustree.metering import MeteredClient
from consensustree.providers import ModelSpec, _NoRedirect


class FakeClient:
    calls = 0
    def complete(self, spec, system, user):
        self.calls += 1
        return f"Model reply #{self.calls}. <script>window.__injected = true</script>\nNo tests were run."


class StudioHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'app.py').write_text('def add(a, b):\n    return a + b\n', encoding='utf-8')
        self.server = create_server(self.root, 0, client_factory=lambda max_calls: MeteredClient(FakeClient(), max_calls))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.base = f'http://127.0.0.1:{self.server.server_port}'
        self.token = self.server.studio_token

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def call(self, path, payload=None, token=True, headers=None):
        h={'X-CT-Token': self.token} if token else {}
        h.update(headers or {})
        if payload is not None:
            h['Content-Type'] = 'application/json'
            data = json.dumps(payload).encode('utf-8')
            method = 'POST'
        else:
            data = None
            method = 'GET'
        req=urllib.request.Request(self.base+path,headers=h,data=data,method=method)
        try:
            with urllib.request.urlopen(req,timeout=5) as r:
                raw=r.read()
                return r.status, raw if path.startswith('/?') or path.startswith('/api/dashboard/') else json.loads(raw), r.headers
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read()), e.headers

    def start_payload(self, **kwargs):
        preview=self.call('/api/preview',{'path':'.'})[1]
        data={'mode':'review','provider':'ollama','model':'llama3.2','strategy':'basic',
              'groups':2,'path':'.','consent':True,'fingerprint':preview['fingerprint']}
        data.update(kwargs)
        return data

    def await_job(self, job_id):
        for _ in range(100):
            code, body, _ = self.call('/api/jobs/'+job_id)
            if body['status']!='running':
                return body
            time.sleep(.04)
        self.fail('Job did not finish')

    def test_auth_host_and_origin_protection(self):
        self.assertEqual(self.call('/api/status', token=False)[0],403)
        self.assertEqual(self.call('/api/status',headers={'X-CT-Token':'incorrect'})[0],403)
        self.assertEqual(self.call('/api/status',headers={'Host':'evil.com'})[0],403)
        self.assertEqual(self.call('/api/demo',{},headers={'Origin':'https://malicious.site'})[0],403)
        self.assertEqual(self.call('/api/status')[0],200)

    def test_landing_page_strict_csp(self):
        code, content, headers = self.call('/?token='+self.token)
        self.assertEqual(code,200)
        self.assertIn(b'Intelligence together',content)
        self.assertIn(b'connect-src \'self\'',content)
        self.assertNotIn(b'unsafe-inline',content)
        self.assertRegex(content.decode(),r"script-src 'sha256-[A-Za-z0-9+/=]+'")
        self.assertEqual(headers['Referrer-Policy'],'no-referrer')
        self.assertEqual(headers['X-Frame-Options'],'DENY')

    def test_preview_never_calls_model_and_lists_files(self):
        c, body, _=self.call('/api/preview',{'path':'.'})
        self.assertEqual(c,200)
        self.assertEqual(body['files'],['app.py'])
        self.assertEqual(len(body['fingerprint']),64)
        self.assertEqual(body['warnings'],[])

    def test_prevents_path_traversal(self):
        self.assertEqual(self.call('/api/preview',{'path':'..'})[0],400)
        self.assertEqual(self.call('/api/preview',{'path':'does-not-exist'})[0],400)
        outside=self.root.parent/'consensustree-outside-studio-test.py'
        try:
            outside.write_text('hello',encoding='utf-8')
            (self.root/'out.py').symlink_to(outside)
            self.assertEqual(self.call('/api/preview',{'path':'out.py'})[0],400)
        finally:
            outside.unlink(missing_ok=True)

    def test_source_hash_invalidates_when_source_changes(self):
        d=self.start_payload()
        (self.root/'app.py').write_text('print("changed")\n')
        c,r,_=self.call('/api/run',d)
        self.assertEqual(c,400)
        self.assertIn('changed',r['error'])

    def test_requires_explicit_consent_and_preview(self):
        d=self.start_payload(consent=False)
        self.assertEqual(self.call('/api/run',d)[0],400)
        d=self.start_payload(fingerprint='')
        self.assertEqual(self.call('/api/run',d)[0],400)

    def test_secret_warning_blocks_model_call(self):
        (self.root/'app.py').write_text('API_KEY = "'+'123456789012345678901234567890'+'"\n')
        p=self.call('/api/preview',{'path':'.'})[1]
        self.assertTrue(p['warnings'])
        self.assertEqual(self.call('/api/run',self.start_payload())[0],400)

    def test_invalid_payloads_rejected(self):
        for changes in [{'mode':'execute'},{'provider':'invalid'},{'strategy':'unknown'},
                        {'groups':True},{'groups':0},{'model':'../../bad'},{'consent':'yes'}]:
            with self.subTest(changes=changes):
                c,body,_=self.call('/api/run',self.start_payload(**changes))
                self.assertEqual(c,400,body)

    def test_missing_keys_rejected_without_key_echo(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY':''}):
            c, body, _=self.call('/api/run',self.start_payload(provider='openai'))
            self.assertEqual(c,400)
            self.assertIn('OPENAI_API_KEY',body['error'])

    def test_end_to_end_mock_review_and_dashboard(self):
        c,run,_=self.call('/api/run',self.start_payload())
        self.assertEqual(c,202)
        r=self.await_job(run['job_id'])
        self.assertEqual(r['status'],'completed')
        self.assertEqual(len(r['report']['agents']),3)
        self.assertIn('Model reply',r['report']['synthesis'])
        self.assertEqual(r['report']['execution']['metering']['api_calls'],4)
        c,html,head=self.call('/api/dashboard/'+run['job_id'])
        self.assertEqual(c,200)
        self.assertIn(b'Decision Studio',html)
        self.assertNotIn(b'<script>window.__injected',html)
        self.assertIn(b'\\u003cscript\\u003e',html)
        self.assertIn('text/html',head['Content-Type'])

    def test_hierarchical_review(self):
        c,body,_=self.call('/api/run',self.start_payload(strategy='hierarchical',groups=2))
        self.assertEqual(c,202)
        r=self.await_job(body['job_id'])
        self.assertEqual(r['status'],'completed')
        self.assertEqual(len(r['report']['groups']),2)
        self.assertEqual(r['report']['execution']['metering']['api_calls'],9)

    def test_end_to_end_mock_decision(self):
        c,run,_=self.call('/api/run',{'mode':'ask','provider':'ollama','question':'Should we deploy?',
                                     'strategy':'basic','groups':2,'consent':True})
        self.assertEqual(c,202)
        r=self.await_job(run['job_id'])
        self.assertEqual(r['status'],'completed')
        self.assertEqual(r['report']['mode'],'ask')

    def test_demo_has_no_models_and_is_labeled(self):
        c,body,_=self.call('/api/demo',{})
        self.assertEqual(c,200)
        self.assertTrue(body['report']['demo'])
        self.assertIn('no AI',body['notice'])

    def test_unknown_job_and_methods(self):
        self.assertEqual(self.call('/api/jobs/missing')[0],404)
        self.assertEqual(self.call('/api/preview')[0],404)

    def test_web_studio_rejects_remote_ollama_url(self):
        with patch.dict(os.environ, {'OLLAMA_BASE_URL':'http://api.example.org:11434'}):
            with self.assertRaises(ValueError):
                _local_ollama_url()
        with patch.dict(os.environ, {'OLLAMA_BASE_URL':'http://127.0.0.1:11434'}):
            self.assertEqual(_local_ollama_url(), 'http://127.0.0.1:11434')

    def test_template_csp_and_redirect_handler(self):
        h=_studio_template()
        self.assertIn('connect-src \'self\'',h)
        self.assertNotIn('unsafe-inline',h)
        self.assertIsNone(_NoRedirect().redirect_request(None,None,302,None,{},'https://elsewhere.test'))


if __name__=='__main__':
    unittest.main()

"""Local hostile-input security regression; NOT an independent penetration test."""
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from consensustree.studio import create_server, _local_ollama_url, MAX_BODY
from consensustree.metering import MeteredClient

class HostileModel:
    def complete(self,*args):
        return 'Unverified report. <script>globalThis.pwned=true</script> demo.py:1'

class SecurityAssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.tmp.name)
        (cls.root/'demo.py').write_text('def add(a,b):\n return a+b\n',encoding='utf-8')
        cls.server=create_server(cls.root,0,client_factory=lambda limit:MeteredClient(HostileModel(),limit))
        cls.worker=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.worker.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
        cls.token=cls.server.studio_token
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.worker.join(timeout=3)
        cls.tmp.cleanup()

    def request(self,path,payload=None,headers=None,auth=True,raw=None):
        h={'X-CT-Token':self.token} if auth else {}
        h.update(headers or {})
        if payload is not None:
            data=json.dumps(payload).encode()
            h.setdefault('Content-Type','application/json')
        else:data=raw
        req=urllib.request.Request(self.base+path,headers=h,data=data,method='POST' if data is not None else 'GET')
        try:
            with urllib.request.urlopen(req,timeout=5) as res:
                return res.status,res.read(),dict(res.headers)
        except urllib.error.HTTPError as exc:
            return exc.code,exc.read(),dict(exc.headers)

    def preview(self):
        return json.loads(self.request('/api/preview',{'path':'.'})[1])

    def test_01_requires_capability_token(self):
        self.assertEqual(self.request('/api/status',auth=False)[0],403)
    def test_02_rejects_host_header(self):
        self.assertEqual(self.request('/api/status',headers={'Host':'evil.example'})[0],403)
    def test_03_rejects_foreign_origin(self):
        self.assertEqual(self.request('/api/preview',{'path':'.'},headers={'Origin':'https://evil.example'})[0],403)
    def test_04_rejects_path_traversal(self):
        self.assertEqual(self.request('/api/preview',{'path':'..'})[0],400)
    def test_05_rejects_wrong_content_type(self):
        self.assertEqual(self.request('/api/run',raw=b'{}',headers={'Content-Type':'text/plain'})[0],415)
    def test_06_rejects_oversized_body(self):
        self.assertEqual(self.request('/api/preview',raw=b'x'*(MAX_BODY+1),headers={'Content-Type':'application/json'})[0],413)
    def test_07_rejects_malformed_json(self):
        self.assertEqual(self.request('/api/preview',raw=b'{oops',headers={'Content-Type':'application/json'})[0],400)
    def test_08_requires_source_preview_consent(self):
        data={'mode':'review','provider':'ollama','model':'llama3.2','path':'.',
              'strategy':'basic','consent':True,'fingerprint':'invalid'}
        self.assertEqual(self.request('/api/run',data)[0],400)
    def test_09_blocks_secret_in_question(self):
        payload={'mode':'ask','provider':'ollama','model':'llama3.2','consent':True,
                 'question':'API_KEY="'+'X'*36+'"'}
        self.assertEqual(self.request('/api/run',payload)[0],400)
    def test_10_model_html_is_escaped_in_results(self):
        p=self.preview()
        payload={'mode':'review','provider':'ollama','model':'llama3.2','consent':True,
                 'path':'.','fingerprint':p['fingerprint']}
        code,data,_=self.request('/api/run',payload)
        self.assertEqual(code,202)
        job_id=json.loads(data)['job_id']
        for _ in range(60):
            status=json.loads(self.request('/api/jobs/'+job_id)[1])
            if status['status']!='running': break
            time.sleep(.02)
        self.assertEqual(status['status'],'completed')
        code,html,_=self.request('/api/dashboard/'+job_id)
        self.assertEqual(code,200)
        self.assertNotIn(b'<script>globalThis.pwned=true</script>',html)
    def test_11_blocks_remote_ollama_config(self):
        with patch.dict('os.environ',{'OLLAMA_BASE_URL':'http://evil.example:11434'}):
            with self.assertRaises(ValueError): _local_ollama_url()
    def test_12_defensive_response_headers(self):
        code,html,headers=self.request('/')
        self.assertEqual(code,200)
        self.assertEqual(headers['X-Frame-Options'],'DENY')
        self.assertEqual(headers['Referrer-Policy'],'no-referrer')
        self.assertEqual(headers['Cache-Control'],'no-store')
    def test_13_no_report_without_token(self):
        self.assertEqual(self.request('/api/jobs/arbitrary',auth=False)[0],403)
    def test_14_untrusted_path_preview_exclusion(self):
        (self.root/'hidden_secret.py').write_text('secret="test"')
        try:
            self.assertNotIn('hidden_secret.py',self.preview()['files'])
        finally:
            (self.root/'hidden_secret.py').unlink(missing_ok=True)

if __name__=='__main__':unittest.main()

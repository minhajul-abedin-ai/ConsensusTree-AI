"""Network adapter contract tests against an in-process fake Ollama API."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from consensustree.providers import LLMClient, ModelSpec, ProviderError, _post_json


class StubHandler(BaseHTTPRequestHandler):
    calls=[]
    def log_message(self,*args):
        pass
    def do_POST(self):
        length=int(self.headers['Content-Length'])
        body=json.loads(self.rfile.read(length))
        self.calls.append((self.path,body))
        if self.path=='/redirect':
            self.send_response(302)
            self.send_header('Location','/collector')
            self.end_headers()
            return
        if self.path=='/collector':
            self.send_response(500)
            self.end_headers()
            return
        output=json.dumps({'message':{'content':'Local model fixture response'}}).encode()
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(output)))
        self.end_headers()
        self.wfile.write(output)


class ProviderTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),StubHandler)
        cls.worker=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.worker.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.worker.join(timeout=3)

    def test_ollama_request_json_shape(self):
        StubHandler.calls=[]
        client=LLMClient(ollama_url=self.base,timeout=2)
        result=client.complete(ModelSpec('ollama','llama3.2'),'system prompt','user question')
        self.assertEqual(result,'Local model fixture response')
        path,body=StubHandler.calls[-1]
        self.assertEqual(path,'/api/chat')
        self.assertFalse(body['stream'])
        self.assertEqual(body['messages'][0]['role'],'system')
        self.assertEqual(body['messages'][1]['content'],'user question')

    def test_no_redirect_follows_sensitive_post(self):
        StubHandler.calls=[]
        with self.assertRaises(ProviderError):
            _post_json(self.base+'/redirect',{'Authorization':'Bearer test-secret'},{'hello':'world'},2)
        self.assertEqual([p for p,_ in StubHandler.calls],['/redirect'])


if __name__=='__main__':unittest.main()

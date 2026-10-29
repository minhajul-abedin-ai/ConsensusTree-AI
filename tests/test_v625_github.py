import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from consensustree.github import upsert_bot_pr_comment, MARKER


class Response:
    def __init__(self, data): self.body=json.dumps(data).encode()
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self, n=None): return self.body


class Api:
    def __init__(self, items): self.calls=[];self.items=items
    def open(self, request, timeout=15):
        self.calls.append((request.get_method(),request.full_url))
        if request.get_method()=='GET': return Response(self.items)
        return Response({'html_url':'https://github.com/me/project/pull/5#issuecomment-1'})


class GitHubUpsertTests(unittest.TestCase):
    def setup_report(self, root):
        report=Path(root)/'report.md';report.write_text('Summary: inspect the finding.');return report

    def test_creates_when_no_prior_bot_comment(self):
        with tempfile.TemporaryDirectory() as tmp:
            api=Api([{'id':12,'user':{'login':'other-user'},'body':MARKER+'old'}])
            with patch('consensustree.github.urllib.request.build_opener',return_value=api):
                result=upsert_bot_pr_comment('me/project',5,self.setup_report(tmp),token='fake-token')
            self.assertEqual(result['action'],'created')
            self.assertEqual(api.calls[-1][0],'POST')

    def test_updates_only_our_bot_comment(self):
        with tempfile.TemporaryDirectory() as tmp:
            api=Api([{'id':22,'user':{'login':'github-actions[bot]'},'body':MARKER+'old'}])
            with patch('consensustree.github.urllib.request.build_opener',return_value=api):
                result=upsert_bot_pr_comment('me/project',5,self.setup_report(tmp),token='fake-token')
            self.assertEqual(result['action'],'updated')
            self.assertEqual(api.calls[-1][0],'PATCH')
            self.assertTrue(api.calls[-1][1].endswith('/issues/comments/22'))

    def test_rejects_repository_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                upsert_bot_pr_comment('../repo',5,self.setup_report(tmp),token='fake-token')

if __name__=='__main__': unittest.main()

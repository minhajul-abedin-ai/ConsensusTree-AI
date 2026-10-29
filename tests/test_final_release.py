"""Final prerelease hardening tests: provider boundaries and trusted GitHub automation."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from consensustree.automation import run_github_pr_review
from consensustree.core import Council
from consensustree.hierarchy import HierarchicalCouncil
from consensustree.providers import LLMClient, ModelSpec, ProviderError, MAX_COMPLETION_CHARS


class ProviderSafetyTests(unittest.TestCase):
    def test_remote_plaintext_ollama_blocked(self):
        for url in ('http://api.example.org:11434', 'http://192.168.1.2:11434',
                    'http://169.254.169.254', 'http://localhost:11434/path',
                    'https://user:pass@api.example.org', 'https://api.example.org/?key=a'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                LLMClient(ollama_url=url)

    def test_local_plaintext_and_remote_tls_allowed(self):
        for url in ('http://127.0.0.1:11434', 'http://localhost:11434',
                    'http://[::1]:11434', 'https://models.example.org:443'):
            with self.subTest(url=url):
                self.assertIsInstance(LLMClient(ollama_url=url), LLMClient)

    def test_non_finite_and_zero_timeouts_blocked(self):
        for timeout in (0, -1, float('inf'), float('nan'), 601, '123'):
            with self.subTest(timeout=repr(timeout)), self.assertRaises(ValueError):
                LLMClient(timeout=timeout)

    def test_provider_large_completion_rejected_before_reporting_usage(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY':'fake-testing-value'}), patch(
            'consensustree.providers._post_json', return_value={
                'choices': [{'message': {'content': 'x' * (MAX_COMPLETION_CHARS+1)}}],
                'usage': {'prompt_tokens': 100, 'completion_tokens': 20}
            }):
            client=LLMClient()
            with self.assertRaisesRegex(ProviderError, 'exceeds'):
                client.complete(ModelSpec('openai','gpt-4.1-mini'), 's','u')
            self.assertIsNone(client.last_usage)

    def test_plugin_excessive_output_does_not_flow_into_chair(self):
        class Oversized:
            calls=0
            def complete(self, spec, system, user):
                self.calls+=1
                return 'x'*(MAX_COMPLETION_CHARS+1)
        client=Oversized()
        with self.assertRaises(ProviderError):
            Council([ModelSpec('ollama','llama3.2')],client=client).ask('Architect a queue')
        self.assertEqual(client.calls,3)

    def test_hierarchical_rejects_giant_specialist_completions(self):
        class Oversized:
            calls=0
            def complete(self, spec, system, user):
                self.calls+=1
                return 'x'*(MAX_COMPLETION_CHARS+1)
        client=Oversized()
        with self.assertRaises(ProviderError):
            HierarchicalCouncil([ModelSpec('ollama','llama3.2')], client=client,
                                groups=1, max_calls=5).ask('Choose a queue')
        self.assertEqual(client.calls,3)

class GitHubAutomationTrustTests(unittest.TestCase):
    def test_rejects_credentialed_pull_request_event(self):
        with self.assertRaisesRegex(ValueError, 'pull_request_target'):
            run_github_pr_review(env={'CONSENSUSTREE_AUTO_REVIEW':'true',
                                      'GITHUB_EVENT_NAME':'pull_request'})

    def test_workflow_uses_trusted_event_and_no_pr_head_checkout(self):
        text=Path(__file__).resolve().parents[1].joinpath('.github/workflows/ai-pr-review.yml').read_text()
        self.assertIn('pull_request_target:', text)
        self.assertNotIn('  pull_request:\n',text)
        self.assertIn('CONSENSUSTREE_AUTO_REVIEW',text)
        self.assertIn('ref: ${{ github.event.pull_request.base.sha }}',text)
        self.assertIn('git cat-file -e',text)
        self.assertNotIn('ref: ${{ github.event.pull_request.head.sha }}',text)

if __name__=='__main__': unittest.main()

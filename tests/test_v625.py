"""v6.2.5 regression coverage: live usage parsing, ranking, PR trust, benchmarks."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from consensustree.automation import parse_pr_event, run_github_pr_review
from consensustree.context import rank_candidates
from consensustree.core import Council
from consensustree.metering import MeteredClient, load_pricing
from consensustree.production_benchmark import run_production_cases, score_adjudicated
from consensustree.providers import LLMClient, ModelSpec, provider_usage, ProviderError
from consensustree.scanner import scan


class UsageTests(unittest.TestCase):
    def test_provider_reported_token_formats(self):
        inputs = [
            ('openai', {'usage': {'prompt_tokens': 11, 'completion_tokens': 7}}),
            ('anthropic', {'usage': {'input_tokens': 11, 'output_tokens': 7}}),
            ('gemini', {'usageMetadata': {'promptTokenCount': 11, 'candidatesTokenCount': 7}}),
            ('ollama', {'prompt_eval_count': 11, 'eval_count': 7}),
        ]
        for provider, response in inputs:
            with self.subTest(provider=provider):
                self.assertEqual(provider_usage(provider, response)['total_tokens'], 18)
        self.assertIsNone(provider_usage('openai', {'usage': {'prompt_tokens': 11}}))
        self.assertIsNone(provider_usage('openai', {'usage': {'prompt_tokens': True, 'completion_tokens': 4}}))

    def test_client_usage_and_reset_after_failed_request(self):
        with patch.dict('os.environ', {'OPENAI_API_KEY':'example-not-real-key'}), patch('consensustree.providers._post_json', return_value={
            'choices': [{'message': {'content': 'hello'}}], 'usage': {'prompt_tokens': 80, 'completion_tokens': 20}
        }):
            client = LLMClient()
            self.assertEqual(client.complete(ModelSpec('openai','gpt-4.1-mini'),'s','u'), 'hello')
            self.assertEqual(client.last_usage['input_tokens'], 80)
        with patch.dict('os.environ', {'OPENAI_API_KEY':'example-not-real-key'}), patch('consensustree.providers._post_json', side_effect=ProviderError('failure')):
            with self.assertRaises(ProviderError):
                client.complete(ModelSpec('openai','gpt-4.1-mini'),'s','u')
        self.assertIsNone(client.last_usage)

    def test_metering_uses_actual_counts_not_char_estimates_for_cost(self):
        class Fake:
            last_usage = {'source': 'provider_reported','input_tokens': 500000,
                          'output_tokens': 250000, 'total_tokens': 750000}
            def complete(self, spec, system, user): return 'answer'
        client = MeteredClient(Fake(), max_calls=1, pricing={
            'openai:gpt-4.1-mini': {'input_per_million_usd': 2.0,
                                    'output_per_million_usd': 8.0}
        })
        client.complete(ModelSpec('openai','gpt-4.1-mini'),'hi','there')
        usage = client.usage()
        self.assertEqual(usage['provider_reported_input_tokens'], 500000)
        self.assertEqual(usage['estimated_cost_usd'], 3.0)
        self.assertFalse(usage['actual_billed_cost_verified'])
        with self.assertRaises(ProviderError):
            client.complete(ModelSpec('openai','gpt-4.1-mini'),'s','u')

    def test_load_pricing_rejects_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'rates.json'
            p.write_text(json.dumps({'a':{'input_per_million_usd':2,'output_per_million_usd':10}}))
            self.assertIn('a',load_pricing(p))
            p.write_text(json.dumps({'a': {'input_per_million_usd': -1, 'output_per_million_usd':3}}))
            with self.assertRaises(ValueError): load_pricing(p)


class ContextTests(unittest.TestCase):
    @staticmethod
    def git(cwd, *args):
        return subprocess.run(['git','-C',str(cwd),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              check=True).stdout.decode().strip()

    def test_smart_context_prioritizes_changes_and_nearby_tests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.git(root,'init','-q')
            self.git(root,'config','user.email','example@example.com')
            self.git(root,'config','user.name','Test')
            for name in ('alpha.py','beta.py','test_alpha.py','zeta.py'):
                (root/name).write_text('def work():\n    return 1\n')
            (root/'.gitignore').write_text('SECRETS/\n')
            (root/'SECRETS').mkdir()
            (root/'SECRETS'/'hidden.py').write_text('password="fake"')
            self.git(root,'add','.')
            self.git(root,'commit','-qm','base')
            (root/'alpha.py').write_text('def work():\n    return 2\n')
            snap=scan(root,smart=True,max_files=2,max_chars=4000)
            self.assertEqual(snap.files[0], 'alpha.py')
            self.assertEqual(snap.selection['changed_files_detected'],1)
            self.assertEqual(len(snap.files),2)
            self.assertGreater(snap.omitted_files,0)
            self.assertNotIn('hidden.py',snap.text)

    def test_smart_context_handles_empty_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.git(root,'init','-q')
            (root/'app.py').write_text('def add(a,b):\n return a+b\n')
            snap=scan(root,smart=True)
            self.assertEqual(snap.files,['app.py'])
            self.assertEqual(snap.selection['changed_files_detected'],0)

    def test_focus_prefers_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'authentication.py').write_text('def login():\n return True\n')
            (root/'a.py').write_text('def run():\n return True\n')
            snap=scan(root,smart=True,focus='authentication',max_files=1)
            self.assertEqual(snap.files,['authentication.py'])


class AutomationTests(unittest.TestCase):
    @staticmethod
    def event(repo='me/repo',fork=False):
        return {'repository': {'full_name':repo}, 'pull_request': {
            'number':17,
            'base':{'sha':'a'*40,'repo':{'full_name':repo}},
            'head':{'sha':'b'*40,'repo':{'full_name':'another/repo' if fork else repo}}}}

    def test_fork_rejected(self):
        with self.assertRaisesRegex(ValueError,'Fork'):
            parse_pr_event(self.event(fork=True),expected_repo='me/repo')

    def test_non_sha_rejected(self):
        e=self.event();e['pull_request']['head']['sha']='--upload-secrets'
        with self.assertRaisesRegex(ValueError,'SHA'):
            parse_pr_event(e,expected_repo='me/repo')

    def test_automation_is_opt_in(self):
        self.assertEqual(run_github_pr_review(env={})['status'],'skipped')

    def test_end_to_end_pr_review_with_mocked_model_and_poster(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            ContextTests.git(root,'init','-q')
            ContextTests.git(root,'config','user.email','example@example.com')
            ContextTests.git(root,'config','user.name','Tester')
            (root/'app.py').write_text('def test():\n    return 1\n')
            ContextTests.git(root,'add','.')
            ContextTests.git(root,'commit','-qm','base')
            base=ContextTests.git(root,'rev-parse','HEAD')
            (root/'app.py').write_text('def test():\n    return 2\n')
            ContextTests.git(root,'add','.')
            ContextTests.git(root,'commit','-qm','head')
            head=ContextTests.git(root,'rev-parse','HEAD')
            # Privileged workflow runs trusted base code, with PR head as diff data.
            ContextTests.git(root,'checkout','--detach',base)
            e=self.event();e['pull_request']['base']['sha']=base;e['pull_request']['head']['sha']=head
            event_file=root/'event.json';event_file.write_text(json.dumps(e))
            env={'CONSENSUSTREE_AUTO_REVIEW':'true','GITHUB_EVENT_NAME':'pull_request_target',
                 'GITHUB_EVENT_PATH':str(event_file),'GITHUB_REPOSITORY':'me/repo',
                 'GITHUB_WORKSPACE':str(root),'CONSENSUSTREE_PROVIDER':'ollama'}
            class Model:
                calls=0
                def complete(self,spec,sys,user):
                    self.calls+=1
                    return 'Code review notes, hypothetical only.'
            model=Model(); posted=[]
            def poster(repo,n,report,*,token):
                posted.append(Path(report).read_text())
                return {'posted':True,'action':'created'}
            result=run_github_pr_review(env=env,client=model,post=poster)
            self.assertEqual(result['status'],'reviewed')
            self.assertEqual(model.calls,4)
            self.assertEqual(len(posted),1)
            self.assertIn('app.py',posted[0])


class ProductionBenchmarkTests(unittest.TestCase):
    def test_production_council_path_uses_real_roles(self):
        class Fake:
            calls=0
            def complete(self,*args): self.calls+=1;return 'Unverified review finding.'
        client=Fake()
        records=run_production_cases([{'id':'case1','source':'def f():\n return 1\n'}],
                 client,ModelSpec('ollama','llama3.2'),max_cases=1)
        self.assertEqual(client.calls,5)
        self.assertEqual(len(records['cases'][0]['council']['agents']),3)
        self.assertFalse(records['independently_scored'])
        self.assertFalse(records['genuine_provider_verified'])

    def test_independent_assessor_disagreements_not_hidden(self):
        records={'benchmark_type':'production_Council_vs_single_model','cases':[{'id':'case1'}]}
        notes=[{'id':'case1','arm':'baseline','assessor':a,'correct':True,'independent':True}
               for a in ('reviewer-one','reviewer-two')]
        notes += [{'id':'case1','arm':'council','assessor':'reviewer-one','correct':True,'independent':True},
                  {'id':'case1','arm':'council','assessor':'reviewer-two','correct':False,'independent':True}]
        score=score_adjudicated(records,notes)
        self.assertEqual(score['score']['baseline']['accuracy_on_consensus_cases'],1.0)
        self.assertIsNone(score['score']['council']['accuracy_on_consensus_cases'])
        self.assertEqual(score['score']['council']['disagreements'],1)
        self.assertFalse(score['independence_identity_verified'])

if __name__=='__main__': unittest.main()

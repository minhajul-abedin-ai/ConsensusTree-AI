"""Validate metrics without pretending to measure genuine model performance."""
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from consensustree.providers import ModelSpec
from consensustree.validation import (accuracy_metrics, live_probes, parse_verdict,
                                       run_accuracy)


class FakeModel:
    def __init__(self): self.calls = 0
    def complete(self,spec,system,user):
        self.calls += 1
        return 'An illustrative benchmark response.\nVERDICT: ISSUE'


class ValidationTests(unittest.TestCase):
    def test_suite_has_independent_safe_unsafe_labels(self):
        suite=json.loads((Path(__file__).parents[1]/'benchmarks/accuracy_cases.json').read_text())
        cases=suite['cases']
        self.assertEqual(len(cases), 50)
        self.assertEqual(len({c['id'] for c in cases}),50)
        self.assertEqual(sum(c['expected_issue'] for c in cases),25)
        self.assertEqual(len({c['family'] for c in cases}),10)
        for case in cases: self.assertNotIn('expected_issue',case['source'])

    def test_preflight_is_opt_in(self):
        result=live_probes(execute=False)
        self.assertFalse(result['all_live_verified'])
        self.assertTrue(all(p['status']=='not_run' for p in result['providers']))

    def test_missing_keys_skip_live_calls(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY':''}):
            output=live_probes(execute=True,providers=['openai'],timeout=1)
        self.assertEqual(output['providers'][0]['status'],'skipped')
        self.assertFalse(output['providers'][0]['live_verified'])

    def test_injected_client_cannot_pass_as_live(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY':'dummy'}):
            result=live_probes(execute=True,providers=['openai'],
                               client_factory=lambda p:FakeModel())
        self.assertEqual(result['providers'][0]['status'],'passed')
        self.assertFalse(result['providers'][0]['live_verified'])

    def test_verdict_strict_and_abstains(self):
        self.assertIs(parse_verdict('Not formatted'),None)
        self.assertTrue(parse_verdict('Reason.\nVERDICT: ISSUE'))
        self.assertFalse(parse_verdict('VERDICT: NO_ISSUE'))
        self.assertIsNone(parse_verdict('VERDICT: ISSUE\nVERDICT: NO_ISSUE'))

    def test_metrics_false_positives_and_false_negatives(self):
        rows=[{'expected_issue':True,'single':True},
              {'expected_issue':True,'single':False},
              {'expected_issue':False,'single':True},
              {'expected_issue':False,'single':False},
              {'expected_issue':False,'single':None}]
        out=accuracy_metrics(rows,arm='single')
        self.assertEqual((out['tp'],out['fp'],out['tn'],out['fn'],out['abstained']),
                         (1,1,1,1,1))
        self.assertEqual(out['precision'],.5)
        self.assertEqual(out['recall'],.5)
        self.assertEqual(out['coverage'],.8)

    def test_run_protocol_bounded_calls(self):
        suite=json.loads((Path(__file__).parents[1]/'benchmarks/accuracy_cases.json').read_text())
        client=FakeModel()
        result=run_accuracy(suite['cases'],client,ModelSpec('ollama','dummy'),max_cases=3,max_calls=10)
        self.assertEqual(client.calls,10)
        self.assertEqual(result['cases_attempted'],2)
        self.assertEqual(result['single_metrics']['scored'],2)
        self.assertEqual(result['council_metrics']['scored'],2)
        self.assertFalse(result['production_Council_directly_evaluated'])

    def test_failed_requests_consume_budget(self):
        class FailingClient:
            def __init__(self): self.calls=0
            def complete(self,*args):
                self.calls+=1
                raise RuntimeError("Network did not respond")
        cases=json.loads((Path(__file__).parents[1]/"benchmarks/accuracy_cases.json").read_text())["cases"]
        client=FailingClient()
        out=run_accuracy(cases,client,ModelSpec("ollama","dummy"),max_cases=3,max_calls=5)
        self.assertEqual(client.calls,1)
        self.assertEqual(out["api_calls_attempted"],1)
        self.assertEqual(out["cases_attempted"],1)

    def test_invalid_max_calls_and_bogus_label(self):
        with self.assertRaises(ValueError):
            accuracy_metrics([{'expected_issue':'yes','single':True}],arm='single')
        with self.assertRaises(ValueError):
            run_accuracy([{'source':'a','id':'a','category':'x','expected_issue':True}],FakeModel(),
                         ModelSpec('ollama','dummy'),max_cases=1,max_calls=0)

if __name__=='__main__': unittest.main()

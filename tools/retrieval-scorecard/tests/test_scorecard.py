import copy
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from retrieval_scorecard import InputError, evaluate, load, render_html


def fixture():
    return ({'schema_version':1,'queries':[{'id':'q1','judgments':[{'document_id':'a','relevance':3},{'document_id':'b','relevance':2},{'document_id':'c','relevance':0}]}]}, {'schema_version':1,'run_id':'synthetic','queries':[{'id':'q1','documents':['x','b','a']}]})

class ScoreTests(unittest.TestCase):
    def test_hand_calculated(self):
        q,r=fixture();item=evaluate(q,r,3)['queries'][0]
        self.assertEqual(item['precision_at_k'],2/3);self.assertEqual(item['recall_at_k'],1)
        self.assertEqual(item['rr_at_k'],.5)
        dcg=2/math.log2(3)+3/math.log2(4);ideal=3+2/math.log2(3)
        self.assertAlmostEqual(item['dcg_at_k'],dcg)
        self.assertAlmostEqual(item['ndcg_at_k'],dcg/ideal)
        self.assertEqual(item['ranking_evidence'][0]['relevance'],None)
        self.assertEqual(item['unjudged_at_k'],1)
    def test_cutoff_and_short_run(self):
        q,r=fixture();r['queries'][0]['documents']=['a']
        item=evaluate(q,r,4)['queries'][0]
        self.assertEqual(item['precision_at_k'],.25);self.assertEqual(item['recall_at_k'],.5)
        self.assertEqual(item['rr_at_k'],1)
        r['queries'][0]['documents']=['x','a']
        self.assertEqual(evaluate(q,r,1)['queries'][0]['rr_at_k'],0)
    def test_missing_and_extra_queries(self):
        q,r=fixture();r['queries'][0]['id']='not-in-qrels'
        result=evaluate(q,r,3)
        self.assertEqual(result['excluded_run_queries'],['not-in-qrels'])
        self.assertTrue(result['queries'][0]['missing_run_query'])
        self.assertEqual(result['summary']['mrr_at_k'],0)
    def test_zero_relevance_in_macro_denominator(self):
        q,r=fixture();r['queries'][0]['documents']=['a','b']
        q['queries'].append({'id':'empty','judgments':[]})
        result=evaluate(q,r,2)
        self.assertEqual(result['summary']['recall_at_k'],.5)
        self.assertEqual(result['summary']['ndcg_at_k'],.5)
        self.assertEqual(result['summary']['mrr_at_k'],.5)
    def test_ideal_order_scores_one_and_reverse_lower(self):
        q,r=fixture();r['queries'][0]['documents']=['a','b','c']
        self.assertEqual(evaluate(q,r,3)['summary']['ndcg_at_k'],1)
        r['queries'][0]['documents'].reverse()
        self.assertLess(evaluate(q,r,3)['summary']['ndcg_at_k'],1)
    def test_fractional_linear_gain(self):
        q,r=fixture();q['queries'][0]['judgments'][0]['relevance']=.5
        r['queries'][0]['documents']=['a','b']
        expected=(.5+2/math.log2(3))/(2+.5/math.log2(3))
        self.assertAlmostEqual(evaluate(q,r,2)['summary']['ndcg_at_k'],expected)
    def test_bounds_random_permutations(self):
        rng=random.Random(72)
        for _ in range(40):
            q,r=fixture();rng.shuffle(r['queries'][0]['documents'])
            for value in evaluate(q,r,rng.randint(1,6))['summary'].values():
                if isinstance(value,float): self.assertTrue(0<=value<=1)
    def test_input_not_mutated_and_deterministic(self):
        q,r=fixture();before=copy.deepcopy((q,r))
        self.assertEqual(evaluate(q,r),evaluate(q,r));self.assertEqual((q,r),before)
    def test_subnormal_ndcg_and_scale_invariance(self):
        q,r=fixture()
        q['queries'][0]['judgments']=[{'document_id':'a','relevance':5e-324}]
        r['queries'][0]['documents']=['x','a']
        tiny=evaluate(q,r,2)['queries'][0]
        self.assertAlmostEqual(tiny['ndcg_at_k'],1/math.log2(3))
        q['queries'][0]['judgments'][0]['relevance']=1
        self.assertEqual(tiny['ndcg_at_k'],evaluate(q,r,2)['queries'][0]['ndcg_at_k'])
        q,r=fixture();baseline=evaluate(q,r,3)['summary']['ndcg_at_k']
        for item in q['queries'][0]['judgments']:item['relevance']*=1e-200
        self.assertAlmostEqual(baseline,evaluate(q,r,3)['summary']['ndcg_at_k'])
    def test_invalid_grades(self):
        for grade in [True,-1,1001,'3',None,float('nan'),float('inf')]:
            q,r=fixture();q['queries'][0]['judgments'][0]['relevance']=grade
            with self.subTest(grade=grade),self.assertRaises(InputError):evaluate(q,r)
    def test_duplicate_queries_and_documents(self):
        for side,field in [('q','queries'),('r','queries'),('q','judgments'),('r','documents')]:
            q,r=fixture();obj=q if side=='q' else r
            seq=obj['queries'] if field=='queries' else obj['queries'][0][field]
            seq.append(copy.deepcopy(seq[0]))
            with self.subTest(side=side,field=field),self.assertRaises(InputError):evaluate(q,r)
    def test_invalid_schema_and_cutoff(self):
        for k in [True,0,-1,1.5,10001]:
            with self.subTest(k=k),self.assertRaises(InputError):evaluate(*fixture(),k)
        q,r=fixture();q['extra']='bad'
        with self.assertRaises(InputError):evaluate(q,r)
        q,r=fixture();r['schema_version']=True
        with self.assertRaises(InputError):evaluate(q,r)
    def test_loader_rejects_nonfinite_duplicates_depth_size(self):
        for text in ['{"a":1,"a":2}','{"a":1e400}','{"a":NaN}','['*110+'0'+']'*110,'x'*2000001]:
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'x.json';path.write_text(text)
                with self.assertRaises(InputError):load(path)
    def test_html_escapes_untrusted_ids_and_has_no_external_resources(self):
        q,r=fixture();r['run_id']='<script>alert(1)</script>'
        page=render_html(evaluate(q,r))
        self.assertNotIn('<script>',page);self.assertIn('&lt;script&gt;',page)
        self.assertNotIn('src=',page);self.assertNotIn('href=',page)
    def test_cli_reports_and_existing_directory(self):
        q,r=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'q.json').write_text(json.dumps(q));(root/'r.json').write_text(json.dumps(r))
            command=[sys.executable,'-m','retrieval_scorecard',str(root/'q.json'),str(root/'r.json'),'--k','3','--output-dir',str(root/'report')]
            first=subprocess.run(command,capture_output=True,text=True,timeout=10)
            self.assertEqual(first.returncode,0,first.stderr)
            result=root/'report/report.json';saved=result.read_bytes()
            self.assertEqual(json.loads(saved),evaluate(q,r,3))
            self.assertTrue((root/'report/report.html').exists())
            second=subprocess.run(command,capture_output=True,text=True,timeout=10)
            self.assertEqual(second.returncode,2);self.assertEqual(saved,result.read_bytes())

if __name__=='__main__':unittest.main()

import copy,json,random,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from splitguard import InputError,audit,load,normalized,render,tokens,validate

def row(i,text,split='train',**kw):return dict(id=str(i),text=text,split=split,**kw)
class AuditTests(unittest.TestCase):
    def test_exact_normalization_and_labels(self):
        r=audit([row(1,'ＡLPHA  Beta','train',label='yes'),row(2,'alpha beta','test',label='no')])
        f=r['findings'][0];self.assertEqual(f['kind'],'normalized_exact');self.assertTrue(f['label_conflict']);self.assertIsNone(f['jaccard'])
    def test_punctuation_retained_exact(self):
        r=audit([row(1,'one two three!'),row(2,'one two three?','test')])
        self.assertEqual(r['findings'][0]['kind'],'near_candidate')
    def test_within_split_not_reported(self):
        self.assertEqual(audit([row(1,'one two three'),row(2,'one two three')])['findings'],[])
    def test_short_near_coverage(self):
        r=audit([row(1,'hello'),row(2,'world','test')]);self.assertEqual(r['coverage']['near_ineligible_ids'],['1','2'])
    def test_jaccard(self):
        r=audit([row(1,'a b c d'),row(2,'a b c e','test')],.3,2)
        f=r['findings'][0];self.assertAlmostEqual(f['jaccard'],.5);self.assertEqual(f['shared_shingles'],2);self.assertEqual(f['union_shingles'],4)
    def test_threshold(self):
        self.assertEqual(audit([row(1,'a b c d'),row(2,'a b c e','test')],.6,2)['findings'],[])
    def test_missing_label_unknown(self):
        self.assertIsNone(audit([row(1,'a b c'),row(2,'a b c','test')])['findings'][0]['label_conflict'])
    def test_order_invariant_and_no_mutation(self):
        rows=[row(1,'a b c'),row(2,'a b c','test')];before=copy.deepcopy(rows)
        self.assertEqual(audit(rows),audit(list(reversed(rows))));self.assertEqual(rows,before)
    def test_hash_changes(self):
        a=audit([row(1,'hello')]);b=audit([row(1,'Hello')]);self.assertNotEqual(a['input_sha256'],b['input_sha256'])
    def test_index_matches_bruteforce(self):
        rng=random.Random(12);rows=[row(i,' '.join(rng.choices('abcdef',k=8)),['train','dev','test'][i%3]) for i in range(35)]
        expected=set()
        for a in rows:
            for b in rows:
                if a['id']>=b['id'] or a['split']==b['split']:continue
                aa=tokens(a['text']);bb=tokens(b['text']);sa=set(zip(aa,aa[1:]));sb=set(zip(bb,bb[1:]));score=len(sa&sb)/len(sa|sb)
                if normalized(a['text'])==normalized(b['text']) or score>=.25:expected.add((a['id'],b['id']))
        got={(f['left_id'],f['right_id']) for f in audit(rows,.25,2)['findings']};self.assertEqual(got,expected)
    def test_bad_schema(self):
        for rows in [[],[row(1,'')],[row(1,'ok',split='validation')],[row(1,'ok',label=1)],[row(1,'ok'),row(1,'other')],[row(1,'ok',unknown=True)],[row(1,'\ud800')]]:
            with self.assertRaises(InputError):validate(rows)
    def test_bad_parameters(self):
        for value in [0,-1,2,10**1000,True,float('nan'),float('inf'),'0.5']:
            with self.assertRaises(InputError):audit([row(1,'hi')],value)
        for n in [0,11,True,1.2]:
            with self.assertRaises(InputError):audit([row(1,'hi')],shingle_size=n)
    def test_budget_aborts_no_partial(self):
        with patch('splitguard.MAX_VISITS',0):
            with self.assertRaisesRegex(InputError,'no partial'):audit([row(1,'a b c'),row(2,'a b c','test')])
    def test_limits(self):
        with self.assertRaises(InputError):audit([row(1,'x '*4001)])
        with patch('splitguard.MAX_SHINGLES',0):
            with self.assertRaises(InputError):audit([row(1,'a b c')])
        with self.assertRaises(InputError):audit([row(i,'ok') for i in range(401)])
    def test_html_escape(self):
        r=audit([row('<script>','<script>alert(1)</script>'),row('2','<script>alert(1)</script>','test')]);s=render(r)
        self.assertNotIn('<script>',s);self.assertIn('&lt;script&gt;',s);self.assertIn('Cross-split pairs',s);self.assertIn('Not comparable',s);self.assertNotIn('Coverage: {',s)
    def test_jsonl_errors(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.jsonl'
            for text in ['{"id":"1","id":"2"}','[','{ "x":'+ '['*2000+'0'+']'*2000+'}']:
                p.write_text(text)
                with self.assertRaises(InputError):load(p)
            p.write_bytes(b'\xff')
            with self.assertRaises(InputError):load(p)
            p.write_bytes(b'x'*2000001)
            with self.assertRaises(InputError):load(p)
    def test_cli_outputs_and_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);inp=base/'in.jsonl';out=base/'out.json';page=base/'out.html';inp.write_text('\n'.join(json.dumps(r) for r in [row(1,'a b c'),row(2,'a b c','test')]))
            args=[sys.executable,'-m','splitguard',str(inp),'--json',str(out),'--html',str(page)]
            run=subprocess.run(args,capture_output=True);self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(len(json.loads(out.read_text())['findings']),1);self.assertIn('Split Guard',page.read_text())
            old=out.read_bytes();run=subprocess.run(args,capture_output=True);self.assertEqual(run.returncode,2);self.assertEqual(old,out.read_bytes())
            run=subprocess.run([sys.executable,'-m','splitguard',str(inp),'--json',str(base/'same'),'--html',str(base/'same')],capture_output=True);self.assertEqual(run.returncode,2)
if __name__=='__main__':unittest.main()

import copy,json,math,subprocess,sys,tempfile,unittest
from pathlib import Path
from regression_lab import *
def run(scores=(.4,.6),direction='higher'):
    return dict(schema_version=1,run_id='fixture',dataset_id='synthetic',dataset_version='v1',metric='bounded score',direction=direction,items=[dict(id=str(i),score=s,slice='all') for i,s in enumerate(scores)])
class Tests(unittest.TestCase):
    def test_means(self):
        r=compare(run(),run((.5,.4)),100)
        self.assertAlmostEqual(r['overall']['mean_improvement'],-.05)
        self.assertAlmostEqual(r['overall']['baseline_mean'],.5)
        self.assertEqual(r['overall']['signal'],'uncertain')
    def test_lower(self):
        r=compare(run(direction='lower'),run((.3,.5),'lower'),100)
        self.assertAlmostEqual(r['overall']['mean_improvement'],.1)
    def test_quantile(self):
        self.assertEqual(quantile([0,1],.25),.25)
        self.assertEqual(quantile([3],.5),3)
    def test_pairing_not_independent(self):
        r=compare(run((0,.2,.5,.8)),run((.1,.3,.6,.9)),100)
        for v in r['overall']['ci95']:self.assertAlmostEqual(v,.1)
    def test_reproducibility_and_order(self):
        a,b=run(),run((.1,.9))
        x=compare(a,b,100,1);a['items'].reverse();b['items'].reverse()
        self.assertEqual(x,compare(a,b,100,1))
    def test_coverage(self):
        b=run((.7,.8));b['items'][1]['id']='new'
        r=compare(run(),b,100)
        self.assertEqual(r['coverage']['baseline_only'],['1']);self.assertEqual(r['coverage']['candidate_only'],['new'])
        self.assertFalse(r['coverage']['complete']);self.assertIsNone(r['overall']['ci95'])
    def test_no_overlap(self):
        b=run();[x.update(id='new'+x['id']) for x in b['items']]
        r=compare(run(),b,100);self.assertEqual(r['overall']['signal'],'unavailable')
    def test_mismatch(self):
        for key,value in [('metric','other'),('dataset_version','v2'),('dataset_id','other'),('direction','lower')]:
            b=run();b[key]=value
            with self.assertRaises(InputError):compare(run(),b,100)
    def test_slice_mismatch(self):
        b=run();b['items'][0]['slice']='other'
        with self.assertRaises(InputError):compare(run(),b,100)
    def test_invalid_scores(self):
        for score in [True,None,'0.3',float('nan'),float('inf'),-.1,1.1,10**500]:
            a=run();a['items'][0]['score']=score
            with self.assertRaises(InputError):validate(a)
    def test_duplicate_id(self):
        a=run();a['items'][1]['id']='0'
        with self.assertRaises(InputError):validate(a)
    def test_settings(self):
        for kw in [dict(seed=-1),dict(seed=True),dict(resamples=1),dict(resamples=10000)]:
            with self.assertRaises(InputError):compare(run(),run(),**kw)
    def test_positive_signal(self):
        r=compare(run([.1]*25),run([.4,.5,.6,.7,.8]*5),100)
        self.assertEqual(r['overall']['signal'],'positive_interval')
    def test_constant_uncertain(self):
        r=compare(run([0]*25),run([1]*25),100)
        self.assertEqual(r['overall']['signal'],'uncertain')
    def test_html_escaped(self):
        a=run();a['run_id']='<script>alert(1)</script>'
        output=render(compare(a,run(),100));self.assertNotIn('<script>',output);self.assertIn('&lt;script&gt;',output)
    def test_strict_loading(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json'
            for text in ['{"a":1,"a":2}','['*200+'0'+']'*200,'x'*(MAX_BYTES+1)]:
                p.write_text(text)
                with self.assertRaises(InputError):load(p)
    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);a=d/'a.json';b=d/'b.json';o=d/'out.json';h=d/'out.html'
            a.write_text(json.dumps(run()));b.write_text(json.dumps(run((.7,.8))))
            args=[sys.executable,'-m','regression_lab',str(a),str(b),'--json',str(o),'--html',str(h),'--resamples','100']
            self.assertEqual(subprocess.run(args,capture_output=True).returncode,0)
            self.assertEqual(json.loads(o.read_text())['coverage']['matched'],2)
            original=o.read_text();self.assertEqual(subprocess.run(args,capture_output=True).returncode,2);self.assertEqual(o.read_text(),original)
            self.assertIn('Evaluation Regression Lab',h.read_text())
if __name__=='__main__':unittest.main()

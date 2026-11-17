import copy
import json
import tempfile
import unittest
from pathlib import Path
from reviewbench.core import DatasetError, load, summarize, total, validate
from reviewbench.report import render
from reviewbench.__main__ import main


def example():
    return {'id':'test-001','category':'editorial','prompt':'Summarize the date.',
            'source':'The fictional event is on May 4.','responses':{'A':'May 4.','B':'May 5.'},
            'scores':{'A':{'accuracy':5,'instructions':5,'clarity':5},'B':{'accuracy':1,'instructions':5,'clarity':5}},
            'winner':'A','rationale':'A preserves the source date; B changes it.',
            'evidence':[{'response':'B','quote':'May 5','reason':'The source says May 4.'}],
            'uncertainty':'No outside verification; this is fictional.','synthetic':True}

class ValidationTests(unittest.TestCase):
    def test_valid(self): self.assertEqual(validate(example()), [])
    def test_no_mutation(self):
        record=example(); before=copy.deepcopy(record); validate(record); self.assertEqual(record,before)
    def test_nonobject(self):
        for value in (None, [], 'text', 2): self.assertTrue(validate(value))
    def test_missing_fields(self):
        for key in example():
            record=example(); del record[key]; self.assertTrue(validate(record), key)
    def test_extra_field(self):
        record=example(); record['client']='private'; self.assertTrue(validate(record))
    def test_bad_scores(self):
        for value in (True,False,0,6,1.5,'5',None,[],{}):
            record=example(); record['scores']['A']['accuracy']=value; self.assertTrue(validate(record))
    def test_malformed_score_objects(self):
        for value in (None, [], {}, {'A':[],'B':{}}):
            record=example(); record['scores']=value; self.assertTrue(validate(record))
    def test_bad_winner(self):
        for value in ('B','tie','C',None,[],{}):
            record=example(); record['winner']=value; self.assertTrue(validate(record))
    def test_abstain(self):
        record=example(); record['winner']='abstain'; self.assertFalse(validate(record))
    def test_tie(self):
        record=example(); record['scores']['B']=record['scores']['A'].copy(); record['winner']='tie'; self.assertFalse(validate(record))
    def test_bad_evidence(self):
        for value in ([],None,[{}],[{'response':[], 'quote':'x','reason':'why'}],[{'response':'B','quote':'not present','reason':'why'}]):
            record=example(); record['evidence']=value; self.assertTrue(validate(record))
    def test_empty_text(self):
        for key in ('prompt','source','rationale','uncertainty'):
            record=example(); record[key]=' '; self.assertTrue(validate(record))
    def test_non_synthetic(self):
        for value in (False,1,'true'):
            record=example(); record['synthetic']=value; self.assertTrue(validate(record))
    def test_invalid_ids(self):
        for value in ('A', 'with space', '<script>', 'x'*65):
            record=example(); record['id']=value; self.assertTrue(validate(record))
    def test_total(self): self.assertEqual(total(example()['scores']['A']),20)
    def test_html_escapes_all_content(self):
        record=example(); record['prompt']='<script>alert(1)</script>'; record['responses']['A']='<img onerror="boom">'
        html=render([record]); self.assertNotIn('<script>',html); self.assertNotIn('<img',html); self.assertIn('&lt;script&gt;',html)
    def test_report_is_offline(self):
        html=render([example()]); self.assertNotIn('<script',html); self.assertNotIn('src=',html)
    def test_summary(self):
        result=summarize([example()]); self.assertEqual(result['decisions'],{'A':1,'B':0,'tie':0,'abstain':0})

class FileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.path=Path(self.tmp.name)/'cases.jsonl'
    def write(self,text): self.path.write_text(text,encoding='utf-8')
    def test_roundtrip(self): self.write(json.dumps(example())); self.assertEqual(load(self.path),[example()])
    def test_blank_lines(self): self.write('\n'+json.dumps(example())+'\n\n'); self.assertEqual(len(load(self.path)),1)
    def test_empty(self):
        self.write('  \n'); self.assertRaises(DatasetError,load,self.path)
    def test_duplicate_ids(self):
        self.write((json.dumps(example())+'\n')*2); self.assertRaisesRegex(DatasetError,'line 2.*duplicate',load,self.path)
    def test_duplicate_json_keys(self):
        self.write('{"id":"one","id":"two"}'); self.assertRaisesRegex(DatasetError,'duplicate JSON key',load,self.path)
    def test_nonfinite(self):
        for value in ('NaN','Infinity','-Infinity'):
            self.write('{"score":'+value+'}'); self.assertRaises(DatasetError,load,self.path)
    def test_malformed_json(self):
        self.write('{broken'); self.assertRaisesRegex(DatasetError,'line 1',load,self.path)
    def test_cli_writes_outputs(self):
        self.write(json.dumps(example())); html=self.path.with_suffix('.html'); out=self.path.with_suffix('.json')
        self.assertEqual(main([str(self.path),'--html',str(html),'--json',str(out)]),0)
        self.assertIn('ReviewBench',html.read_text()); self.assertEqual(json.loads(out.read_text())['records'],1)
    def test_cli_no_output_on_invalid_input(self):
        self.write('{}'); out=self.path.with_suffix('.html'); self.assertEqual(main([str(self.path),'--html',str(out)]),1); self.assertFalse(out.exists())
    def test_cli_no_input_overwrite(self):
        self.write(json.dumps(example()))
        with self.assertRaises(SystemExit): main([str(self.path),'--html',str(self.path)])
        self.assertEqual(load(self.path),[example()])
    def test_missing_second_output_directory_does_not_write_first(self):
        self.write(json.dumps(example())); out=self.path.with_suffix('.html')
        self.assertEqual(main([str(self.path),'--html',str(out),'--json',str(self.path.parent/'missing'/'summary.json')]),1)
        self.assertFalse(out.exists())
    def test_invalid_second_output_preserves_existing_first(self):
        self.write(json.dumps(example())); out=self.path.with_suffix('.html'); out.write_text('previous')
        self.assertEqual(main([str(self.path),'--html',str(out),'--json',str(self.path.parent)]),1)
        self.assertEqual(out.read_text(),'previous')
    def test_cli_missing_input(self): self.assertEqual(main([str(self.path)]),1)
    def test_repository_dataset(self):
        path=Path(__file__).resolve().parents[1]/'data/cases.jsonl'
        self.assertGreaterEqual(len(load(path)),10)

if __name__=='__main__': unittest.main()

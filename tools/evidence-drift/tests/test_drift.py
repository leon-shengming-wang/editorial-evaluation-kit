import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from evidence_drift import SnapshotError, compare, content_hash, load, validate

ROOT = Path(__file__).resolve().parents[1]

class DriftTests(unittest.TestCase):
    def setUp(self):
        self.before = load(ROOT/'examples/before.json')
        self.after = load(ROOT/'examples/after.json')
    def test_changes_and_dependencies(self):
        result = compare(self.before, self.after)
        self.assertEqual([(c['id'], c['kind']) for c in result['source_changes']], [('access','added'),('hours','changed'),('ticket','removed')])
        visit = next(a for a in result['answer_changes'] if a['id']=='visit')
        self.assertEqual(visit['changed_source_ids'], ['hours','ticket'])
        self.assertTrue(visit['review_required'])
    def test_no_change(self):
        result = compare(self.before, self.before)
        self.assertEqual(result['source_changes'], [])
        self.assertEqual(result['answer_changes'], [])
    def test_hash_and_order(self):
        reordered = copy.deepcopy(self.before)
        reordered['sources'].reverse()
        reordered['answers'][0]['source_ids'].reverse()
        self.assertEqual(compare(self.before, self.after), compare(reordered, self.after))
        self.assertNotEqual(content_hash('Text'),content_hash('Text '))
    def test_metadata_change_not_content_change(self):
        after = copy.deepcopy(self.before); after['sources'][0]['title']='New title'
        item = compare(self.before,after)['source_changes'][0]
        self.assertEqual(item['changed_fields'],['title'])
        self.assertEqual(item['before_content_sha256'], item['after_content_sha256'])
        self.assertEqual(compare(self.before,after)['answer_changes'][0]['kind'],'unchanged')
    def test_schema_rejections(self):
        mutations = [lambda s:s.update(schema_version=True),lambda s:s.update(extra=1),lambda s:s.update(captured_at='2026-01-01'),lambda s:s['sources'].append(s['sources'][0]),lambda s:s['answers'].append(s['answers'][0]),lambda s:s['answers'][0].update(source_ids=['absent']),lambda s:s['answers'][0].update(source_ids=['hours','hours']),lambda s:s['sources'][0].update(url='file:///tmp/x'),lambda s:s['sources'][0].update(url='https://name:secret@example.org'),lambda s:s['sources'][0].update(content=123)]
        for mutate in mutations:
            data=copy.deepcopy(self.before);mutate(data)
            with self.subTest(data=data),self.assertRaises(SnapshotError):validate(data)
    def test_duplicate_keys_and_deep_json(self):
        for text in ('{"schema_version":1,"schema_version":2}', '['*110+'0'+']'*110):
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'input.json';path.write_text(text)
                with self.assertRaises(SnapshotError):load(path)
    def test_cli_and_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'report.json'
            cmd=[sys.executable,'-m','evidence_drift',str(ROOT/'examples/before.json'),str(ROOT/'examples/after.json'),'--output',str(output)]
            first=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=10)
            self.assertEqual(first.returncode,0,first.stderr)
            saved=output.read_bytes();self.assertEqual(json.loads(saved),compare(self.before,self.after))
            second=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=10)
            self.assertEqual(second.returncode,2);self.assertEqual(saved,output.read_bytes())
    def test_unchanged_text_with_changed_source_needs_review(self):
        after=copy.deepcopy(self.before);after['sources'][0]['content']='New hours.'
        item=compare(self.before,after)['answer_changes'][0]
        self.assertEqual(item['changed_fields'],[]);self.assertTrue(item['review_required'])

if __name__=='__main__':unittest.main()

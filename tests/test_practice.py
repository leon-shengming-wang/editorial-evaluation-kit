import copy
import tempfile
import unittest
from pathlib import Path
from reviewbench.core import load
from reviewbench.practice import input_fingerprint, literal, main, worksheet

ROOT = Path(__file__).resolve().parents[1]

class PracticeTests(unittest.TestCase):
    def setUp(self):
        self.records = load(ROOT / 'data/cases.jsonl')
    def test_reference_labels_and_rationales_omitted(self):
        record = copy.deepcopy(self.records[0])
        record['rationale'] = 'SECRET_REFERENCE_REASON'
        record['uncertainty'] = 'SECRET_REFERENCE_LIMIT'
        record['winner'] = 'SECRET_REFERENCE_WINNER'
        record['scores'] = {'SECRET_REFERENCE_SCORE': 999}
        record['evidence'] = [{'reason': 'SECRET_REFERENCE_EVIDENCE'}]
        text = worksheet([record])
        self.assertNotIn('SECRET_REFERENCE', text)
        self.assertNotIn('Weighted score', text)
        self.assertIn(record['source'], text)
        self.assertIn(record['responses']['A'], text)
    def test_input_fingerprint_ignores_reference_changes(self):
        record = copy.deepcopy(self.records[0])
        original = input_fingerprint(record)
        record['winner'] = 'tie'
        record['rationale'] = 'Changed reference only'
        self.assertEqual(original, input_fingerprint(record))

    def test_input_fingerprint_detects_source_change(self):
        record = copy.deepcopy(self.records[0])
        original = input_fingerprint(record)
        record['source'] += ' New information.'
        self.assertNotEqual(original, input_fingerprint(record))

    def test_category_selection(self):
        text = worksheet(self.records, ['language', 'audio'])
        self.assertIn('lg-001 / language', text)
        self.assertNotIn('ed-001 / editorial', text)
    def test_no_matching_records(self):
        with self.assertRaises(ValueError): worksheet(self.records, ['unknown'])
    def test_embedded_fence_is_literal(self):
        text = literal('before```\n<script>alert(1)</script>\n```after')
        self.assertTrue(text.startswith('````\n'))
        self.assertTrue(text.endswith('\n````'))
    def test_does_not_mutate_records(self):
        before = copy.deepcopy(self.records)
        worksheet(self.records)
        self.assertEqual(before, self.records)
    def test_cli_create_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'worksheet.md'
            argv = [str(ROOT / 'data/cases.jsonl'), '--category', 'audio', '--output', str(p)]
            self.assertEqual(main(argv), 0)
            initial = p.read_text()
            with self.assertRaises(SystemExit): main(argv)
            self.assertEqual(initial, p.read_text())
    def test_refuse_input_overwrite(self):
        p = str(ROOT / 'data/cases.jsonl')
        with self.assertRaises(SystemExit): main([p, '--output', p])

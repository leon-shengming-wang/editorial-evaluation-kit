import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from reviewbench.agreement import audit, compare, main
from reviewbench.audit import AuditStore
from reviewbench.core import load


class AgreementTests(unittest.TestCase):
    def rows(self, left, right):
        return [(str(i), who, label, 'reason') for who, labels in [('one', left), ('two', right)]
                for i, label in enumerate(labels)]

    def test_known_kappa(self):
        r = compare(self.rows(['A', 'A', 'B', 'B'], ['A', 'B', 'B', 'B']), 'one', 'two')
        self.assertEqual(r['observed_agreement'], .75)
        self.assertEqual(r['chance_agreement'], .5)
        self.assertEqual(r['cohens_kappa'], .5)
        self.assertEqual(len(r['disagreements']), 1)

    def test_perfect(self):
        self.assertEqual(compare(self.rows(['A', 'B'], ['A', 'B']), 'one', 'two')['cohens_kappa'], 1)

    def test_complete_disagreement(self):
        self.assertEqual(compare(self.rows(['A', 'B'], ['B', 'A']), 'one', 'two')['cohens_kappa'], -1)

    def test_constant(self):
        r = compare(self.rows(['A'], ['A']), 'one', 'two')
        self.assertEqual(r['kappa_status'], 'constant_identical_labels')
        self.assertIsNone(r['cohens_kappa'])

    def test_no_overlap(self):
        r = compare([('x', 'one', 'A', 'r'), ('y', 'two', 'B', 'r')], 'one', 'two')
        self.assertEqual(r['left_only_cases'], ['x'])
        self.assertEqual(r['right_only_cases'], ['y'])
        self.assertIsNone(r['observed_agreement'])

    def test_abstain_is_not_missing(self):
        r = compare(self.rows(['abstain', 'tie'], ['A', 'tie']), 'one', 'two')
        self.assertEqual(r['shared_cases'], 2)
        self.assertEqual(r['observed_agreement'], .5)

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            compare(self.rows(['A'], ['A']) + [('0', 'one', 'B', 'r')], 'one', 'two')

    def test_other_reviewers_ignored(self):
        r = compare(self.rows(['A'], ['A']) + [('0', 'three', 'B', 'r')], 'one', 'two')
        self.assertEqual(r['exact_agreements'], 1)

    def test_invalid_reviewers(self):
        for a, b in [('one', 'one'), ('', 'two'), ('one', ' ')]:
            with self.assertRaises(ValueError): compare([], a, b)

    def test_invalid_label(self):
        with self.assertRaises(ValueError): compare([('x', 'one', 'yes', 'r')], 'one', 'two')

    def test_latest_and_readonly(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'reviews.sqlite'
            records = load('data/cases.jsonl')
            case = records[0]['id']
            with AuditStore(p) as store:
                store.import_cases(records)
                store.add_review(case, 'one', 'A', 'old')
                store.add_review(case, 'one', 'B', 'new')
                store.add_review(case, 'two', 'A', 'different')
            before = p.read_bytes()
            r = audit(p, 'one', 'two')
            self.assertEqual(r['disagreements'][0]['left_reason'], 'new')
            self.assertEqual(p.read_bytes(), before)
            out = Path(d) / 'report.json'
            self.assertEqual(main([str(p), 'one', 'two', '--output', str(out)]), 0)
            self.assertEqual(json.loads(out.read_text())['shared_cases'], 1)
            with self.assertRaises(SystemExit): main([str(p), 'one', 'two', '--output', str(out)])
            self.assertEqual(p.read_bytes(), before)
            html = Path(d) / 'report.html'
            self.assertEqual(main([str(p), 'one', 'two', '--html', str(html)]), 0)
            self.assertIn('Pairwise review audit', html.read_text())
            with self.assertRaises(SystemExit): main([str(p), 'one', 'two', '--html', str(html)])

    def test_missing_database_not_created(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'absent.sqlite'
            with self.assertRaises(FileNotFoundError): audit(p, 'one', 'two')
            self.assertFalse(p.exists())

    def test_invalid_schema(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'empty.sqlite'
            sqlite3.connect(p).close()
            with self.assertRaises(sqlite3.OperationalError): audit(p, 'one', 'two')

    def test_round_trip_json_safe(self):
        r = compare(self.rows([], []), 'one', 'two')
        self.assertEqual(json.loads(json.dumps(r, allow_nan=False)), r)

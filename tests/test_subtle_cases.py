"""Regression checks for nuanced synthetic examples, not proof of judgment quality."""
import unittest
from pathlib import Path
from reviewbench.core import load, total, validate

class SubtleCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {r['id']: r for r in load(Path(__file__).resolve().parents[1] / 'data/cases.jsonl')}

    def test_headline_word_count_matches_rationale(self):
        r = self.cases['ed-001']
        self.assertEqual(len(r['responses']['B'].split()), 10)
        self.assertIn('10 whitespace-delimited words', r['rationale'])
        longer = self.cases['ed-004']
        self.assertEqual(len(longer['responses']['B'].split()), 27)
        self.assertIn('27 whitespace-delimited words', longer['rationale'])

    def test_punctuation_lab_calibration_is_explicit(self):
        doc = (Path(__file__).resolve().parents[1] / 'docs/LANGUAGE-AUDIO-REVIEW.md').read_text()
        self.assertIn('A accuracy 2, instructions 3, clarity 5, total **12**', doc)
        self.assertEqual(total({'accuracy': 2, 'instructions': 3, 'clarity': 5}), 12)
        self.assertIn('Neither version explicitly grants permission after arrival.', doc)

    def test_cutoff_case_marks_both_flawed(self):
        r = self.cases['fc-004']
        self.assertEqual((total(r['scores']['A']), total(r['scores']['B'])), (14, 13))
        self.assertEqual(r['winner'], 'A')
        self.assertIn('not publication-ready', r['rationale'])

    def test_language_category_and_equal_scores(self):
        r = self.cases['lg-001']
        self.assertEqual(r['category'], 'language')
        self.assertEqual(validate(r), [])
        self.assertEqual(r['winner'], 'tie')
        self.assertEqual(total(r['scores']['A']), total(r['scores']['B']))
        self.assertIn('No original Mandarin', r['uncertainty'])

    def test_abstain_despite_score_advantage(self):
        r = self.cases['au-004']
        self.assertGreater(total(r['scores']['A']), total(r['scores']['B']))
        self.assertEqual(r['winner'], 'abstain')
        self.assertEqual(validate(r), [])

    def test_new_case_evidence_and_ascii(self):
        for key in ('fc-004', 'lg-001', 'au-004'):
            r = self.cases[key]
            for e in r['evidence']:
                self.assertIn(e['quote'], r['responses'][e['response']])
            for field in ('prompt', 'source', 'rationale', 'uncertainty'):
                self.assertTrue(r[field].isascii())

if __name__ == '__main__':
    unittest.main()

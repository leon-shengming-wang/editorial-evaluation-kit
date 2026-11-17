"""Reproducible shape fuzzing of JSON-compatible values, not a security proof."""
import copy
import unittest
from reviewbench.core import validate
from test_core import example

class ShapeMutationTests(unittest.TestCase):
    def test_top_level_mutations_do_not_crash(self):
        values=[None,False,0,1.5,'',[],{},['nested'],{'nested':[]}]
        for field in example():
            for value in values:
                with self.subTest(field=field,value=value):
                    record=example(); record[field]=copy.deepcopy(value)
                    self.assertIsInstance(validate(record),list)
    def test_evidence_mutations_do_not_crash(self):
        values=[None,False,0,1.5,'',[],{},['nested'],{'nested':[]}]
        for field in ('response','quote','reason'):
            for value in values:
                with self.subTest(field=field,value=value):
                    record=example(); record['evidence'][0][field]=copy.deepcopy(value)
                    self.assertIsInstance(validate(record),list)
    def test_score_side_mutations_do_not_crash(self):
        for side in ('A','B'):
            for value in (None,False,0,1.5,'',[],{},['nested'],{'nested':[]}):
                with self.subTest(side=side,value=value):
                    record=example(); record['scores'][side]=copy.deepcopy(value)
                    self.assertTrue(validate(record))

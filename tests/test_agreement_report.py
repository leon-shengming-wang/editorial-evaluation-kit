import unittest
from reviewbench.agreement import compare
from reviewbench.agreement_report import render

class AgreementReportTests(unittest.TestCase):
    def test_escape_and_scope(self):
        r = compare([('x', 'one', 'A', '<script>alert(1)</script>'), ('x', 'two', 'B', '& bad')], 'one', 'two')
        page = render(r, title='<title>', provenance='<img src=x>')
        self.assertNotIn('<script>', page)
        self.assertIn('&lt;script&gt;', page)
        self.assertIn('&lt;img src=x&gt;', page)
        self.assertIn('lang="en"', page)
        self.assertIn('scope="row"', page)

    def test_empty(self):
        page = render(compare([], 'one', 'two'))
        self.assertIn('Not defined', page)
        self.assertIn('No differing labels', page)

    def test_deterministic_and_offline(self):
        r = compare([], 'one', 'two')
        self.assertEqual(render(r), render(r))
        self.assertNotIn('https://', render(r))

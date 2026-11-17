import copy
import json
import tempfile
import unittest
from pathlib import Path
from preflight.core import contrast,inspect,validate
from preflight.render import svg,html
from preflight.__main__ import main,strict_object

ROOT=Path(__file__).resolve().parents[1]
def good(): return json.loads((ROOT/'examples/good.json').read_text())
class Checks(unittest.TestCase):
    def test_black_white(self): self.assertAlmostEqual(contrast('#000000','#ffffff'),21)
    def test_same_color(self): self.assertAlmostEqual(contrast('#123456','#123456'),1)
    def test_symmetry(self): self.assertEqual(contrast('#aabbcc','#001122'),contrast('#001122','#aabbcc'))
    def test_bad_color(self):
        for value in ('red','#fff','javascript:x',None):
            with self.assertRaises(ValueError): contrast(value,'#ffffff')
    def test_good(self): self.assertEqual(inspect(good()),[])
    def test_bad_fixture(self):
        codes={f['code'] for f in inspect(json.loads((ROOT/'examples/bad.json').read_text()))}
        self.assertTrue({'CONTRAST','OUT_OF_BOUNDS','FONT_FAMILY','BODY_SIZE','HIERARCHY','BOX_OVERLAP','ROLE_FONT_VARIATION'}<=codes)
    def test_safe_margin_boundary(self):
        s=good();s['boxes'][0]['x']=s['rules']['safe_margin'];self.assertNotIn('SAFE_MARGIN',[f['code'] for f in inspect(s)])
        s['boxes'][0]['x']-=0.1;self.assertIn('SAFE_MARGIN',[f['code'] for f in inspect(s)])
    def test_touching_edges_not_overlap(self):
        s=good(); a,b=s['boxes'][:2]; b['y']=a['y']+a['height'];self.assertNotIn('BOX_OVERLAP',[f['code'] for f in inspect(s)])
    def test_duplicate_id(self):
        s=good();s['boxes'][1]['id']=s['boxes'][0]['id'];self.assertTrue(validate(s))
    def test_boolean_numeric(self):
        s=good();s['canvas']['width']=True;self.assertTrue(validate(s))
    def test_nonfinite(self):
        for n in (float('nan'),float('inf'),float('-inf')):
            s=good();s['boxes'][0]['x']=n;self.assertTrue(validate(s))
    def test_unknown_fields(self):
        s=good();s['canvas']['texture']='unknown';self.assertTrue(validate(s))
    def test_font_injection(self):
        s=good();s['boxes'][0]['font_family']='Arial" onload="x';self.assertTrue(validate(s))
    def test_svg_escape(self):
        s=good();s['boxes'][0]['text']='<script>alert(1)</script>';s['title']='<img src=x>'
        out=svg(s);self.assertNotIn('<script>',out);self.assertNotIn('<img',out);self.assertIn('&lt;script&gt;',out)
    def test_report_offline(self):
        out=html(good(),[]);self.assertNotIn('<script',out);self.assertNotIn('src=',out)
    def test_no_mutation(self):
        s=good();original=copy.deepcopy(s);inspect(s);self.assertEqual(s,original)
    def test_empty_boxes(self):
        s=good();s['boxes']=[];self.assertTrue(validate(s))
    def test_invalid_margin(self):
        s=good();s['rules']['safe_margin']=1000;self.assertTrue(validate(s))
    def test_duplicate_json_key(self):
        with self.assertRaises(ValueError): json.loads('{"x":1,"x":2}',object_pairs_hook=strict_object)
    def test_cli_good(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(main([str(ROOT/'examples/good.json'),'--output',d]),0)
            self.assertTrue((Path(d)/'specimen.svg').exists())
    def test_cli_bad(self):
        with tempfile.TemporaryDirectory() as d:self.assertEqual(main([str(ROOT/'examples/bad.json'),'--output',d]),1)
    def test_cli_invalid(self):
        with tempfile.TemporaryDirectory() as d:self.assertEqual(main([str(Path(d)/'missing'),'--output',d]),2)
    def test_mutation_shapes(self):
        for key in good():
            for value in (None,[],{},False,0,''):
                s=good();s[key]=value;self.assertIsInstance(validate(s),list)

    def test_invalid_output_keeps_existing_report(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'report.html').write_text('previous'); (root/'findings.json').mkdir()
            self.assertEqual(main([str(ROOT/'examples/good.json'),'--output',d]),2)
            self.assertEqual((root/'report.html').read_text(),'previous')
    def test_input_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'findings.json'; source.write_text(json.dumps(good()))
            self.assertEqual(main([str(source),'--output',d]),2)
            self.assertEqual(json.loads(source.read_text()),good())

    def test_huge_integer_rejected_without_overflow(self):
        from preflight.core import number
        self.assertFalse(number(10**1000))
        self.assertFalse(number(-(10**1000)))
        s=good(); s['boxes'][0]['x']=10**1000
        self.assertTrue(validate(s))
        with self.assertRaises(ValueError): inspect(s)
        with self.assertRaises(ValueError): svg(s)
    def test_extreme_float_geometry_rejected(self):
        for field in ('x','y','width','height','font_px'):
            for value in (1e308,-1e308,100001):
                s=good();s['boxes'][0][field]=value
                self.assertTrue(validate(s))
                with self.assertRaises(ValueError): svg(s)
    def test_extreme_rule_values_rejected(self):
        for field in ('safe_margin','body_min_px','headline_ratio'):
            s=good();s['rules'][field]=10**1000
            self.assertTrue(validate(s))
    def test_huge_json_integer_cli_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'input.json'; s=good();s['boxes'][0]['x']=10**1000
            source.write_text(json.dumps(s))
            self.assertEqual(main([str(source),'--output',str(Path(d)/'output')]),2)
            self.assertFalse((Path(d)/'output').exists())

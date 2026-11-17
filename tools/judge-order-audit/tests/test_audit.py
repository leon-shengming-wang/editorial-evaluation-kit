import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('order_audit', ROOT / 'audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def run(value):
    return None if value is None else {'verdict': value}


def sample(a='first', b='second'):
    return {'schema_version': 1, 'data_kind': 'synthetic', 'judge': 'Fixture judge',
            'rubric': 'Fixture only', 'cases': [{'id': 'case-1', 'original': run(a), 'swapped': run(b)}]}


class AuditTests(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(audit.normalize(run('first')), 'A')
        self.assertEqual(audit.normalize(run('second')), 'B')
        self.assertEqual(audit.normalize(run('first'), True), 'B')
        self.assertEqual(audit.normalize(run('second'), True), 'A')

    def test_same_identity_consistent(self):
        for a, b in [('first', 'second'), ('second', 'first')]:
            self.assertEqual(audit.analyze(sample(a, b))['cases'][0]['category'], 'consistent')

    def test_same_position_flips(self):
        for value in ('first', 'second'):
            self.assertEqual(audit.analyze(sample(value, value))['cases'][0]['category'], 'flipped')

    def test_full_matrix(self):
        for a, b in itertools.product([None, 'first', 'second', 'tie', 'abstain'], repeat=2):
            with self.subTest(a=a, b=b):
                result = audit.analyze(sample(a, b))
                s = result['summary']
                self.assertEqual(sum(s['categories'].values()), 1)
                expected = 'missing' if None in (a, b) else 'abstain' if 'abstain' in (a, b) else 'tie' if 'tie' in (a, b) else 'flipped' if a == b else 'consistent'
                self.assertEqual(result['cases'][0]['category'], expected)
                self.assertEqual(s['observed_runs'], int(a is not None) + int(b is not None))

    def test_undefined_rates(self):
        s = audit.analyze(sample(None, None))['summary']
        self.assertIsNone(s['flip_rate_decisive_pairs'])
        self.assertIsNone(s['first_position_pick_rate'])
        self.assertEqual(s['complete_pair_rate'], 0)

    def test_ties_not_consistency(self):
        s = audit.analyze(sample('tie', 'tie'))['summary']
        self.assertEqual(s['both_tied'], 1)
        self.assertEqual(s['decisive_pairs'], 0)
        self.assertEqual(audit.analyze(sample('tie', 'second'))['summary']['tie_changed'], 1)

    def test_duplicate_keys(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            audit.loads('{"schema_version":1,"schema_version":1}')

    def test_nested_duplicate_keys(self):
        raw = json.dumps(sample()).replace('"verdict": "first"', '"verdict":"first","verdict":"second"')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            audit.loads(raw)

    def test_nonfinite(self):
        for value in ('NaN', 'Infinity', '-Infinity'):
            with self.assertRaises(ValueError):
                audit.loads('{"schema_version":' + value + '}')

    def test_strict_schema(self):
        variants = []
        for key, value in [('schema_version', True), ('schema_version', 2), ('data_kind', 'real'), ('judge', ''), ('cases', []), ('cases', {}), ('unknown', 1)]:
            x = sample(); x[key] = value; variants.append(x)
        for value in ('A', 'B', '', 1, {}, None):
            x = sample(); x['cases'][0]['original'] = {'verdict': value}; variants.append(x)
        for x in variants:
            with self.subTest(x=x), self.assertRaises(ValueError):
                audit.validate(x)

    def test_duplicate_case(self):
        x = sample(); x['cases'] *= 2
        with self.assertRaisesRegex(ValueError, 'Duplicate case'):
            audit.validate(x)

    def test_invalid_unicode_and_controls(self):
        for value in ('\ud800', '\x00', 'x' * 201):
            x = sample(); x['cases'][0]['id'] = value
            with self.assertRaises(ValueError):
                audit.validate(x)

    def test_html_escaping(self):
        x = sample(); x['judge'] = '<script>alert(1)</script>'; x['cases'][0]['prompt'] = '<img src=x onerror=alert(1)>'
        page = audit.render(audit.analyze(x))
        self.assertNotIn('<script>', page)
        self.assertNotIn('<img', page)
        self.assertIn('&lt;script&gt;', page)

    def test_determinism_and_hash(self):
        x = sample(); one = audit.analyze(x)
        self.assertEqual(one, audit.analyze(x))
        self.assertEqual(audit.render(one), audit.render(audit.analyze(x)))
        x['cases'][0]['swapped']['verdict'] = 'first'
        self.assertNotEqual(one['input_sha256'], audit.analyze(x)['input_sha256'])

    def test_size_limit(self):
        with self.assertRaisesRegex(ValueError, '8 MB'):
            audit.loads(' ' * (audit.MAX_BYTES + 1))

    def test_cli_and_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'input.json'; source.write_text(json.dumps(sample()))
            command = [sys.executable, str(ROOT / 'audit.py'), str(source), '--output-dir', str(root / 'report')]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue((root / 'report/report.html').exists())
            report = json.loads((root / 'report/report.json').read_text())
            self.assertEqual(report['summary']['cases'], 1)
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            self.assertEqual(subprocess.run(command + ['--force'], capture_output=True).returncode, 0)

    def test_html_existing_prevents_json_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'input.json'; source.write_text(json.dumps(sample()))
            out = root / 'report'; out.mkdir(); (out / 'report.html').write_text('KEEP')
            result = subprocess.run([sys.executable, str(ROOT / 'audit.py'), str(source), '--output-dir', str(out)], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse((out / 'report.json').exists())
            self.assertEqual((out / 'report.html').read_text(), 'KEEP')

    def test_input_cannot_be_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'report.json'; source.write_text(json.dumps(sample()))
            result = subprocess.run([sys.executable, str(ROOT / 'audit.py'), str(source), '--output-dir', str(root), '--force'], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(source.read_text()), sample())
            self.assertFalse((root / 'report.html').exists())

    def test_malformed_cli_no_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'input.json'; source.write_text('{')
            result = subprocess.run([sys.executable, str(ROOT / 'audit.py'), str(source), '--output-dir', str(root / 'report')], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse((root / 'report').exists())


if __name__ == '__main__':
    unittest.main()

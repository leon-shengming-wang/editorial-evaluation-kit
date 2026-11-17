"""Independent-review regressions for malformed inputs and CLI provenance."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from comparekit.core import InputError, MAX_BYTES, analyze, check, parse, strict_loads
from test_core import case
import test_server


class ParsingRegressions(unittest.TestCase):
    def test_non_string_constraint_types_are_validation_errors(self):
        for value in ([], {}, None, 1, True):
            with self.subTest(value=value), self.assertRaises(InputError):
                analyze([case(constraints=[{'type': value}])])

    def test_overflow_is_not_strict_json(self):
        for value in ('1e400', '-1e400', 'NaN', 'Infinity', '-Infinity'):
            with self.subTest(value=value):
                self.assertEqual(check('{"x":' + value + '}', {'type': 'json_object', 'value': None})['status'], 'fail')
                with self.assertRaises(InputError):
                    strict_loads('{"x":' + value + '}')
        self.assertEqual(strict_loads('{"x":1e20}')['x'], 1e20)

    def test_duplicate_answer_is_not_silently_overwritten(self):
        raw = json.dumps(case())[:-1] + ',"answer_a":"replacement"}'
        for text in (raw, '[' + raw + ']', json.dumps(case(id='other')) + '\n' + raw):
            with self.subTest(text=text), self.assertRaisesRegex(InputError, 'Duplicate object key'):
                parse(text)

    def test_deep_json_is_validation_error(self):
        with self.assertRaisesRegex(InputError, 'nesting'):
            strict_loads('[' * 2000 + '0' + ']' * 2000)


class HTTPRegressions(unittest.TestCase):
    setUpClass = classmethod(test_server.ServerTests.setUpClass.__func__)
    tearDownClass = classmethod(test_server.ServerTests.tearDownClass.__func__)
    request = test_server.ServerTests.request

    def test_malformed_type_returns_json_error(self):
        status, raw = self.request(data={'cases': [case(constraints=[{'type': []}])]})
        self.assertEqual(status, 400)
        self.assertIn('error', json.loads(raw))

    def test_raw_text_accepts_singleton_and_jsonl(self):
        for text, count in ((json.dumps(case()), 1), (json.dumps(case())+'\n'+json.dumps(case(id='two')), 2)):
            status, raw = self.request(data={'text': text})
            self.assertEqual(status, 200)
            self.assertEqual(len(json.loads(raw)['cases']), count)

    def test_raw_text_rejects_duplicate_keys(self):
        text = json.dumps(case())[:-1] + ',"answer_a":"replacement"}'
        status, raw = self.request(data={'text': text})
        self.assertEqual(status, 400)
        self.assertIn('Duplicate object key', json.loads(raw)['error'])

    def test_raw_text_requires_string(self):
        self.assertEqual(self.request(data={'text': {}})[0], 400)


class CLIRegressions(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'comparekit', *map(str, args)], capture_output=True, text=True, timeout=10)

    def test_smoke_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder)/'input.json', Path(folder)/'result.json'
            source.write_text(json.dumps([case()]))
            first = self.run_cli(source, '--output', output)
            self.assertEqual(first.returncode, 0, first.stderr)
            saved = output.read_bytes()
            self.assertEqual(json.loads(saved)['batch_id'], analyze([case()])['batch_id'])
            second = self.run_cli(source, '--output', output)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(output.read_bytes(), saved)

    def test_malformed_and_oversized_have_no_traceback(self):
        for text in ('['*2000+'0'+']'*2000, 'x'*(MAX_BYTES+1)):
            with self.subTest(size=len(text)), tempfile.TemporaryDirectory() as folder:
                source = Path(folder)/'input.json'
                source.write_text(text)
                result = self.run_cli(source)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn('Traceback', result.stderr)
                self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()

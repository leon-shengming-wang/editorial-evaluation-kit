import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from reviewbench.core import load
from reviewbench.desk import main, payload, render, script_json

class DeskTests(unittest.TestCase):
    def test_label_free_payload(self):
        p = payload(load('data/cases.jsonl'))
        self.assertEqual(len(p), 17)
        for row in p:
            self.assertEqual(set(row), {'id','category','prompt','source','responses','fingerprint'})
            self.assertEqual(len(row['fingerprint']),64)

    def test_embedded_json_safe(self):
        encoded = script_json({'x':'</script><img src=x onerror=alert(1)>&\u2028'})
        self.assertNotIn('<',encoded)
        self.assertNotIn('>',encoded)
        self.assertEqual(json.loads(encoded)['x'],'</script><img src=x onerror=alert(1)>&\u2028')

    def test_offline_structure(self):
        page=render(load('data/cases.jsonl'))
        self.assertIn('connect-src \'none\'',page)
        self.assertIn('lang="en"',page)
        self.assertNotIn('/*__DATA__*/',page)
        self.assertNotIn('/*__CODE__*/',page)
        self.assertNotIn('https://',page)
        self.assertNotIn('localStorage',page)
        self.assertIn('aria-live="polite"',page)

    def test_exclusive_output(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'desk.html'
            self.assertEqual(main(['data/cases.jsonl','--output',str(p)]),0)
            before=p.read_bytes()
            with self.assertRaises(SystemExit): main(['data/cases.jsonl','--output',str(p)])
            self.assertEqual(p.read_bytes(),before)

    def test_javascript_state_machine(self):
        node=shutil.which('node')
        jxa=shutil.which('osascript')
        if not node and not jxa: self.skipTest('Node or JavaScriptCore required for UI-state tests')
        script=Path('tests/desk_mock.js').read_text()+'\n'
        script+='document.getElementById("case-data").textContent='+json.dumps(json.dumps(payload(load('data/cases.jsonl'))))+';\n'
        script+=Path('reviewbench/assets/desk.js').read_text()+'\n'
        checks=Path('tests/desk_checks.js').read_text()
        if node: checks=checks.replace("JSON.stringify({assertions, status:'passed'});", "console.log(JSON.stringify({assertions, status:'passed'}));")
        script+=checks
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.js';p.write_text(script)
            command=[node,str(p)] if node else [jxa,'-l','JavaScript',str(p)]
            result=subprocess.run(command,text=True,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'passed')
        self.assertGreaterEqual(json.loads(result.stdout)['assertions'],25)

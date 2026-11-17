import copy
import json
import tempfile
import unittest
from pathlib import Path
from speechqa.core import analyze
from speechqa.report import render


def segment(a=0, b=2, words=None):
    return dict(
        start=a,
        end=b,
        text="hello world",
        avg_logprob=-0.2,
        compression_ratio=1,
        words=(
            words
            if words is not None
            else [
                dict(start=0, end=1, word="hello", probability=0.9),
                dict(start=1, end=2, word="world", probability=0.9),
            ]
        ),
    )


class Checks(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(analyze([segment()], 2, [dict(start=0, end=2)])["flags"], [])

    def test_missing_start(self):
        s = segment(words=[dict(start=1, end=2, word="world", probability=0.9)])
        f = analyze([s], 2, [dict(start=0, end=2)])["flags"]
        self.assertEqual(
            (f[0]["kind"], f[0]["start"], f[0]["end"]), ("uncovered-speech", 0, 1)
        )

    def test_missing_end(self):
        s = segment(words=[dict(start=0, end=1, word="hello", probability=0.9)])
        f = analyze([s], 2, [dict(start=0, end=2)])["flags"]
        self.assertEqual((f[0]["start"], f[0]["end"]), (1, 2))

    def test_empty_asr(self):
        self.assertEqual(
            analyze([], 2, [dict(start=0, end=2)])["flags"][0]["kind"],
            "uncovered-speech",
        )

    def test_silence(self):
        self.assertEqual(analyze([], 2, [])["flags"], [])

    def test_union(self):
        s = segment(
            words=[
                dict(start=0, end=1.4, word="hello"),
                dict(start=1, end=2, word="world"),
            ]
        )
        f = analyze([s], 2, [dict(start=0, end=2)])["flags"]
        self.assertFalse(any(x["kind"] == "uncovered-speech" for x in f))
        self.assertTrue(any(x["kind"] == "timestamp" for x in f))

    def test_gap_threshold(self):
        s = segment(words=[dict(start=0.5, end=1.5, word="hello")])
        self.assertEqual(analyze([s], 2, [dict(start=0, end=2)])["flags"], [])

    def test_bad_duration(self):
        for d in [0, -1, float("nan"), float("inf"), True]:
            with self.assertRaises(ValueError):
                analyze([], d)

    def test_nonfinite_word(self):
        s = segment()
        s["words"][0]["end"] = float("nan")
        with self.assertRaises(ValueError):
            analyze([s], 2)

    def test_out_of_bounds(self):
        self.assertTrue(
            any(f["kind"] == "timestamp" for f in analyze([segment(-1, 3)], 2)["flags"])
        )

    def test_uncertainty(self):
        s = segment()
        s["words"][0]["probability"] = 0.1
        s["avg_logprob"] = -2
        self.assertEqual(len(analyze([s], 2)["flags"]), 2)

    def test_no_missing_confidence_default(self):
        s = segment()
        s.pop("avg_logprob")
        [w.pop("probability") for w in s["words"]]
        self.assertEqual(analyze([s], 2)["flags"], [])

    def test_reference_deletion(self):
        x = analyze([segment()], 2, reference="hello beautiful world")[
            "reference_comparison"
        ]
        self.assertEqual(x["differences"][0]["operation"], "delete")
        self.assertEqual(x["differences"][0]["reference"], "beautiful")

    def test_reference_normalization(self):
        self.assertEqual(
            analyze([segment()], 2, reference="Hello, WORLD!")["reference_comparison"][
                "differences"
            ],
            [],
        )

    def test_render_injection(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.wav"
            p.write_bytes(b"RIFF")
            s = render(dict(text="</script><script>alert(1)</script>"), p)
            self.assertNotIn("</script><script>alert(1)", s)
            self.assertIn("\\u003c/script", s)

    def test_template_literals_preserved(self):
        import re

        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.wav"
            p.write_bytes(b"RIFF")
            original = {"text": "DATA_PAYLOAD AUDIO_PAYLOAD SCRIPT_PAYLOAD </script>"}
            rendered = render(original, p)
            payload = re.search(
                r'<script type="application/json" id="data">(.*?)</script>',
                rendered,
                re.S,
            ).group(1)
            self.assertEqual(json.loads(payload), original)

    def test_report_offline(self):
        t = Path("speechqa/report.js").read_text()
        self.assertNotIn("innerHTML", t)
        self.assertNotIn("fetch(", t)
        self.assertIn("audio.currentTime", t)
        self.assertIn("audio.playbackRate", t)


if __name__ == "__main__":
    unittest.main()

import unittest
from speechqa.core import compare_reference


def example():
    return [
        dict(
            start=0,
            end=3,
            text="hello bright world",
            words=[
                dict(start=0, end=0.8, word="hello"),
                dict(start=1, end=1.8, word="bright"),
                dict(start=2, end=3, word="world"),
            ],
        )
    ]


class ReferenceTiming(unittest.TestCase):
    def diff(self, ref, segments=None, duration=3):
        return compare_reference(
            segments if segments is not None else example(), duration, ref
        )["differences"]

    def test_substitution_word_backed(self):
        d = self.diff("hello beautiful world")[0]
        self.assertEqual(d["operation"], "replace")
        self.assertEqual(d["location"]["kind"], "recognized-word-interval")
        self.assertEqual((d["location"]["start"], d["location"]["end"]), (1, 1.8))

    def test_unexpected_word(self):
        d = self.diff("hello world")[0]
        self.assertEqual(d["operation"], "insert")
        self.assertEqual(d["location"]["start"], 1)

    def test_missing_word_gets_context_not_invented_time(self):
        d = self.diff("hello very bright world")[0]
        self.assertEqual(d["operation"], "delete")
        self.assertEqual(d["location"]["kind"], "neighboring-context")
        self.assertEqual((d["location"]["start"], d["location"]["end"]), (0, 1.8))

    def test_opening(self):
        d = self.diff("well hello bright world")[0]
        self.assertEqual(d["location"]["kind"], "neighboring-context")
        self.assertEqual(d["location"]["start"], 0)

    def test_ending(self):
        d = self.diff("hello bright world today")[0]
        self.assertEqual(d["location"]["kind"], "neighboring-context")
        self.assertEqual(d["location"]["end"], 3)

    def test_empty_asr(self):
        d = self.diff("hello", [])[0]
        self.assertEqual(d["location"]["kind"], "unavailable")
        self.assertIsNone(d["location"]["start"])

    def test_missing_word_timing(self):
        s = example()
        s[0]["words"] = []
        self.assertEqual(
            self.diff("hello different world", s)[0]["location"]["kind"], "unavailable"
        )

    def test_text_word_mismatch(self):
        s = example()
        s[0]["words"][1]["word"] = "wrong"
        self.assertEqual(
            self.diff("hello different world", s)[0]["location"]["kind"], "unavailable"
        )

    def test_invalid_time(self):
        for bad in [-1, float("nan"), float("inf"), 4]:
            s = example()
            s[0]["words"][1]["start"] = bad
            self.assertEqual(
                self.diff("hello different world", s)[0]["location"]["kind"],
                "unavailable",
            )

    def test_overlap(self):
        s = example()
        s[0]["words"][1]["start"] = 0.2
        self.assertEqual(
            self.diff("hello different world", s)[0]["location"]["kind"], "unavailable"
        )

    def test_multiple_normalized_tokens_per_word(self):
        s = [
            dict(
                start=0,
                end=1,
                text="state-of-art",
                words=[dict(start=0, end=1, word="state-of-art")],
            )
        ]
        d = self.diff("modern", s, 1)[0]
        self.assertEqual(d["location"]["kind"], "recognized-word-interval")
        self.assertEqual(d["location"]["end"], 1)

    def test_reference_equal(self):
        self.assertEqual(self.diff("Hello, bright WORLD!"), [])

    def test_repeated_phrase_warning(self):
        d = self.diff("hello bright bright world")[0]
        self.assertIn("ambiguous", d["alignment_warning"])
        self.assertEqual(d["location"]["kind"], "neighboring-context")

    def test_cannot_bridge_missing_anchor(self):
        s = example()
        s[0]["words"][0]["end"] = -1
        self.assertEqual(
            self.diff("hello very bright world", s)[0]["location"]["kind"],
            "unavailable",
        )

    def test_cross_segment_overlap(self):
        s = [
            dict(
                start=0, end=2, text="hello", words=[dict(start=0, end=2, word="hello")]
            ),
            dict(
                start=1, end=3, text="world", words=[dict(start=1, end=3, word="world")]
            ),
        ]
        self.assertEqual(
            self.diff("different", s)[0]["location"]["kind"], "unavailable"
        )

    def test_single_word_in_overlapping_segment_unavailable(self):
        s = [
            dict(
                start=0, end=2, text="hello", words=[dict(start=0, end=2, word="hello")]
            ),
            dict(
                start=1, end=3, text="world", words=[dict(start=1, end=3, word="world")]
            ),
        ]
        self.assertEqual(
            self.diff("hello earth", s)[0]["location"]["kind"], "unavailable"
        )
        self.assertEqual(self.diff("hi world", s)[0]["location"]["kind"], "unavailable")

    def test_reversed_segments_unavailable(self):
        s = [
            dict(
                start=2, end=3, text="hello", words=[dict(start=2, end=3, word="hello")]
            ),
            dict(
                start=0, end=1, text="world", words=[dict(start=0, end=1, word="world")]
            ),
        ]
        self.assertEqual(
            self.diff("hello earth", s)[0]["location"]["kind"], "unavailable"
        )

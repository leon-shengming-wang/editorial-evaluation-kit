"""Deterministic checks on actual ASR output; no model dependency."""

import difflib
import math
import re


def number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def analyze(segments, duration, speech_spans=None, reference=None):
    if not number(duration) or duration <= 0:
        raise ValueError("Audio duration must be finite and positive")
    vad_provided = speech_spans is not None
    speech_spans = speech_spans or []
    flags, covered = [], []
    last = 0.0

    def flag(kind, start, end, evidence, segment=None):
        flags.append(
            dict(
                id="flag-%04d" % (len(flags) + 1),
                rule_id=kind,
                state="unreviewed",
                kind=kind,
                start=max(0, min(duration, start)),
                end=max(0, min(duration, end)),
                evidence=evidence,
                segment=segment,
            )
        )

    words = []
    for i, s in enumerate(segments):
        a, b = s.get("start"), s.get("end")
        if not number(a) or not number(b):
            raise ValueError("Non-finite segment timestamp")
        if a < 0 or b <= a or b > duration + 0.1 or a < last - 0.05:
            flag(
                "timestamp",
                a,
                b,
                "Segment boundaries are invalid or overlap the previous segment.",
                i,
            )
        last = max(last, b)
        log = s.get("avg_logprob")
        if number(log) and log < -0.8:
            flag(
                "uncertainty",
                a,
                b,
                "Average token log probability %.3f is below heuristic -0.8; listen before judging."
                % log,
                i,
            )
        ratio = s.get("compression_ratio")
        if number(ratio) and ratio > 2.4:
            flag(
                "repetition",
                a,
                b,
                "Compression ratio %.3f exceeds heuristic 2.4." % ratio,
                i,
            )
        prev = a
        for w in s.get("words", []):
            x, y = w.get("start"), w.get("end")
            if not number(x) or not number(y):
                raise ValueError("Non-finite word timestamp")
            valid = 0 <= x < y <= duration + 0.1 and x >= a - 0.1 and y <= b + 0.1
            if not valid or x < prev - 0.05:
                flag(
                    "timestamp",
                    x,
                    y,
                    "Word boundary invalid, outside segment, or overlapping previous word: "
                    + w["word"],
                    i,
                )
            if valid:
                covered.append((x, y))
            prev = max(prev, y)
            p = w.get("probability")
            if number(p) and p < 0.55:
                flag(
                    "uncertainty",
                    x,
                    y,
                    "Model word probability %.3f below heuristic .55: %s"
                    % (p, w["word"]),
                    i,
                )
            words.append(w)
    # Remove the union of recognized word intervals from independently detected speech.
    # Gaps >= .75 sec are candidates, not proof of a missing word.
    for span in speech_spans:
        a, b = span["start"], span["end"]
        if not number(a) or not number(b) or a < 0 or b <= a or b > duration + 0.1:
            raise ValueError("Invalid speech activity span")
        cursor = a
        for x, y in sorted(covered):
            if y <= cursor or x >= b:
                continue
            if x - cursor >= 0.75:
                flag(
                    "uncovered-speech",
                    cursor,
                    min(x, b),
                    "Silero detected speech without aligned ASR words for at least 0.75 seconds. Could be omission, music, noise, or alignment error.",
                )
            cursor = max(cursor, min(y, b))
        if b - cursor >= 0.75:
            flag(
                "uncovered-speech",
                cursor,
                b,
                "Silero detected speech without aligned ASR words for at least 0.75 seconds. Listen to verify.",
            )
    # Speech activity disagreement is another review cue, not proof of hallucination.
    for i, s in enumerate(segments):
        a, b = s["start"], s["end"]
        overlap = sum(
            max(0, min(b, v["end"]) - max(a, v["start"])) for v in speech_spans
        )
        if vad_provided and s["text"].strip() and b > a and overlap / (b - a) < 0.1:
            flag(
                "unsupported-speech",
                a,
                b,
                "Less than 10% of this segment overlaps independent speech activity. Could be quiet speech, VAD failure or unsupported ASR text.",
                i,
            )
    comparison = None
    if reference is not None:
        tokenize = lambda t: re.findall(r"[\w]+(?:['’][\w]+)?", t.lower())
        expected = tokenize(reference)
        actual = tokenize(" ".join(s["text"] for s in segments))
        differences = []
        for op, a, b, c, d in difflib.SequenceMatcher(
            None, expected, actual, autojunk=False
        ).get_opcodes():
            if op != "equal":
                differences.append(
                    dict(
                        operation=op,
                        reference=" ".join(expected[a:b]),
                        recognized=" ".join(actual[c:d]),
                    )
                )
        comparison = dict(
            differences=differences,
            note="Sequence alignment against your supplied reference; not WER, not verified omissions. Reference may itself differ from the recording. No inferred timestamps.",
        )
    return dict(flags=flags, reference_comparison=comparison)

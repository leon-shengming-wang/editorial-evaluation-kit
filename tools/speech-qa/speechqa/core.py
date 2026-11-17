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
    comparison = (
        compare_reference(segments, duration, reference)
        if reference is not None
        else None
    )
    return dict(flags=flags, reference_comparison=comparison)


def tokenize(text):
    """English-focused comparison normalization; does not infer word boundaries for CJK."""
    return re.findall(r"[\w]+(?:['’][\w]+)?", text.lower().replace("’", "'"))


def compare_reference(segments, duration, reference):
    """Map differences to ASR-backed intervals, never invent missing-word timestamps.

    A segment's text must exactly match its normalized word stream before its
    word times can locate a difference. A deletion has no recognized words and
    therefore can only offer neighboring context, never an exact missing span.
    """
    actual, timing = [], []
    conflicting_segments = set()
    for i, current in enumerate(segments):
        for j, previous_segment in enumerate(segments[:i]):
            if (
                number(previous_segment["end"])
                and number(current["start"])
                and previous_segment["end"] > current["start"]
            ):
                conflicting_segments.update((i, j))
    for segment_index, segment in enumerate(segments):
        tokens = tokenize(segment["text"])
        word_tokens, word_times = [], []
        previous = segment["start"]
        valid = (
            segment_index not in conflicting_segments
            and number(segment["start"])
            and number(segment["end"])
            and 0 <= segment["start"] < segment["end"] <= duration
        )
        for word in segment.get("words", []):
            a, b = word.get("start"), word.get("end")
            safe = (
                number(a)
                and number(b)
                and 0 <= a < b <= duration
                and segment["start"] <= a
                and b <= segment["end"]
                and a >= previous
            )
            valid = valid and safe
            if safe:
                previous = b
            pieces = tokenize(word["word"])
            word_tokens.extend(pieces)
            word_times.extend([dict(start=a, end=b, word=word["word"])] * len(pieces))
        actual.extend(tokens)
        timing.extend(
            word_times if valid and word_tokens == tokens else [None] * len(tokens)
        )
    expected = tokenize(reference)
    differences = []
    for op, a, b, c, d in difflib.SequenceMatcher(
        None, expected, actual, autojunk=False
    ).get_opcodes():
        if op == "equal":
            continue
        location = dict(
            kind="unavailable",
            start=None,
            end=None,
            explanation="No trustworthy matching word-time sequence at this difference. Listen to the recording manually.",
            anchors=[],
        )
        if c < d and all(timing[c:d]):
            selected = timing[c:d]
            if all(
                (
                    selected[i] is selected[i + 1]
                    or selected[i]["end"] <= selected[i + 1]["start"]
                )
                for i in range(len(selected) - 1)
            ):
                location = dict(
                    kind="recognized-word-interval",
                    start=selected[0]["start"],
                    end=selected[-1]["end"],
                    explanation="ASR timestamps for the recognized words, not verified error boundaries. Script sequence matching is heuristic.",
                    anchors=selected,
                )
        elif op == "delete":
            before = timing[c - 1] if c > 0 else None
            after = timing[c] if c < len(timing) else None
            if before and after and before["end"] <= after["start"]:
                location = dict(
                    kind="neighboring-context",
                    start=before["start"],
                    end=after["end"],
                    explanation="Expected text has no ASR word timestamps. Play the neighboring recognized words; the missing text may not have been spoken at all.",
                    anchors=[before, after],
                )
            elif before and c == len(timing):
                location = dict(
                    kind="neighboring-context",
                    start=before["start"],
                    end=min(duration, before["end"] + 1),
                    explanation="Expected ending has no ASR timestamps. Only the last recognized word and up to one second after it are offered as context, not an omission location.",
                    anchors=[before],
                )
            elif after and c == 0:
                location = dict(
                    kind="neighboring-context",
                    start=max(0, after["start"] - 1),
                    end=after["end"],
                    explanation="Expected opening has no ASR timestamps. Only the first recognized word and up to one second before it are offered as context, not an omission location.",
                    anchors=[after],
                )
        differences.append(
            dict(
                operation=op,
                reference=" ".join(expected[a:b]),
                recognized=" ".join(actual[c:d]),
                reference_token_range=[a, b],
                recognized_token_range=[c, d],
                location=location,
                alignment_warning="Repeated phrases can make script matching ambiguous. Verify the suggested location by listening.",
            )
        )
    return dict(
        differences=differences,
        note="Supplied-script comparison, not verified errors or WER. Playback locations use ASR word estimates; absent words get neighboring context only. Timing is unavailable when text and word-time evidence disagree.",
    )

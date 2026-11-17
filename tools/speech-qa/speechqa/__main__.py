"""Run local ASR, independent VAD, evidence checks and a portable review report."""

import argparse
import sys
import dataclasses
import hashlib
import importlib.metadata
import json
import time
import wave
import tempfile
from pathlib import Path
from .core import analyze
from .report import render


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="New output directory; never overwrites existing output",
    )
    parser.add_argument(
        "--model",
        default="base.en",
        help="faster-whisper model name or local model directory",
    )
    parser.add_argument("--language", default="en", help="Whisper language code")
    parser.add_argument(
        "--reference",
        type=Path,
        help="Optional plain-text expected script, not treated as ground truth",
    )
    args = parser.parse_args()
    if not args.audio.is_file():
        parser.error("Audio file not found")
    if args.audio.stat().st_size > 100 * 1024 * 1024:
        parser.error("Prototype limit: 100 MB input")
    if args.out.exists():
        parser.error("Output directory already exists; choose a new one")
    try:
        from faster_whisper import WhisperModel
        from faster_whisper.audio import decode_audio
        from faster_whisper.utils import download_model
        from faster_whisper.vad import get_speech_timestamps, VadOptions
    except ImportError:
        parser.error("Install requirements.txt in a virtual environment first")
    audio = decode_audio(str(args.audio), sampling_rate=16000)
    duration = len(audio) / 16000
    if not 0 < duration <= 1800:
        parser.error("Prototype supports nonempty clips up to 30 minutes")
    started = time.perf_counter()
    model_path = (
        str(Path(args.model))
        if Path(args.model).is_dir()
        else download_model(args.model)
    )
    model_digest = hashlib.sha256(
        (Path(model_path) / "model.bin").read_bytes()
    ).hexdigest()
    model = WhisperModel(model_path, device="cpu", compute_type="int8")
    result, info = model.transcribe(
        audio,
        language=args.language,
        word_timestamps=True,
        vad_filter=False,
        beam_size=5,
    )
    segments = [
        dict(
            start=s.start,
            end=s.end,
            text=s.text,
            avg_logprob=s.avg_logprob,
            no_speech_prob=s.no_speech_prob,
            compression_ratio=s.compression_ratio,
            words=[dataclasses.asdict(w) for w in (s.words or [])],
        )
        for s in result
    ]
    speech = [
        dict(start=s["start"] / 16000, end=s["end"] / 16000)
        for s in get_speech_timestamps(audio, VadOptions())
    ]
    reference = args.reference.read_text(encoding="utf-8") if args.reference else None
    report = dict(
        schema_version=1,
        model_sha256=model_digest,
        elapsed_seconds=round(time.perf_counter() - started, 3),
        audio_sha256=hashlib.sha256(args.audio.read_bytes()).hexdigest(),
        duration=duration,
        model=args.model,
        language=info.language,
        engine="faster-whisper",
        engine_version=importlib.metadata.version("faster-whisper"),
        rules=dict(
            word_probability_below=0.55,
            segment_logprob_below=-0.8,
            compression_ratio_above=2.4,
            uncovered_speech_min_seconds=0.75,
            vad_support_below=0.1,
        ),
        settings=dict(
            device="cpu",
            compute_type="int8",
            beam_size=5,
            word_timestamps=True,
            vad_filter=False,
        ),
        segments=segments,
        speech_spans=speech,
        **analyze(segments, duration, speech, reference)
    )
    # Create output only after inference succeeds. Original input is never edited.
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "analysis.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    with tempfile.TemporaryDirectory(prefix="speechqa-preview-") as directory:
        preview = Path(directory) / "preview.wav"
        with wave.open(str(preview), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(16000)
            out.writeframes((audio.clip(-1, 1) * 32767).astype("<i2").tobytes())
        (args.out / "index.html").write_text(render(report, preview), encoding="utf-8")
    print("Created", args.out / "index.html")
    print(
        len(segments),
        "segments;",
        len(report["flags"]),
        "review candidates, not confirmed errors.",
    )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError) as exc:
        print("Speech QA failed: " + str(exc), file=sys.stderr)
        raise SystemExit(1)

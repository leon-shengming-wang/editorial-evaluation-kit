# Observed failure, not a fabricated benchmark

`silence-observed.json` is actual `tiny.en` output on 3 seconds of 16 kHz mono digital silence, from the local run documented in `../VERIFICATION.md`. The model hallucinated “You”; the checker flagged it. This is one observed case, not an error-rate estimate. The artifact predates the addition of model-binary hashes and stable flag IDs; new runs include them.

Reproduce the input without downloading any audio:

```sh
python - <<'PY'
import wave
with wave.open('/tmp/silence.wav', 'wb') as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(16000)
    f.writeframes(bytes(16000 * 2 * 3))
PY
python -m speechqa /tmp/silence.wav --model tiny.en --out /tmp/silence-review
```

Exact model output can vary with dependency/model revisions. The correct assertion is not that every model must hallucinate “You”; it is that unsupported transcript text remains visible and flagged rather than silently treated as verified speech.

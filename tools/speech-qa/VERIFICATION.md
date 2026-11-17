# Verification record — 2026-11-17

## Actual inference, not canned output

An 11.0-second public test fixture from OpenAI Whisper was downloaded for local testing:
https://raw.githubusercontent.com/openai/whisper/main/tests/jfk.flac

SHA-256: `63a4b1e4c1dc655ac70961ffbf518acd249df237e5a0152faae9a4a836949715`.
The upstream recording is a JFK speech excerpt. **Audio is not redistributed in this repository.** The screenshots show our own interface, generated transcript and actual model output; they are not client work or a reviewer performance score.

On this Apple Silicon Mac, Python 3.9, faster-whisper 1.1.1, CPU int8 and `tiny.en` generated 22 words in two segments. The second “ask” at 8.06–8.66 seconds had model probability about 0.200, and became a review candidate. This does not establish that the word is wrong. The expected script comparison matched after normalization.

A separate real inference on 3 seconds of generated digital silence produced the spurious word “You”. The pipeline flagged low segment log probability, low word probability and no independent VAD support. **This observed failure is why the interface never labels ASR as verified truth.** No broad benchmark, accuracy percentage or accent/language generalization is claimed.

## Browser integration exercised

A fresh isolated headless Chromium instance, not the user's personal browser profile, performed:
- file selection and actual local POST upload;
- real inference response with aligned transcript;
- actual audio playback advancing time, followed by pause retaining time;
- word-click seek and active-word highlight;
- 1.5× playback-rate change;
- correction entered separately from original text;
- downloaded JSON checked for correction and unchanged original;
- desktop and 390px mobile screenshots, no horizontal overflow;
- no JavaScript page errors during this test.

Desktop and mobile screenshots were inspected. Playback progress was machine-observed, not an auditory quality judgment. Safari, Firefox, keyboard-only navigation, screen-reader behavior, every supported input format and long recordings have not been fully tested. The current smoke script is optional and requires Playwright plus a running server and authorized test fixture.

## Fast tests and boundaries

26 deterministic Python tests cover interval unions, omitted-span candidates, empty/silent activity, low confidence, absent confidence, invalid duration/time, supplied-script comparison, escaping, offline rendering, loopback host/origin protections, malformed form basics and missing token. Parent ReviewBench and Layout Preflight suites were rerun independently. CI does not download an ASR model and must not be described as model-quality verification.

Current limits: single-user loopback server, one job at a time, English browser UI/default model; CLI multilingual support is an exposed upstream option, **not independently tested multilingual accuracy**. No diarization, forced alignment, WER benchmarking, cancellation UI, persistent jobs, transcript draft import or production hardening. Review edits are in-memory until export. Large input limits are prototype caps, not performance guarantees.

Independent review caught and fixed literal-placeholder corruption in report generation and missing GET host/origin checks. Regression tests cover both. Decoding currently occurs before the duration limit is checked; use short trusted recordings, since a highly compressed long file can consume substantial memory before rejection. This is another reason not to expose the server publicly.

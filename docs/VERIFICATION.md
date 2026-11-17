# Verification record

Local validation on Python 3.9.6:

- 63 unittest tests passed.
- All 17 synthetic cases pass strict schema, exact evidence quote, and weighted decision checks.
- Five categories are covered; decisions: five A, five B, four ties, three abstentions.
- The regenerated 17-case report was inspected in Chrome on desktop, including the new semantic-review example. No remote fonts, scripts, API calls, or image requests are required.
- SQL tests cover transactional rollback, immutable case identity, retained decision history, latest-per-reviewer queries, foreign keys, and parameterized SQL.
- Validator tests cover duplicate JSON keys and record IDs, non-finite numbers, invalid types including booleans as scores, empty text, missing fields, contradictory decisions, and malformed evidence.
- Report tests confirm HTML escaping for injected markup. CLI tests prevent overwriting input and reject invalid records before generating reports.

An independent code pass exercised 198 malformed-value mutations without a crash. This is a bounded robustness check, not a security certification.

- Practice export tests verify that reference labels, scores, rationales, evidence annotations and uncertainty fields are excluded; dataset source and candidate responses remain visible. Existing files are not overwritten.

## Hosted checks and remaining limits

- Hosted GitHub CI passed on Python 3.9 and 3.12 for the 17-case version at commit `6f358b82a40b3a8419e0492d7cb564153e5b9864` ([run](https://github.com/leon-shengming-wang/editorial-evaluation-kit/actions/runs/43995440710)). The initial run failed before tests because Ubuntu 26.04 lacked Python 3.9; pinning Ubuntu 22.04 resolved the environment issue. Later changes require their own CI run.
- The companion layout report was visually inspected in Chrome; its 29 tests also pass locally.
- These authored labels have not been independently reviewed by Leon or another human rater.
- No image or audio model was tested. Design cases use text specifications; audio cases use supplied text references.
- No real model performance, inter-rater reliability, hiring eligibility, or production security claims are made.

## Reproduce

```bash
python3 -m unittest discover -s tests -v
python3 -m reviewbench data/cases.jsonl --html reports/index.html --json reports/summary.json
```

## Pairwise audit addition — November 17, 2026

- Main standard-library suite: 80 tests pass on local Python 3.9.
- Layout Preflight companion: 29 tests pass from its own directory.
- Existing 17-case HTML/JSON reports regenerate without changes.
- Agreement fixture reproduces deterministic JSON and offline HTML.
- Verified known kappa arithmetic, perfect/negative agreement, constant-label undefined kappa, no overlap, missing ratings, ties and abstentions, duplicate rejection, latest-revision selection, read-only database bytes, missing database non-creation, safe HTML escaping and exclusive output creation.
- Visual browser inspection was not performed in this pass because a supported browser-control tool was unavailable. HTML checks are structural and content tests, not a claim that every visual layout or browser was tested.
- The initial attempt to run companion tests from the repository root failed import resolution; rerunning from the documented `tools/layout-preflight` working directory passed all 29 tests. The CI workflow already uses that working directory.

## Offline Review Desk addition — November 17, 2026

- 85 main Python tests pass, including the JavaScript state harness with at least 25 assertions under macOS JavaScriptCore. CI uses Node 22 for the same harness.
- The desk embeds only case inputs plus their SHA-256 fingerprints, not reference labels or rationales.
- Generated HTML and existing report outputs are deterministic.
- State tests are not a substitute for actual browser visual/download verification; a local headless Chrome command returned no DOM output, so that stage remains unverified.

# Verification record

Local validation on Python 3.9.6:

- 52 unittest tests passed.
- All 17 synthetic cases pass strict schema, exact evidence quote, and weighted decision checks.
- Five categories are covered; decisions: five A, five B, four ties, three abstentions.
- The earlier 14-case HTML report was inspected in Chrome on desktop. The regenerated 17-case report passes automated generation and escaping checks but has not yet received a new visual inspection. No remote fonts, scripts, API calls, or image requests are required.
- SQL tests cover transactional rollback, immutable case identity, retained decision history, latest-per-reviewer queries, foreign keys, and parameterized SQL.
- Validator tests cover duplicate JSON keys and record IDs, non-finite numbers, invalid types including booleans as scores, empty text, missing fields, contradictory decisions, and malformed evidence.
- Report tests confirm HTML escaping for injected markup. CLI tests prevent overwriting input and reject invalid records before generating reports.

An independent code pass exercised 198 malformed-value mutations without a crash. This is a bounded robustness check, not a security certification.

## Not yet verified

- Hosted GitHub CI passed on Python 3.9 and 3.12 for the 14-case version at commit `bd88bdaae86f5cd9a0192bf8423cb68bafa88373`. The initial run failed before tests because Ubuntu 26.04 lacked Python 3.9; pinning Ubuntu 22.04 resolved the environment issue. Later changes require their own CI run.
- The companion layout report was visually inspected in Chrome; its 29 tests also pass locally.
- These authored labels have not been independently reviewed by Leon or another human rater.
- No image or audio model was tested. Design cases use text specifications; audio cases use supplied text references.
- No real model performance, inter-rater reliability, hiring eligibility, or production security claims are made.

## Reproduce

```bash
python3 -m unittest discover -s tests -v
python3 -m reviewbench data/cases.jsonl --html reports/index.html --json reports/summary.json
```

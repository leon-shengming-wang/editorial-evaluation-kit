# Verification record

Local validation on Python 3.9.6:

- 48 unittest tests passed.
- All 14 synthetic cases pass strict schema, exact evidence quote, and weighted decision checks.
- Four categories are covered; decisions: four A, five B, three ties, two abstentions.
- HTML report generated and inspected in Chrome on desktop. No remote fonts, scripts, API calls, or image requests are required.
- SQL tests cover transactional rollback, immutable case identity, retained decision history, latest-per-reviewer queries, foreign keys, and parameterized SQL.
- Validator tests cover duplicate JSON keys and record IDs, non-finite numbers, invalid types including booleans as scores, empty text, missing fields, contradictory decisions, and malformed evidence.
- Report tests confirm HTML escaping for injected markup. CLI tests prevent overwriting input and reject invalid records before generating reports.

An independent code pass exercised 198 malformed-value mutations without a crash. This is a bounded robustness check, not a security certification.

## Not yet verified

- Hosted GitHub CI has not run. A workflow file is provided, but its presence is not a passing build.
- These authored labels have not been independently reviewed by Leon or another human rater.
- No image or audio model was tested. Design cases use text specifications; audio cases use supplied text references.
- No real model performance, inter-rater reliability, hiring eligibility, or production security claims are made.

## Reproduce

```bash
python3 -m unittest discover -s tests -v
python3 -m reviewbench data/cases.jsonl --html reports/index.html --json reports/summary.json
```

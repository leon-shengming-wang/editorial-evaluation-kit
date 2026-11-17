# Contrast
## Batch checks. Human judgment.

A local answer-comparison workbench: import your own A/B responses, run explicit instruction checks across a batch, inspect the reasons, and record a human decision with evidence. English UI. Python 3.9+. **No dependencies, model API, account, or network needed after download.**

This is an AI-assisted portfolio engineering project, not evidence of paid client work or independent model benchmarking. The eight examples are authored synthetic demonstrations, not measured model outputs or private platform tasks.

## Run

From this directory:

```sh
python3 -m comparekit --serve
```

Open **http://127.0.0.1:8768**. Load synthetic examples → Analyze batch → inspect answers and checks → record a decision with evidence and a reason → Export review. The exported JSON contains the inputs, automated findings, recorded decisions, optional human rubric scores and unfinished drafts. Restore against the **same analyzed batch**; changed input/constraints produce a different fingerprint. Export before closing: this app has no database or browser storage.

For batch automation without a browser:

```sh
python3 -m comparekit examples/demo.json --output my-results.json
python3 -m unittest discover -s tests -v
```

The CLI refuses to overwrite an existing output. It returns status 2 for invalid input. Interrupted writes can leave partial new files; inspect output before use.

## Input contract

Accepts a single case, an array, `{ "cases": [...] }`, or JSONL (one case per line). Maximum 2 MB, 200 cases, 50,000 characters per prompt/answer, 30 constraints per case. Duplicate keys, duplicate IDs, invalid types, unknown case fields and non-finite numbers are rejected. HTTP request wrapping counts toward the 2 MB limit.

```json
{
  "id": "release-note",
  "prompt": "Mention beta in at most 20 words, without saying guaranteed.",
  "answer_a": "The beta is available to invited testers.",
  "answer_b": "The beta is guaranteed to succeed.",
  "constraints": [
    {"type": "max_words", "value": 20},
    {"type": "required_terms", "value": ["beta"]},
    {"type": "forbidden_terms", "value": ["guaranteed"]}
  ]
}
```

You explicitly encode checkable requirements. The engine does **not** automatically infer every requirement from natural-language prompts.

| Check | Meaning and limits |
| --- | --- |
| `max_words`, `min_words` | Integer 0–50000. Unicode word-token regex with internal apostrophes/hyphens; not a language-aware tokenizer. |
| `exact_bullets` | Counts unordered `-`, `+`, `*` lines including nested lines. Numbered lists do not count. |
| `max_headings` | Counts Markdown ATX headings only, not HTML or Setext headings. |
| `required_terms`, `forbidden_terms` | 1–50 literal case-insensitive terms with word-edge matching. Not paraphrase or semantic matching. |
| `json_object` | Strict JSON, object at root; rejects fences, duplicate keys and non-finite numbers. Does not validate a task-specific schema. |
| `no_markdown` | Heuristic. Common formatting cues flag a failure candidate; no cues still requires review. Literal punctuation can create false positives. |

For the last two checks, omit `value`. All numeric thresholds are explicit, unweighted constraints, not learned scores.

## Read the result correctly

Automatic checks return `pass`, `fail` or `review`, each with a concrete reason. A check-based A/B cue only means fewer explicit failures. Equal failure counts are **not a quality tie**. Empty responses, absent constraints and unresolved heuristics require review. The demo deliberately includes a false factual answer that passes a length check, illustrating this boundary.

Truthfulness, safety, completeness, nuance and usefulness remain human judgments. Recorded decisions require evidence plus a reason; optional 1–5 rubric scores are human-entered. The app is not a replacement for source verification and makes no hiring or performance claims. There is no LLM judge, inference charge, position-swapping study or fabricated accuracy score. A future model-judge extension would need consent, cost controls, prompt-injection defenses and A/B-versus-B/A diagnostics before its output could be trusted.

## Compared with the original Review Desk

[Review Desk](../../docs/REVIEW-DESK.md) is a portable worksheet for the repository's fixed 17 authored practice cases. Contrast imports arbitrary validated batches and runs deterministic checks before human adjudication. It is a separate local service, not a renamed copy of the fixed-case worksheet.

## Privacy and security

The service binds to loopback, rejects unrelated Host/Origin headers, serves only fixed routes, does not store input, and renders imported content as text. No third-party assets, telemetry, model calls or external uploads are built in. **Browser extensions, OS/browser downloads, backups and other local software are outside this guarantee**; use an appropriate browser profile for sensitive data. Export includes full prompts/responses and notes: do not commit confidential work. SHA-256 identifies content, not authorship or truth. Restored review files are untrusted user records, not signed audit evidence.

## Verification

42 Python tests cover parsing, deterministic rules, server boundaries, CLI failure modes, output protection and regression cases. Local Chrome verification exercised the eight-case demo, batch analysis, an evidence-backed recorded decision and the export control. Export initiation was visible; file download/restore and mobile viewport were not independently browser-verified in this run. Review-draft conflict handling and JavaScript syntax were separately checked. CI runs Python 3.9 and 3.12.

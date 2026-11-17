# Evidence Drift Lab · Work in progress

A small, working research foundation for tracking when evidence behind an answer changes. This is **not a completed fact-checking product**. It compares two user-supplied local snapshots, not live websites. All included examples are synthetic; they are not client work, production results, or real museum information.

## Implemented now

- Version-1 schema validation for timestamped evidence snapshots and answer records.
- Unique source and answer IDs, resolved source references, strict field validation, duplicate-key rejection, bounded input and nesting.
- Deterministic source additions, removals, literal content changes, and URL/title changes.
- SHA-256 fingerprints of exact UTF-8 source content and canonical snapshots.
- Answer change records and explicit dependency-based review flags when referenced sources change.
- A dependency-free CLI, synthetic example snapshots, and regression tests.

## Try it

Requires Python 3.9 or later, standard library only. From this folder:

```sh
python3 -m evidence_drift examples/before.json examples/after.json
python3 -m evidence_drift examples/before.json examples/after.json --output report.json
python3 -m unittest discover -s tests -v
```

The output file must not already exist. Errors return exit code 2. No files are uploaded, no API key is used, and no network request is made. Store exported reports carefully if you supply private source text.

The sample changes museum opening hours, removes a ticket source, and adds an accessibility source. The visit answer remains textually unchanged but loses one citation and depends on changed evidence. The report flags it for review without asserting that it is false.

## Input contract

See `examples/before.json` for the complete schema. Both snapshots must include exactly:

- `schema_version`: integer `1`.
- `snapshot_id`: nonempty string identifying the supplied snapshot.
- `captured_at`: ISO 8601 timestamp with timezone, supplied by you, not independently verified.
- `sources`: records with `id`, `url`, `title`, and `content` strings. URLs must be HTTP(S) without embedded credentials. Content may be empty.
- `answers`: records with `id`, `text`, and `source_ids`. References must be unique and resolve in that snapshot. To represent a removed source in a later snapshot, remove its later reference too; the comparison retains prior dependencies.

IDs are matched across snapshots. Keep source identity stable yourself; this tool cannot infer whether two URLs identify the same underlying publication. It does not enforce chronological order, so reverse comparison is allowed. Each file is limited to 2 MB, each collection to 1,000 records, each string to 100,000 characters, and nesting to 100 levels.

## What the report means

`source_changes` lists additions, removals and changed fields, with before/after content hashes. Whitespace and casing count as content changes. Metadata-only changes retain the same content hash but still trigger conservative dependency review. `answer_changes` includes answer text/reference changes and unchanged answers referencing changed sources. `review_required` only signals a changed dependency; `false` is **not approval or a claim that the answer is correct**.

Snapshot hashes normalize record order, reference order and JSON key order. They include snapshot IDs, timestamps and full record content. They establish reproducible input identity, not source authenticity. Reports are sorted by record ID and omit execution timestamps to keep identical input results deterministic.

## Not implemented yet

- Claim extraction or alignment between answer claims and individual source passages.
- Retrieval, crawling, scheduled checks, source authenticity or citation verification.
- Semantic equivalence, contradiction detection, factuality scoring, or model-assisted judgments.
- A review UI, reviewer decisions, persistent storage, version migration or change history database.
- Evaluation against a labeled real-world corpus, coverage/recall metrics, or production performance guarantees.

Next research milestone: define an annotated claim-to-passage schema and hand-reviewed synthetic fixtures before adding semantic methods. Any later model output should remain a review hypothesis, not a truth verdict. AI-assisted implementation is intended to be inspectable through code and tests; no employment, client or model-training experience is implied.

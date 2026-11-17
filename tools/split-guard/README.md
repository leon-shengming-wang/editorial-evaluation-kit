# Split Guard
### Inspect overlap before trusting an evaluation split.

A local, dependency-free dataset audit for **cross-split normalized duplicates and token-shingle similarity candidates**. It accepts your own JSONL, reports exact evidence and conflicting labels, and exports a readable HTML report plus machine-readable JSON. It never deletes records or certifies a benchmark as uncontaminated.

This English-language, AI-assisted portfolio project uses synthetic fixtures, not confidential platform tasks or measured model performance. No client or employment experience is implied.

## Run

Python 3.9+. From this directory:

```sh
python3 -m splitguard examples/records.jsonl --threshold 0.5 --json audit.json --html audit.html
python3 -m unittest discover -s tests -v
```

Open `audit.html` in any browser. A [committed synthetic report](reports/synthetic-audit.html) is available to download and open locally; GitHub source view does not execute HTML. Reproduce the demo artifacts with `python3 -m examples.build_demo` from this directory. Both output paths must be new; existing files are never overwritten. With no output arguments, JSON goes to stdout. Invalid input or an exceeded work budget exits with status 2 and no analysis report. If disk writing fails after analysis, a new output may be partial; inspect files before using them.

## Input

One object per nonblank line; UTF-8, optional BOM:

```json
{"id":"example-001","split":"train","text":"An original sample to audit.","label":"optional category"}
```

`id`, `split`, `text` are required; `label` is optional. All are nonempty strings. IDs are globally unique, split is exactly `train`, `dev` or `test`, and unknown fields/duplicate JSON keys are rejected. Labels are case-sensitive categories, not inferred truth.

Bounds: 2 MB, 400 records, 50,000 characters per text, 200 per other field, 4,000 tokens per record, 100,000 unique document-shingle entries in total and 1,000,000 inverted-index posting visits. Exceeding a bound **stops the audit** rather than silently sampling. Smaller batches can miss overlap between batches: do not describe separately audited batches as globally audited.

## How it works

1. Exact normalization: Unicode NFKC, casefold, collapse whitespace. Punctuation is preserved. Every cross-split pair of identical normalized strings is reported.
2. Near-duplicate candidates: tokenize with Unicode `\w+`, form a set of consecutive word shingles (default 3 words, configurable 1–10). This removes punctuation for near comparison, ignores repeated-shingle frequency, and is not language-aware word segmentation.
3. An inverted index finds pairs sharing at least one shingle. Cross-split, non-exact pairs receive exact set Jaccard: `shared / union`. Report those at or above the threshold (default 0.7, valid range `(0,1]`). No MinHash sampling or probabilistic retrieval is used.
4. Records shorter than the shingle width are excluded from **near** scoring and listed explicitly, while exact detection still covers them. Zero-overlap pairs cannot reach a positive threshold and need not be scored.

Within successful bounded runs, candidate generation is complete for these declared exact and shingle rules, not for semantic similarity. The report includes total possible cross-split pairs, exact pairs, near candidates scored, work performed, ineligible IDs, settings and reproducible input fingerprint. Output ordering is deterministic, independent of record input order. Pair evidence includes both excerpts (first 240 characters), SHA-256 hashes of complete original texts, overlap counts and up to five shared shingles. Full input texts remain in your source file.

`label_conflict=true` means two provided labels differ, even if the pair is merely a near candidate. It does not establish which label is wrong. Missing labels yield `null`. Similar text may legitimately have different answers after a small but meaningful edit, as the synthetic opening-hours example illustrates.

## Design research

- [Hugging Face: Large-scale Near-deduplication Behind BigCode](https://huggingface.co/blog/dedup) explains document-level near deduplication and the tradeoffs of MinHash/LSH. Split Guard deliberately chooses bounded exact shingle scoring for inspectable small evaluation sets, rather than claiming large-corpus scalability.
- [Google Research deduplicate-text-datasets](https://github.com/google-research/deduplicate-text-datasets) provides research implementations of exact-substring and near-duplicate analysis. This project is an independent small implementation; it does not copy or implement Google's algorithms.
- [Deduplicating Training Data Makes Language Models Better](https://arxiv.org/abs/2107.06499) motivates investigating repetition and split overlap. Its findings do not establish contamination in any dataset you supply here.

## Limitations and safety

This is a **review queue**, not proof a model trained on a benchmark. It cannot detect semantic paraphrases with low lexical overlap, translated copies, image/audio overlap, or unknown training data. Boilerplate may trigger false positives. Tokenization is especially limited for unsegmented languages. The threshold is a user-selected screening setting, not a validated accuracy score. No quality, recall, or contamination-rate guarantee is made.

All processing is local with the Python standard library. No web requests, executable input, model APIs, third-party assets or analytics. HTML escapes imported content. Reports contain dataset excerpts and labels: review them before sharing, and never commit private platform content. The source dataset is never modified. Seventeen tests include exact/near boundaries, brute-force agreement on a seeded synthetic batch, missing labels, Unicode, schema errors, output protection, resource limits and HTML escaping.

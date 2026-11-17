# Retrieval Scorecard

An offline, inspectable scorecard for ranked document retrieval. Import relevance judgments (qrels) and a ranked run; export a macro summary, per-query calculations, and document-level evidence as JSON and a self-contained HTML report. **No model, network request, API key or third-party dependency.** Synthetic examples demonstrate mechanics, not benchmark performance or client experience.

## Run

Python 3.9 or newer, from this folder:

```sh
python3 -m retrieval_scorecard examples/qrels.json examples/run.json --k 3 --output-dir demo-report
python3 -m unittest discover -s tests -v
```

Open `demo-report/report.html` in a browser. `report.json` retains full numeric precision and input hashes. The output directory must not exist; reruns never overwrite prior work. Invalid input returns exit code 2. An operating-system write failure may leave a partial new directory, which should not be treated as a complete report.

## Exact metric policy

Only queries explicitly present in qrels are scored. A missing run query gets an empty ranking and zero scores. Run-only queries are listed as excluded, not silently mixed into the mean. An empty run is valid; empty qrels query set is rejected.

At cutoff **k**:

- Binary relevance means **grade > 0**.
- Precision: relevant documents retrieved in the first k positions divided by **k**, even if fewer documents were returned.
- Recall: those relevant hits divided by all positive judgments for the query. With no positive judgments, it is **0** by declared convention.
- Reciprocal rank (RR): 1 divided by the first relevant rank at or before k; otherwise 0. **MRR** is the macro average of query RR, not a different per-query metric.
- DCG: sum of `grade / log2(rank + 1)` over the first k ranks. This is **linear graded gain**, not `2^grade - 1`.
- Ideal DCG: the same sum after sorting **all judged documents** by descending grade, truncated at k. nDCG is DCG / ideal DCG; if ideal DCG is zero, nDCG is **0** by convention.

Unjudged documents remain at their original rank and contribute zero gain. Reports show `judged: false` and `relevance: null`, keeping unknown judgments distinguishable from explicit zero judgments. Incomplete qrels can underestimate retrieval quality. Zero-relevance queries remain in every macro denominator. Summary means weight queries equally; no micro average or significance test is provided.

## Input schema

Both files require integer `schema_version: 1`. See complete fixtures in `examples/`.

Qrels contains `queries`, each with `id` and `judgments`. Each judgment has `document_id` and numeric `relevance` in [0, 1000], including fractional grades. Boolean and non-finite values are rejected. An empty judgment list is allowed.

Run contains `run_id` and `queries`, each with `id` and `documents`: an ordered array of document IDs. **Array order is rank**, starting at 1. There are no scores or ties to resolve. Convert score-based systems to an explicitly ordered run yourself and document any tie policy. Native TREC whitespace files are not accepted by this version.

All object fields are exact: unknown/missing fields, duplicate JSON keys, duplicate query IDs and duplicate document IDs within a query are rejected. IDs are nonempty UTF-8 strings of at most 200 characters. Maximum file size is 2 MB; maximum nesting is 100 levels; maximum queries per file is 1,000; maximum documents per query is 10,000; maximum combined records is 100,000. k is an integer from 1 to 10,000.

## Inspectability and privacy

Each query includes the actual top-k ranking, judgment status, relevance, gain, DCG contribution and ideal ranking. The report also exposes denominator counts, unjudged counts and missing-run flags. Input SHA-256 values hash canonical JSON key ordering, preserving array order, so changing an input ordering changes its fingerprint. They establish input identity, not authenticity. Output is deterministic for identical inputs; no run timestamp is injected.

HTML escapes supplied identifiers and contains no JavaScript, remote font, image, link or telemetry. It works offline. Reports include document/query identifiers and should be treated as sensitive if inputs are private. Do not publish proprietary judgments without permission.

## Research basis and deliberate choices

Primary references consulted for definitions and implementation conventions:

- https://ir-measur.es/en/latest/measures.html — metric naming, graded nDCG, relevance thresholds and judged-only variants.
- https://github.com/usnistgov/trec_eval/blob/master/m_ndcg_cut.c — linear relevance gain with logarithmic rank discount and ideal normalization.

This implementation is independent code, not copied TREC Eval code. It deliberately fixes relevance at grade > 0 and uses explicit document order rather than score sorting. It does not claim bit-for-bit compatibility with another evaluation library. Tests cover hand-calculated values, ideal/reversed ordering, fractional grades, missing and extra queries, short rankings, cutoff behavior and rejected malformed inputs.

## Limits

This scores **retrieval against supplied labels**, not generated answers, citations, factual truth, semantic relevance, fairness, safety or end-user satisfaction. It does not produce judgments, fetch documents, train embeddings, call an LLM, or establish a credible real-world benchmark from synthetic fixtures. Human label quality, corpus coverage, query selection and any train/test leakage must be assessed separately. Larger experiments, multiple-run comparisons and statistical testing are future work, not hidden features.

### Numerical stability

nDCG is calculated after dividing gains by the maximum query grade; this preserves the ratio while avoiding subnormal-number underflow. JSON includes the scale and scaled DCG values for inspection. Raw DCG and individual raw contributions can still underflow or round at floating-point precision. Extremely different grades may have negligible contributions below that precision.

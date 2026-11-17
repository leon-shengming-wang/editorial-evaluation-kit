# Evaluation Regression Lab

**Compare imported evaluation scores with paired evidence, coverage and uncertainty.** A small, complete, dependency-free command-line analysis tool with an offline HTML report. It does not call models, generate answers or decide their quality. It answers a narrower question: on matching items scored using a comparable procedure, how did the candidate change?

This is an AI-assisted engineering portfolio project. Every committed example score is deliberately authored synthetic data, not a real model benchmark, client result or claim of independent coding experience.

## Run

Python 3.9 or newer; standard library only. From this directory:

```sh
python3 -m regression_lab examples/baseline.json examples/candidate.json \
  --json my-report.json --html my-report.html
python3 -m unittest discover -s tests -v
```

Open the generated HTML in a browser. The committed `examples/report.html` is also self-contained: download its raw file and open it. GitHub's code view does not execute or render an HTML report. No network, account, API key or model costs are required.

`--resamples` defaults to 2000 (range 100–5000); `--seed` defaults to 17 (integer 0–4294967295). Omitting both output flags prints JSON. Outputs must be distinct, new paths; the CLI never overwrites existing files. Invalid input returns exit status 2. Two-file output is not transactional: an I/O failure can leave one partial/new artifact; inspect before sharing.

## Input contract

Each run has exactly these fields:

```json
{
  "schema_version": 1,
  "run_id": "my-baseline",
  "dataset_id": "my-evaluation-set",
  "dataset_version": "2026-11-17-v1",
  "metric": "human-rubric-v2-normalized",
  "direction": "higher",
  "items": [
    {"id": "example-001", "score": 0.7, "slice": "evidence"}
  ]
}
```

- Scores must be finite numeric values in **[0,1]**, never booleans. This deliberately excludes unnormalized latency, token cost or other scales. Normalize upstream only with a defensible fixed procedure and name it in `metric`.
- `direction` is `higher` or `lower`. Improvement is candidate minus baseline for `higher`, its negative for `lower`. Raw deltas remain visible.
- Dataset ID, dataset version, metric and direction must match. A matched item's slice must not change. These labels are assertions supplied by the caller, not proof that prompts, scoring rubrics, judge versions or sampling procedures were actually identical. Encode the evaluator/rubric version in `metric`; verify the rest before comparing.
- Each item ID is unique within a run. One slice label per item; one to 1000 items per file, 2 MB file cap, text fields at most 500 characters, maximum nesting 100. Duplicate JSON keys and unknown fields are rejected.
- Pairing uses IDs, not row order. Unmatched IDs are listed and excluded, never converted to zeros. Means and intervals use only matched pairs. Missing-item bias is not corrected.

## Statistics, precisely

The statistic is the arithmetic mean of per-item direction-normalized differences. A paired bootstrap samples the **same item index for both runs**, equivalently resampling their differences with replacement. Each replicate contains the original matched sample size. The 95% percentile interval uses linearly interpolated empirical 2.5th and 97.5th percentiles. This is not BCa, a hypothesis test or a p-value.

Each overall/slice analysis uses the reported seed and number of replicates on ID-sorted pairs. Fingerprints normalize JSON key and item order; run metadata and scores remain part of identity. The report has no execution timestamp, so the same input/settings reproduce the same output in the tested Python environments. Hashes establish content identity, not authenticity.

No interval is reported for zero or one pair. Fewer than 20 pairs, constant observed differences, or an interval crossing zero produce an `uncertain` signal. The threshold of 20 is an explicit conservative display policy, **not a mathematical guarantee of adequate sample size**. Constant differences can produce a point interval; the UI still warns that this does not establish certainty. `positive_interval`/`negative_interval` describe only the observed resampling interval, not deployment approval or statistical significance. Per-slice intervals are exploratory and unadjusted for multiple comparisons.

## What it cannot establish

The bootstrap assumes independent, representative paired items. Correlated prompts, repeated users, selection bias, annotator noise and model/evaluator randomness are not modeled. Use cluster resampling or repeated-run designs elsewhere when appropriate. A confident-looking interval cannot repair poor labels, noncomparable evaluators or incomplete coverage. Scoring is imported, not independently verified; no semantic/factual correctness claims are made. All output includes IDs and scores, so keep confidential evaluation material out of public repositories.

## Research basis and design choices

- [SciPy bootstrap documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html): paired resampling preserves corresponding observations, and multiple interval methods exist. This implementation independently uses the simpler percentile method and declares it, rather than implying SciPy's default BCa behavior.
- [EleutherAI evaluation harness interface](https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/interface.md): explicit evaluation configuration and seeds support reproducibility. Here, input fingerprints, declared metric/dataset versions and fixed resampling settings make the narrower score-comparison operation reproducible.

No code was copied from those projects. This is not a wrapper or endorsement, and its results are not interchangeable with their full model-evaluation pipelines.

## Verification

17 tests cover hand-calculated means/quantiles, direction reversal, paired resampling, zero/one-pair coverage, small/constant samples, metadata mismatches, finite scores, duplicate IDs/keys, HTML escaping, deterministic ordering and CLI overwrite protection. The committed demonstration intentionally includes a baseline-only and a candidate-only item so coverage loss remains visible.

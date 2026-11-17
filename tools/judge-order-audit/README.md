# Judge Order Audit

**An offline reliability check for imported pairwise judge decisions.** Run the same answer pair in A/B and B/A order elsewhere, then inspect whether the judge's preference survives the reversal. This tool makes no model calls and incurs no API charges.

It is a focused companion to Answer Compare: that tool checks explicit response constraints and records human reviews; this tool audits the *order stability of an existing judge*, not the quality of answers themselves.

## Run

Python 3.9+; standard library only. From this directory:

```sh
python3 audit.py examples/synthetic.json --output-dir output/demo
python3 -m unittest discover -s tests -v
```

Open `output/demo/report.html` locally, or inspect `report.json`. The HTML is self-contained, responsive, script-free, and escapes imported text. No server, network, packages, credentials or model are needed. Exit status is 0 on success, 2 for invalid input or filesystem errors. Existing report files are protected; use a new directory or explicitly pass `--force`. Both paths are checked before writing; filesystem failure during writing can still leave a partial report, so trust success only on exit 0.

A committed example is in `examples/report/report.html` with its JSON counterpart. **Every decision in that example is synthetic**, not a recorded run from a real model.

## Input contract

Strict UTF-8 JSON, maximum 8 MiB and 10,000 cases. Duplicate keys, unknown fields, non-finite values, duplicate case IDs and malformed records are rejected. No silent deduplication or automatic parsing of judge prose.

```json
{
  "schema_version": 1,
  "data_kind": "imported",
  "judge": "Your actual model version and sampling configuration",
  "rubric": "The unchanged rubric used for both runs",
  "cases": [
    {
      "id": "pair-001",
      "original": {"verdict": "first", "reason": "Optional supplied rationale"},
      "swapped": {"verdict": "second", "run_id": "Optional source run identifier"}
    }
  ]
}
```

- `data_kind`: `synthetic` or `imported`. A label supplied by the operator, not independently verified provenance.
- `original`: candidates shown as **[A, B]**. `swapped`: same candidates shown as **[B, A]**.
- `verdict`: `first`, `second`, `tie` or `abstain`. These are *positions as presented to the judge*, never permanent identity labels. If your source says A/B but means displayed labels, convert to first/second explicitly. If it means original identities, perform the reverse mapping for the swapped run before import.
- Missing or failed run: use JSON `null` for the entire run. Both run keys are required so missingness is intentional. An observed `abstain` is different from no run.
- Optional per-run `reason` and `run_id` preserve the actual source record. Do not invent a rationale for an unrecorded run.
- Optional per-case `prompt`, `answer_a`, `answer_b` document original identities. Optional top-level `notes` can record collection method and limitations. All optional strings, when supplied, must be nonempty.
- Judge name maximum 300 characters, rubric 2,000, case ID 200, other strings 20,000. Use a separate input per model/rubric/configuration; these fields cannot verify that the upstream runs truly used identical settings.

This format imports categorical preferences, **not numeric ratings or preference probabilities**. Decide and document your own rating-to-verdict conversion upstream; the tool does not assume scales are comparable, select thresholds, or average scores.

## Mapping and outcomes

| Presented verdict | Original A/B run | Swapped B/A run |
|---|---|---|
| first | A | B |
| second | B | A |
| tie | tie | tie |
| abstain | abstain | abstain |

Mutually exclusive categories follow this precedence:

1. **missing**: either run absent, even if the other abstained or tied.
2. **abstain**: both present, at least one abstention.
3. **tie**: both present without abstention, at least one tie. Both tied and tie-versus-decisive are separately counted.
4. **consistent**: both decisive and prefer the same original answer.
5. **flipped**: both decisive and prefer different original answers.

**Flip rate = flipped / (consistent + flipped).** Ties, abstentions and missing pairs do not enter that denominator and are never presented as agreement. No eligible pairs gives JSON `null` and HTML `N/A`, not 0%. Coverage shows observed runs out of 2×cases and complete pairs out of all cases. The first-position rate is first picks divided by all observed decisive runs, including unpaired runs; treat it as descriptive, not a balanced estimate of bias.

The JSON includes exact counts, normalized identities, original records and a canonical-input SHA-256 for traceability. Ratios are rounded to six decimals. The fingerprint uses sorted-key compact ASCII JSON of the validated input, not raw file bytes. Identical input produces byte-identical report content; no current timestamps are inserted.

## Suggested workflow

1. Preserve the same original prompt, responses, rubric and judge configuration. Independently collect both presentation orders; retain failures as null.
2. Import actual categorical decisions, ideally with source run IDs. Do not mix synthetic fixtures into measured results.
3. Inspect missing coverage first, then flips, tie changes and abstentions. Use the HTML's expandable source records to audit conversion errors.
4. Send unresolved cases to a human reviewer. Repeat with independent runs before attributing a change to ordering rather than randomness.

## Research basis and scope

- Lee et al., *RLAIF vs. RLHF: Scaling Reinforcement Learning from Human Feedback with AI Feedback*, section 2.1.1, describes reversed-order inference and averaging preference distributions to mitigate position bias: https://arxiv.org/html/2309.00267v3 . This tool uses the reversal idea as an **audit diagnostic**; it does not reproduce their probability averaging, training setup or results.
- Zheng et al., *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*, studies limitations including position and verbosity bias: https://arxiv.org/abs/2306.05685 . Stability is not factual accuracy or agreement with humans.
- The authors' FastChat LLM Judge documentation separates generation, judgments and evaluation artifacts: https://github.com/lm-sys/FastChat/blob/main/fastchat/llm_judge/README.md (readable source: https://raw.githubusercontent.com/lm-sys/FastChat/main/fastchat/llm_judge/README.md). This is an independent implementation, not a FastChat-compatible adapter or a copied benchmark.

No statistical significance or causal effect is claimed. A single flip could be sampling variation, prompt drift, conversion error or position sensitivity. Repeated correlated cases can distort rates. A stable but consistently wrong judge will look stable here. This report cannot establish candidate quality, hiring fitness or benchmark leadership. Reports contain supplied prompts and rationales, so keep confidential inputs and generated files private.

## Tests

The tests exercise all 25 combinations of decisive/tie/abstain/missing runs, both identity mappings, denominator behavior, duplicate JSON keys and IDs, non-finite values, schema and Unicode rejection, HTML injection escaping, deterministic outputs, CLI execution, overwrite protection and failure without report creation.

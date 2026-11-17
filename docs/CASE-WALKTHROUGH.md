# A review you can inspect in 60 seconds

> Synthetic, AI-assisted exercise. These are authored candidates, not outputs from a measured model run. No employer or client material is used.

## Task

Write a factual headline of no more than 12 words. Preserve the distinction between a proposal and an approved decision.

## Available evidence

A fictional council has proposed extending library hours. No extension has been approved; the vote is due next month.

| Candidate | Headline |
| --- | --- |
| A | Riverton council approves library hours extension until 9 p.m. |
| B | Riverton council proposes later library hours; vote due next month |

## Decision: B

A is readable but turns a proposal into an approval. The word **“approves”** is the decisive defect. B preserves both the proposal and the pending vote. At 10 whitespace-delimited words, it also meets the explicit length constraint.

| Dimension | A | B |
| --- | ---: | ---: |
| Source fidelity / accuracy | 1 | 5 |
| Instruction following | 2 | 5 |
| Clarity | 5 | 5 |
| Weighted total (`2 × accuracy + instructions + clarity`) | 9 | 20 |

**Why not reward A's confident wording?** Clarity cannot repair a central factual error. The conclusion must follow the supplied source, not what sounds more decisive.

**What remains unknown?** The exercise supplies fictional ground truth. It does not establish any real council action, library schedule, or external fact.

**What does the code check?** That the quote occurs in the response, fields and scores are valid, and the declared winner matches the stated weighting rule. It does not independently know whether the source is trustworthy or the judgment is correct.

See the full record `ed-001` in [the dataset](../data/cases.jsonl). Compare the [rubric](RUBRIC.md), [validator](../reviewbench/core.py), and [tests](../tests/test_core.py).

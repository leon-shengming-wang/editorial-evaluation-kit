# Review rubric

## Purpose and provenance

This is an AI-assisted, synthetic demonstration of evidence-based evaluation. All organizations, figures, source passages, responses, and evaluation decisions in the sample dataset were authored for this project. They are not live model outputs, employer assessments, confidential platform tasks, or measurements of Leon's production performance. The examples require owner review before being described as his personally completed evaluations.

The dataset covers editorial fidelity, closed-source fact checking, documented design specifications, and transcript-reference QA. A text-only design note is **not** a rendered design assessment; a transcript comparison is **not** an audio listening test.

## Review sequence

1. Read the task and identify explicit constraints.
2. Establish what the supplied source can and cannot support.
3. Score each response independently on the three dimensions below.
4. Quote exact response text and explain its relationship to the source or instruction.
5. Record uncertainty. Do not substitute plausibility for evidence.
6. Calculate the preference using the rule below. Use `abstain` when the required fact cannot be resolved from available evidence.
7. Recheck numbers, negation, names, scope, dates, and the selected label.

## Anchors

Scores are integers from 1 to 5. Scores are ordinal judgments, not calibrated probabilities.

| Score | Accuracy / source fidelity | Instruction compliance | Clarity |
| --- | --- | --- | --- |
| 5 | All material claims supported; no material distortion | All explicit requirements met | Clear, concise, unambiguous for the task |
| 4 | Minor imprecision without changing the central meaning | Minor nonessential constraint missed | Small wording or organization issue |
| 3 | Mixed fidelity or a meaningful omission | Partially fulfills the task | Understandable with noticeable ambiguity |
| 2 | Major error, but some relevant facts preserved | Major requirement missed; some relevant task elements retained | Hard to follow or substantially ambiguous |
| 1 | Central claim false, reversed, or unsupported | Essential task requirement fails | Unusable or incomprehensible |

Accuracy concerns whether a response's claims match the supplied evidence. Instruction compliance concerns whether it does the requested work. These dimensions can overlap but should not be collapsed. A clearly documented design proposal can truthfully state noncompliant specifications: its accuracy may be 5 while instruction compliance is 1. Unsupported answers are scored low for support, not asserted to be false in the real world.

## Deterministic preference rule

`total = 2 * accuracy + instructions + clarity` (range 4 through 20).

- Higher total: select `A` or `B`.
- Equal total with sufficient evidence: select `tie`.
- Insufficient source evidence to resolve the task's central requested fact: select `abstain`, regardless of the arithmetic.

The weights are this demo's design choice, not any platform's proprietary rubric. They emphasize factual fidelity but do not guarantee that a material factual error always loses against a response with unrelated weaknesses. A production rubric may need explicit critical-error gates and separate acceptability labels. A preference only means better under this rubric; it does not mean either answer is safe to publish.

## Evidence and uncertainty

Every record includes exact quoted spans from response A and/or B. A quote's presence can be checked mechanically; whether its explanation is sound requires human review. The validator cannot determine factual truth, hear audio, inspect unseen layouts, or certify professional judgment. The source is the closed-world ground truth for these fictional cases, not a citation to a real event.

An uncertainty statement should distinguish missing information from known defects. A tie is not the same as an abstention. The procurement and unclear-street cases deliberately demonstrate abstention: both candidates are readable, but neither proposed answer is established.

## Dataset boundaries

There are 14 deliberately small authored cases: four editorial, four design, three fact-check, and three transcript-reference exercises. The final two cases deliberately explore competing constraints and the limitations of additive scores. Winner balance is a teaching choice, not a natural distribution. There are no independent raters, adjudication study, agreement statistics, model rankings, hiring claims, or external quality certifications. Expanding the dataset should preserve this provenance distinction and add independent review before making performance claims.

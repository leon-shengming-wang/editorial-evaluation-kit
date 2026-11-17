# Calibration lab: disagreement is a question, not a verdict

Two reviewers can agree on a wrong answer. They can also disagree because the rubric is ambiguous, evidence is missing, or they prioritize different requirements. This tool makes those differences visible without labeling a person as a bad reviewer.

## Inspect the demonstration

[Download the offline visual audit](../reports/agreement-demo.html) with GitHub's **Download raw file** button and open it locally. [Read the JSON](../reports/agreement-demo.json) directly on GitHub.

All demonstration ratings and reasons are **AI-authored simulations**. The named simulated reviewers are not people, and the numbers are not Leon's performance or measured human agreement. The demonstration uses five paired records and one left-only record. Three of the five pairs match, so observed agreement is 0.6; expected agreement is 0.2 and Cohen's kappa is 0.5. These small, deliberately constructed numbers are only an arithmetic example.

Reproduce both outputs from the repository root:

```sh
python3 -m examples.agreement_demo
```

This command replaces the two committed **demonstration** reports. It does not read your local reviews.

## Use actual local reviews

First follow [the calibration instructions](CALIBRATION.md) to import cases and record real reviews in a local database. Use distinct reviewer IDs only for genuinely distinct reviewers. Do not manufacture a second review to increase coverage.

```sh
# Read-only: prints JSON; does not create or modify the database.
python3 -m reviewbench.agreement my-reviews.sqlite3 reviewer-one reviewer-two

# Save a new file, never overwrite a previous report.
python3 -m reviewbench.agreement my-reviews.sqlite3 reviewer-one reviewer-two --output my-agreement.json
python3 -m reviewbench.agreement my-reviews.sqlite3 reviewer-one reviewer-two --html my-agreement.html
```

Only the **latest** rating per reviewer/case is compared. The original SQLite history remains intact. The database must already exist and provide the ReviewBench `latest_reviews` view. The underlying case store rejects changed content under an existing case ID, so the two reviewers refer to the same imported version. Reviewer IDs are exact and case-sensitive.

## Interpretation contract

- Shared cases form the denominator. Unpaired cases are listed separately, not silently counted as disagreement.
- A, B, tie, and abstain are four nominal categories. Two abstentions count as matching labels, **not** as two correct answers.
- Exact agreement is matches / shared cases.
- Expected agreement is the sum of the product of the two reviewers' marginal label proportions.
- Cohen's kappa is `(observed - expected) / (1 - expected)`. No overlapping ratings produces null metrics; identical constant labels produce undefined kappa rather than an invented 1.0.
- The confusion matrix is directional: first reviewer's labels are rows, second reviewer's labels are columns.
- The queue preserves both reasons. Resolve a disagreement by checking the source, uncertainty and rubric. A majority vote is not a substitute for evidence.
- No pass/fail cutoff, confidence interval, population inference, model leaderboard, or employment claim is made. Label prevalence and sample selection affect kappa.

## Protect your work

The audit opens SQLite in read-only mode and performs no schema changes. JSON and HTML output use exclusive creation. No external scripts, fonts, analytics, or network services are involved. The HTML escapes reviewer-provided text rather than executing it.

Reports contain reviewer IDs, case IDs and reasons. Inspect them before sharing. Keep platform tasks, proprietary guidelines, client information and personal data out of this public repository. The store is append-only through its API, not tamper-proof against someone editing the file directly. A failed disk write can leave an incomplete new report; inspect and use a new filename if necessary.

## Why this belongs in an evaluation portfolio

The useful artifact is not a high agreement number. It is a reviewable process: document the comparison set, identify excluded data, expose the conflicting reasons, and record a new reasoned decision without rewriting history. This complements the editorial cases and visual-layout preflight rather than adding unrelated technology labels.

Research consulted November 17, 2026:

- https://www.dataannotation.tech/faqs — official descriptions emphasize comparison, fact checking and explanations. This is a skill reference, not eligibility or hiring advice.
- https://github.com/huggingface/evaluation-guidebook/blob/main/contents/human-evaluation/basics.md — human evaluation methods and their limits.
- https://github.com/BobbY-24/human-annotation-eval-toolkit — an independent public repository organizes multi-annotator analysis around agreement and disagreement. We adopted the broad presentation idea, not its code, data, claims or identity.

Implementation, examples and documentation were developed with AI assistance. No employer endorses this project.

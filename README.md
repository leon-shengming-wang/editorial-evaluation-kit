# ReviewBench
### Evidence before preference.

An English-only, AI-assisted evaluation workbench focused on editorial judgment, source fidelity, and design review. It makes an A/B decision inspectable: **what was requested, what the source supports, what each response did, and why one was preferred.**

This is a learning and portfolio project created for Leon Wang's editorial and AI-review interests. The code, examples, and documentation were developed with AI assistance. The examples are deliberately authored synthetic exercises, not confidential platform tasks, outputs from measured model runs, or claims about Leon's independent coding proficiency. They have not been independently human-rated.

## Start here

- [Read a 60-second case walkthrough](docs/CASE-WALKTHROUGH.md), rendered directly on GitHub.
- [Download the visual case report](reports/index.html) using GitHub’s download-raw-file button, then open the downloaded HTML in your browser. GitHub’s source view does not run HTML.
- [Explore three subtle decision walkthroughs](docs/SUBTLE-DECISIONS.md): observation cutoff, semantic fidelity, and unresolved transcript meaning.
- [Inspect the scoring rubric](docs/RUBRIC.md).
- [Read the raw cases](data/cases.jsonl).
- [See the automated checks](tests/test_core.py).
- [Inspect the SQL calibration workflow](docs/CALIBRATION.md).
- [Read the verification record](docs/VERIFICATION.md).

## Practice before reading the answer

Export a worksheet without reference scores, labels or rationales:

```bash
python3 -m reviewbench.practice data/cases.jsonl --category language --category audio --output my-practice.md
```

[Open the ready-to-use blank worksheet](docs/PRACTICE-WORKSHEET.md).

The exporter refuses to overwrite an existing file, protecting your notes. Read the supplied source, form a decision and quote evidence before comparing it with the authored reference. Each worksheet records a SHA-256 fingerprint of the displayed input, so changed source material can be distinguished from changed reference judgments. A hash identifies content; it does not certify truth or authorship. This reduces answer anchoring; it is not a secure or independently administered assessment. Keep real review notes private unless you have checked their contents. If an export is interrupted or disk writing fails, a newly created worksheet can be incomplete; inspect it before use and export to a new filename. See [the language and transcript review lab](docs/LANGUAGE-AUDIO-REVIEW.md).

## Companion project: Layout Preflight

[Layout Preflight](tools/layout-preflight/README.md) turns original design specifications into visual SVG specimens and a concrete QA queue. Compare a deliberately flawed exhibit-style layout with its corrected version, then inspect the contrast, margins, typography and geometry rules. This is a separate runnable project with its own examples, tests and limitations, not an image-quality or accessibility certification.

## Run in one minute

Python 3.9 or newer. No dependencies, API key, account, or network connection required.

```bash
python3 -m unittest discover -s tests -v
python3 -m reviewbench data/cases.jsonl --html reports/index.html --json reports/summary.json
```

Open `reports/index.html` in your browser. The report works offline, including on a narrow mobile screen. Generated results can be reproduced from the dataset; invalid records stop report generation with a nonzero exit status and line-numbered errors.

## What this demonstrates

| Skill | Inspectable evidence |
| --- | --- |
| Follow a written rubric | Three explicit dimensions and a declared weighting rule |
| Preserve source meaning | Self-contained fictional source alongside each A/B response |
| Explain a judgment | Exact response quotes and concrete reasons, rather than "B is better" |
| Recognize uncertainty | Explicit limitations; abstention when evidence is insufficient |
| Check data quality | Strict fields, types, score ranges, duplicate IDs, exact quotes, and decision consistency |
| Build reproducible tools | Standard-library Python CLI, unit tests, deterministic HTML and JSON reports |

The 17 synthetic cases cover five categories. For less obvious decisions, inspect `ed-004` (length versus uncertainty), `ds-004` (different defects), `fc-004` (observation cutoff), `lg-001` (units and modality), and `au-004` (unresolved meaning). These distinguish preference from publishability; the language case is English-only semantic QA, not a bilingual proficiency test.

## Design choices

Accuracy counts twice, while instruction following and clarity count once: `2 × accuracy + instructions + clarity`. This is an illustrative editorial rubric, **not a platform's proprietary policy**. A tied total is recorded as a tie; an abstention records insufficient evidence rather than inventing confidence. Reviewers should not equate a numeric score with objective truth.

The validator checks internal consistency and data shape. It cannot determine whether a rationale is sound, whether a claim is true, or whether someone genuinely performed a task. Those still require human review. The label distribution is descriptive only; these hand-built examples cannot support model accuracy, reliability, hiring success, or inter-rater agreement claims.

## Why this project rather than ten empty repositories?

Public role descriptions repeatedly emphasize careful comparison, following instructions, fact checking, and explaining decisions. A small complete artifact makes those practices easier to inspect than a list of technology names.

Research references (read November 2026; role requirements may change):
- [DataAnnotation FAQ](https://www.dataannotation.tech/faqs): comparison, fact checking, and challenging prompts.
- [Handshake generalist evaluation role](https://joinhandshake.com/ai/opportunities/generalist-bachelor-ai-eveluation-specialist/): written instructions and critical reasoning. This is a skill reference, not a statement of eligibility.
- [Mercor graphic designer role](https://work.mercor.com/jobs/list_AAABoVBmFZ_RhmSVwadDBrXW/graphic-designers-must-own-macbook): layout, typography, workflow, and explanation of creative choices.

No employer endorses this project. No private platform guidelines, client material, application answers, or personal conversations are included.

## Repository map

```
data/cases.jsonl       Synthetic, self-contained A/B review records
docs/RUBRIC.md         Scoring anchors and limits
reviewbench/core.py   Strict loader, validation and summaries
reviewbench/report.py Escaped, offline HTML report
reviewbench/audit.py  Transactional SQLite case and review history
reviewbench/calibrate.py Usable import/review/history CLI
reviewbench/__main__.py Command-line interface
tests/test_core.py    Positive, negative and security-focused tests
reports/             Reproducible example outputs
```

## Next improvements

- Have a human reviewer independently assess cases and record disagreements without retroactively editing the original judgment.
- Add genuine consented public-work examples with explicit provenance, separate from synthetic exercises.
- Test a design-specific rubric with original visual artifacts; current design cases are text-described scenarios, not image-model evaluation.

Report files are staged before replacement so invalid destinations do not produce a partial report. Each file replacement is atomic, but replacing two outputs is not a single filesystem transaction; a process crash between replacements can leave different generations. Regenerate both outputs together after an interrupted run.

No hiring outcome or production readiness is implied.

# What changed after review

This project was built with AI assistance and checked through separate code and content review passes. Those passes are not independent human ratings, a security audit, or evidence of employer approval. The notes below describe actual corrections made during development, not hypothetical accomplishments.

## 1. A successful first output did not mean a successful export

**Observed:** the report CLI wrote HTML before discovering that the JSON destination's parent directory did not exist. It returned failure but left one newly generated output behind.

**Change:** validate destinations first, stage output files, then replace them. Tests exercise missing directories, input/output aliasing, and invalid data.

**Remaining limit:** replacing two files is not a single crash-atomic transaction. A crash between replacements can leave different generations. Regenerate both together after an interrupted run.

## 2. Finite-number validation still crashed on an enormous integer

**Observed:** the design-spec companion passed a very large Python integer to a float-oriented finiteness check, raising an overflow error before returning its intended validation message.

**Change:** bound numeric inputs before float conversion. Every numeric value is limited to an absolute magnitude of 100,000; canvas dimensions have a tighter 10,000-pixel limit. Regression tests cover huge integers and extreme geometry, type sizes, and rules.

**Remaining limit:** valid rectangles are not measured text glyphs. Passing these checks does not prove actual text fits, that fonts render identically, or that a design is accessible.

## 3. Local tests passed, but the first hosted build failed before testing

**Observed:** `ubuntu-latest` resolved to Ubuntu 26.04, for which the requested Python 3.9 build was unavailable. The matrix's default fail-fast behavior also canceled the other job.

**Change:** pin the runner to Ubuntu 22.04 and disable matrix fail-fast. Both Python 3.9 and 3.12 subsequently completed the main and companion test suites successfully.

**Remaining limit:** a pinned runner is not permanent maintenance. It must be reviewed when supported runner or interpreter versions change. The repository's verification record identifies tested revisions rather than treating a workflow file as proof of a passing build.

## 4. A plausible word count was wrong

**Observed:** an authored explanation called a headline eleven whitespace-delimited words long; it actually contained ten.

**Change:** correct the JSONL record, Markdown walkthrough, and regenerated report. Add a regression that counts words in both length-sensitive examples and checks the accompanying explanations.

**Lesson:** a schema-valid record can still contain an incorrect explanation. Automated structure checks and substantive review answer different questions.

## 5. Wrong meaning is not automatically poor clarity

**Observed:** a punctuation example was scored down for clarity even though its wording was fluent; the principal defect was that commas changed the scope of a restriction.

**Change:** retain the source-fidelity penalty but restore clarity to 5. The comparative total changed from 10 to 12. The other candidate still ranks higher, but neither meets the strict transcript brief. The explanation also distinguishes a possible pragmatic reading from a demonstrated semantic reversal.

**Lesson:** explain each dimension separately. Do not quietly count the same defect twice unless the rubric explicitly supports it.

## 6. A reference report is not an independent practice session

**Observed:** displaying an authored label alongside a case makes it easy to repeat the answer without forming a judgment.

**Change:** add a separate worksheet exporter that omits reference scores, labels, rationales, evidence annotations, and uncertainty judgments. It retains the task, source, and candidate responses. An input fingerprint identifies what the reviewer actually saw without incorporating the hidden reference decision.

**Remaining limit:** references are public in this repository, so this is not a secure examination. No human practice results have been collected or claimed. The exporter refuses to overwrite existing notes; an interrupted new export can still be incomplete.

## What to inspect

- [Tests](../tests/): reproducible implementation checks.
- [Verification record](VERIFICATION.md): what ran and what remains unverified.
- [Language and transcript lab](LANGUAGE-AUDIO-REVIEW.md): readable judgment and acceptance distinctions.
- [Blank practice worksheet](PRACTICE-WORKSHEET.md): a place to form a real judgment before opening the reference.

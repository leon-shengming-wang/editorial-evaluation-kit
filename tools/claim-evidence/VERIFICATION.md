# Verification record — 2026-11-17

## Evidence available at this revision

- 42 fast deterministic tests cover exact spans (including Unicode, abbreviations and semicolons), local retrieval, missing evidence, numeric/negation cues, duplicate-source aliases, skipped passages, source metadata, URL restrictions, consent, fixed encoded discovery paths, network failure without fabricated evidence, redirect/size/JSON rejection, and loopback host/origin/token protections.
- A real Wikimedia lookup for the explicitly public query `NASA operations 1958` returned readable summaries for NASA, Creation of NASA and NASA Deep Space Network. This confirms the path worked at test time, not ongoing availability, independence or correctness.
- Public demo excerpts were checked against the NASA/National Archives links recorded in the README. The response itself was deliberately authored with errors and an opinion. No confidential platform material was used.

## Independent review and fixes

Review found two important issues: edited sources retained automatic-retrieval provenance, and inputs changed during an in-flight request could make stale results exportable. Both were corrected: source edits clear current retrieval attribution/dates while retaining original-source attribution and license; input revision tracking discards stale responses. Source last-modified timestamps remain distinct from publication dates, source licenses are retained, skipped passage coverage is visible, and duplicate text preserves alternate links.

## Honest limitations

This is deterministic candidate extraction and evidence triage, not autonomous semantic truth detection. No accuracy rate, comprehensive claim recall or fact-checking certification was measured. Strong lexical overlap can still compare different events. Source authenticity, currency, independence and final interpretation remain human responsibilities. The live lookup is limited to secondary-source summaries. Browser and source-network verification details are finalized only after the corresponding tests succeed.

## Actual browser integration

An isolated Chromium instance exercised the public demo end to end: candidate extraction, source passage display, numerical cue, rationale/evidence gates, JSON export preserving unreviewed automation separately from test-entered conclusions, deliberately delayed response with input edits, consent denial, query-change approval reset, actual public Wikimedia retrieval, adding a retrieved source, and source-edit provenance handling. No JavaScript errors or horizontal mobile overflow occurred. Desktop and mobile screenshots were inspected. The test's adjudication was an automated UI test, not Leon's review or an independently rated dataset.

The first browser test harness hit the page's deliberate no-unsafe-eval CSP restriction. The harness was corrected to use locator assertions; the application security policy was not relaxed. Safari/Firefox, assistive technologies, long-document performance and broad factual accuracy were not independently validated.

Original-source licensing is retained separately after edits and in duplicate aliases. Browser export after editing was checked to preserve original attribution without falsely retaining a current retrieval timestamp.

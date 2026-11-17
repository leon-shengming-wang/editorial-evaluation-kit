# Independent Review Desk

A self-contained browser workspace for reviewing the 17 synthetic cases without seeing their reference judgments. It is a usable interface, not a screenshot or a mock product claim.

## Open it

[Download `review-desk.html`](../reports/review-desk.html) using GitHub's **Download raw file** button, then open the downloaded file in a browser. GitHub's normal source view does not execute HTML. There is no installation, account, API key or model bill.

The desk puts the assignment and source first, then two response cards, then the decision, exact evidence, reason and uncertainty fields. It does not prefill a decision or embed reference scores. Use the existing reference report separately, after making an independent judgment.

## What works

- All 17 cases are selectable, with Previous/Next controls.
- Typing automatically keeps the current draft **in the open tab**, including incomplete reviews. Switching cases does not discard text.
- A progress indicator counts only records with a decision, a nonempty reason and an exact source/response quote. It does not grade the reason or certify correctness.
- Download saves touched cases, including incomplete drafts, as JSON with an input fingerprint.
- Restore checks the format, case IDs, fingerprints, decision values, duplicate cases and text sizes before replacing anything. Replacement of an existing draft asks for confirmation. A mismatched dataset is rejected rather than silently attaching old reviews to new source material.
- A close/refresh warning remains active after a download request because the interface cannot verify whether the browser actually saved the file.

## Privacy and persistence

Nothing is uploaded. There is no analytics, server, external font, API call, browser storage or background synchronization. A restrictive content security policy blocks network connections. Input text is rendered as text, not executable markup.

**Closing or refreshing can lose unsaved drafts.** Download the JSON and check it exists before leaving. The warning is a convenience, not a guarantee: browsers can suppress unload prompts. The downloaded JSON contains your own writing; keep it private. It is not automatically imported into the SQLite audit store and is not independently verified evidence of a human review.

This desk supports the bundled synthetic practice cases only. Do not use it to export confidential platform tasks, user information or proprietary guidelines into a public repository.

## Reproduce

From the repository root:

```sh
python3 -m reviewbench.desk data/cases.jsonl --output my-review-desk.html
```

An existing destination is protected. The generator uses the validated dataset, selects only the visible input fields, and embeds an input fingerprint for each case. Labels, scores, rationales and reference evidence are omitted. This reduces answer anchoring, but it is not a secure assessment: the reference data remains public elsewhere in this repository.

## Verification and known limits

- Python tests verify label-free payloads, safe JSON embedding, offline structure and overwrite protection.
- A dependency-free JavaScript state harness exercises initialization, next/previous boundaries, preservation across case changes, completion accounting, exact-quote checks, abstention, export/restore round trips, changed-input rejection, invalid fields, duplicate cases and inert markup handling.
- The state harness uses Node when available and JavaScriptCore on macOS. CI explicitly installs Node so these checks cannot silently skip there.
- The harness is a DOM stub, not a real browser. It does not prove pixel-level layout, native download/save behavior, file-picker dialogs, printing or browser unload prompts. A headless Chrome attempt in this development environment returned no DOM output, so no visual browser pass is claimed.
- Draft JSON has a 1 MB restore limit and 12,000-character field limits. No encrypted storage, collaboration, real-time syncing or automatic SQLite import is implemented.

The source and examples were developed with AI assistance. No claim is made that Leon independently wrote the implementation or that a platform endorses it.

# Calibration without invented performance

A useful review history preserves the original decision, the changed decision, and the reason. It does not silently rewrite a prior judgment to make agreement look better.

`reviewbench.audit.AuditStore` provides a local SQLite history for practicing that workflow. Importing the same case twice is safe. A different payload with the same ID is rejected, so a changed prompt cannot silently replace the case that a reviewer originally saw. Imports are transactional; SQL parameters are bound, not concatenated.

```python
from reviewbench.core import load
from reviewbench.audit import AuditStore

with AuditStore('practice.sqlite3') as store:
    store.import_cases(load('data/cases.jsonl'))
    # Add only reviews you actually perform. Use a pseudonym if appropriate.
    # store.add_review('ed-001', 'reviewer-1', 'A', 'Explain the exact evidence here.')
    print(store.disagreements())
```

Do not upload a real review database without checking its contents and permission. The repository does not include a database, real reviewers, or fabricated review sessions.

The disagreement query compares the latest review per case and reviewer against the **authored reference label**. It is not an accuracy metric. Reference labels may be wrong. Reviewers should resolve differences by inspecting the source and rubric, then append a new decision with an explanation. A tie or abstention can be a responsible outcome.

The database records UTC timestamps, case hashes, and sequential review IDs. This is a convenient audit trail, not a tamper-proof system: anyone who can edit the database file can alter it. There is no authentication, concurrent team workflow, or production access control.

## No-code command-line workflow

Import cases without generating any fake reviews:

```bash
python3 -m reviewbench.calibrate --database practice.sqlite3 import data/cases.jsonl
```

After actually reading a case and forming a judgment, record your own decision and reason. Replace the placeholder below with your real evidence, not a generic compliment:

```bash
python3 -m reviewbench.calibrate --database practice.sqlite3 review ed-001 --reviewer reviewer-1 --winner B --reason "Replace this with your specific source-based reasoning."
python3 -m reviewbench.calibrate --database practice.sqlite3 history ed-001
python3 -m reviewbench.calibrate --database practice.sqlite3 disagreements
```

The last command returns disagreements for discussion, not a leaderboard. Recording a correction appends another row and retains the earlier decision. Keep personal or confidential information out of reviewer names and reasons.

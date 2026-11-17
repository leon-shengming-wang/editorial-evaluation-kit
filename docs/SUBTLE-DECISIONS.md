# Three decisions that need more than a score

These are authored synthetic demonstrations, not independently rated model outputs. Read the complete prompts, fictional sources, responses, scores and exact evidence in [the dataset](../data/cases.jsonl).

## 1. The newest number is not always admissible: `fc-004`

A status note has a noon cutoff. The same primary office reports 600 outages at 11:55 and 420 at 12:10. The second number is newer, but it cannot be used to describe what was known at noon. These updates are successive snapshots, not proof that one source is unreliable.

A preserves the admissible count and its time but drops a condition on reopening. B preserves that condition but imports future information. A wins narrowly, 14 to 13. Accuracy 3 reflects A's meaningful omission; assigning 4 would understate the defect. Neither answer is ready to publish.

**Corrected handoff:** At 11:55, the municipal operations office reported 600 properties without power. The community center could reopen at 14:00 if its electrical inspection passes.

**Transferable check:** Separate event time, observation time, and publication cutoff. Preserve conditions even when shortening copy.

## 2. Correct arithmetic can conceal changed meaning: `lg-001`

Both candidates correctly convert 1.2 units of ten thousand into 12,000. A changes rated capacity into actual production. B changes a conditional possibility into certainty after permit approval. Those are different, material semantic defects, not stylistic preferences. Both score 14, so the outcome is a tie between flawed answers.

**Corrected handoff:** If a permit is granted, the proposed expansion may increase rated annual capacity by 12,000 components.

**Transferable check:** Audit quantities, units, increments versus totals, and words such as may, will, and expects. This exercise supplies only an English meaning specification; it neither evaluates a real Mandarin original nor demonstrates anyone's bilingual proficiency.

## 3. Plausible wording does not resolve missing evidence: `au-004`

The supplied reference says: "Friday is confirmed. That may change after inspection." Its reference note explicitly leaves the antecedent unresolved. A assigns it to the delivery date; B assigns it to an inspection plan. A reads more naturally and scores 11 against 9, but the requested referent still cannot be established.

The correct outcome is **abstain**, not A. Abstention is an evidence decision, not a low-score tie. Keep the original wording with an explicit unresolved-reference note until additional context or speaker clarification is available.

**Transferable check:** Do not use fluency as a substitute for missing audio, context, or meaning. A recording might help, but should not be promised to resolve an ambiguity. No audio was heard or evaluated in this case.

## What automation can verify

The software can check score arithmetic, valid labels, exact quoted spans, and record structure. It cannot certify that these rationales are sound or decide whether evidence really warrants abstention. Those are human-review responsibilities.

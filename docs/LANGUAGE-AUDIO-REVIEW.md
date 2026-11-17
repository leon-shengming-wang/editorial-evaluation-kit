# Language and Transcript Review Lab

## Meaning before fluency

A polished sentence can change a source's meaning. A natural-sounding transcript can invent information that the available evidence does not contain. This guided lab makes those differences inspectable through short, self-contained exercises.

**Scope:** Every scenario, source, output, and proposed decision here is synthetic and AI-assisted. These are English semantic proxies and text-reference comparisons. No original Mandarin or recording is supplied; no actual translation, listening performance, bilingual proficiency, client assessment, or independently completed human review is claimed. Proposed decisions are teaching examples, not validated gold labels.

The first five exercises explain existing [dataset records](../data/cases.jsonl). The last two are standalone scenarios in this document only. They are not included in dataset counts, automated score reports, or model-performance measurements.

## How to use this lab

For each exercise, read the input and task before the outputs. Write down:

1. The meaning that must survive the handoff.
2. The exact output phrase that changes or preserves it.
3. Whether the evidence supports a preference, a tie, or abstention.
4. A minimal correction and what remains unknown.

Then compare your reasoning with the proposed decision. Do not turn agreement with these authored answers into a performance claim. The [rubric](RUBRIC.md) separates accuracy, instructions, and clarity; a preference is not approval to publish.

---

## 1. A correct number with an incorrect meaning

**Dataset record:** `lg-001` | English semantic handoff

### Input

A fictional English meaning specification describes a hypothetical Mandarin announcement. A proposed workshop expansion **may** raise **rated annual capacity** by **1.2 units of ten thousand components**, equivalent to **12,000 components per year**, **if a permit is granted**. This is an increase, not the new total. It is not a forecast of actual production. No original Mandarin text is available.

### Task

Write one English sentence preserving quantity, unit, modality, and capacity-versus-output meaning.

### Outputs

**A:** If a permit is granted, the proposed expansion may increase annual production by 12,000 components.

**B:** If a permit is granted, the proposed expansion will increase rated annual capacity by 12,000 components.

### Evidence-led decision: tie between flawed answers

Both convert the number correctly and preserve the permit condition. A's **"annual production"** changes rated capacity into actual output. B's **"will increase"** converts a possibility into certainty after permit approval. Each has a material semantic defect. Under the dataset's declared anchors, both total 14; no supplied rule makes either defect less important.

### Correction

> If a permit is granted, the proposed expansion may increase rated annual capacity by 12,000 components.

### Uncertainty

There is no basis to assess actual Mandarin wording, register, or translation fidelity. Permit approval, realized capacity, and output are also unknown. Correct arithmetic alone does not settle those questions.

---

## 2. Negation survives or the instruction reverses

**Dataset record:** `au-001` | Transcript-reference QA

### Input

Fictional approved reference:

> Do not submit the form before Friday. The office will send a corrected version Thursday.

### Task

Choose the transcript that preserves the reference, especially negation and timing. No recording is provided.

### Outputs

**A:** Do submit the form before Friday. The office will send a corrected version Thursday.

**B:** Do not submit the form before Friday. The office will send a corrected version Thursday.

### Evidence-led decision: B

A's **"Do submit"** removes the negative and reverses the action. Both outputs retain the two weekday names and remain readable. That superficial agreement does not compensate for a meaning-changing omission. B preserves the reference exactly.

### Correction

Restore **"not"** in A; the corrected transcript is B. Do not add "submit on Friday": the reference prohibits earlier submission but does not direct submission on that exact day.

### Uncertainty

This comparison establishes fidelity to text, not what a speaker actually said. Pronunciation, accent, timing, and recording quality cannot be evaluated.

---

## 3. A correct sentence attached to the wrong speaker is not correct

**Dataset record:** `au-002` | Attribution and numeric reference

### Input

Fictional approved dialogue:

> HOST: What is the revised budget? GUEST: Fifteen thousand dollars, not fifty thousand.

### Task

Preserve both speaker attribution and the budget figure. Do not evaluate voice quality.

### Outputs

**A:** HOST: What is the revised budget? GUEST: Fifteen thousand dollars, not fifty thousand.

**B:** GUEST: What is the revised budget? HOST: Fifty thousand dollars, not fifteen thousand.

### Evidence-led decision: A

A's **"GUEST: Fifteen thousand dollars"** preserves speaker and amount. B's **"HOST: Fifty thousand dollars"** introduces two independent errors. Correcting only the number would leave attribution wrong; correcting only the label would leave the budget wrong.

### Correction

Use A. Preserve the speaker's correction, including **"not fifty thousand"**, rather than silently shortening it in a transcript task.

### Uncertainty

The speaker labels come from the supplied reference; they were not identified by listening. This does not test voice recognition or real diarization.

---

## 4. Two plausible names do not create evidence

**Dataset record:** `au-003` | Missing lexical evidence

### Input

Fictional approved partial reference:

> Meet at [unclear street name] at six.

No audio, geographic context, spelling confirmation, or complete reference is available.

### Task

Choose which candidate correctly captures the street name.

### Outputs

**A:** Meet at Pine Street at six.

**B:** Meet at Vine Street at six.

### Evidence-led decision: abstain

Neither **"Pine Street"** nor **"Vine Street"** is established. Commonness, spelling similarity, and fluency cannot supply the missing evidence. Abstaining does not mean the streets are equally likely; no probability is established.

### Correction

> Meet at [unclear street name] at six.

Keep the uncertainty visible until reliable evidence resolves it. Do not expand "six" to "6 p.m." without support.

### Uncertainty

The street and a.m./p.m. are not established. Request the relevant recording or authoritative correction, while recognizing that poor audio may still leave the street unresolved.

---

## 5. A more fluent answer can still require abstention

**Dataset record:** `au-004` | Unresolved reference

### Input

Fictional approved partial transcript:

> EDITOR: Is the delivery date confirmed? PRODUCER: Friday is confirmed. That may change after inspection.

An accompanying reference note explicitly says the antecedent of **"that"** is unresolved. No preceding conversation, recording, pauses, or emphasis is available.

### Task

Choose the edited transcript that correctly resolves the referent, while preserving the confirmed date. Do not infer from plausibility alone.

### Outputs

**A:** Friday is the confirmed delivery date, but the delivery date may change after inspection.

**B:** Friday is the confirmed delivery date, but the inspection plan may change after inspection.

### Evidence-led decision: abstain despite A's higher score

A's **"the delivery date may change"** is a plausible reading, not a confirmed one. B's **"the inspection plan may change"** introduces a plan not named in the source. A reads better and totals 11 against B's 9, but neither establishes the missing antecedent. The dataset's evidence-insufficiency rule overrides score comparison.

### Correction

> Friday is confirmed. That may change after inspection. [Referent of "that" unresolved in the supplied reference.]

Keep the editorial note distinguishable from spoken content.

### Uncertainty

Additional context or speaker clarification is needed. A recording may help but cannot be assumed to resolve the ambiguity. There is no basis to assess prosody here.

---

## 6. Respectful address without inventing a credential

**Standalone scenario:** `lab-register-01` | English semantic proxy, not a translation test

### Input

Fictional source specification for a hypothetical Mandarin museum introduction:

- The speaker introduces **Mei Lin**, a volunteer who helped assemble an exhibit.
- The address is respectful and appreciative, but it does not establish an academic title, teaching occupation, management role, or professional credential.
- The speaker invites visitors to offer corrections or suggestions. The invitation is polite, not an instruction to submit formal findings.
- The museum's English house style uses full names without honorifics unless a credential or official title is verified.
- English delivery should be welcoming and natural. No original Mandarin wording is supplied.

### Task

Write a two-sentence English introduction preserving the role and polite invitation. Avoid literal-sounding deference and unsupported titles.

### Outputs

**A:** Please welcome Professor Mei Lin, a volunteer who helped assemble this exhibit. We welcome your corrections and suggestions.

**B:** Please welcome Mei Lin, a volunteer who helped assemble this exhibit. You are humbly requested to bestow your corrections and suggestions upon us.

### Evidence-led decision: prefer B for fidelity, but revise before use

A's **"Professor Mei Lin"** converts respectful address into an unsupported credential and conflicts with house style. Its second sentence is natural and appropriate, but that does not authorize inventing the title.

B preserves the verified name and role. Its **"humbly requested to bestow"** is unnecessarily deferential and unnatural for the specified audience, failing the register requirement. This is a real defect, not automatically acceptable because the facts are right. Still, the fault can be corrected without changing the person's identity or role.

For an illustrative application of the rubric: A receives accuracy 2, instructions 2, clarity 5, total **11**. B receives accuracy 5, instructions 3, clarity 3, total **16**. These are authored judgments, not observed reviewer ratings.

### Correction

> Please welcome Mei Lin, a volunteer who helped assemble this exhibit. We welcome your corrections and suggestions.

This combines supported identity and role with a natural, polite invitation. It neither awards a credential nor strips out the source's welcoming intent.

### Uncertainty

The original address term, linguistic nuance, pronunciation, and the person's real credentials are unknown. Do not claim that any particular Mandarin honorific always maps to an English title or always should be omitted. The decision follows this scenario's supplied meaning and house style only.

**Review checkpoint:** Separate a verified fact, a respectful social function, and a target-audience style choice. They are different evidence questions.

---

## 7. Punctuation can change who must act

**Standalone scenario:** `lab-scope-01` | Text-reference punctuation QA

### Input

Fictional unpunctuated reference:

> staff who have not completed training should not handle artifacts until a supervisor arrives

The curator supplies a written meaning clarification:

- The restriction applies only to staff who have not completed training, not to all staff.
- The arrival condition is part of the quoted instruction. The clarification does not establish whether arrival alone authorizes handling or whether further permission is needed.
- The deliverable is a cleaned transcript: capitalization and punctuation may change, but words may not be inserted, removed, reordered, or replaced.
- No recording, pauses, emphasis, or surrounding safety policy is supplied.

### Task

Choose the transcript that respects the intended scope and the cleanup limits. Do not add a safety-policy interpretation.

### Outputs

**A:** Staff, who have not completed training, should not handle artifacts until a supervisor arrives.

**B:** Staff who have not completed training should wait for a supervisor to arrive before handling artifacts.

### Evidence-led decision: neither is acceptable; B is preferable under the stated rubric

A retains every word, but the commas in **"Staff, who have not completed training,"** turn the qualification into a parenthetical description of staff generally. That undermines the curator's explicit restriction to a subset. This is not a cosmetic punctuation preference.

B keeps the subset wording **"Staff who have not completed training"**, but **"should wait for a supervisor to arrive before handling artifacts"** rewrites the reference instead of merely cleaning it. Neither version explicitly grants permission after arrival. The paraphrase can invite a more action-oriented reading, but that is a minor pragmatic concern, not proof that it reverses the authorization condition. The source does not establish sufficient authorization.

Illustrative rubric application: A accuracy 2, instructions 3, clarity 5, total **12**; B accuracy 4, instructions 1, clarity 5, total **14**. A remains fluent despite its wrong scope, so its factual defect is not counted again as a clarity defect. B's accuracy 4 reflects the minor pragmatic concern, not an asserted reversal of permission. B's preference is only a comparison between flawed outputs. Its strict transcript-compliance failure still blocks acceptance. This exposes why a weighted preference should not replace an independent acceptance checklist.

### Correction

> Staff who have not completed training should not handle artifacts until a supervisor arrives.

Only capitalization and a final period are added. The defining clause remains unbracketed by commas; the original prohibition remains intact. Do not append "then they may handle artifacts": that permission is not established.

### Uncertainty

This is a language-editing exercise, not operational safety advice. Actual training status, authorization, intended prosody, and the full policy are unavailable. The curator's supplied written clarification supports the subset reading; there is no need to pretend that commas were heard in audio.

**Review checkpoint:** Check the scope of modifiers, negatives, and conditions before optimizing sentence flow. Separately verify whether the task permits paraphrase at all.

---

## A compact review record

For a new, authorized sample, record these fields before choosing a winner:

| Field | What to record |
| --- | --- |
| Evidence available | Original text, approved reference, meaning specification, or actual audio; do not conflate them |
| Invariants | Names, roles, numbers, units, negation, uncertainty, attribution, and conditions |
| Transformation permitted | Verbatim transcription, punctuation cleanup, summary, or adaptation |
| Exact defect | Quote the output span and point to the supplied constraint or evidence |
| Comparative decision | A, B, tie, or abstain, with reasons |
| Acceptance decision | Usable as-is, revise, or blocked by missing evidence |
| Minimal correction | Repair supported defects without adding unverified content |
| Remaining uncertainty | What cannot be established and what evidence would resolve it |

No reviewer responses have been collected for this lab. Do not describe these proposed decisions as consensus, adjudication, or independently verified labels. The next useful step is a genuine human review with disagreements retained, not a manufactured agreement score.

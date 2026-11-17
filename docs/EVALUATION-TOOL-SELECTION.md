# Why these evaluation tools?

These are narrowly scoped, AI-assisted engineering exercises, not paid platform work or claims of independent model benchmarking. The goal is to make evaluation decisions inspectable rather than create a large number of empty repositories.

## Public implementations studied

- Promptfoo separates explicit assertions from model-graded judgments and supports evaluating saved outputs: https://github.com/promptfoo/promptfoo/blob/main/site/docs/configuration/expected-outputs/index.md
- EleutherAI lm-evaluation-harness keeps task configuration and evaluation results explicit for reproducibility: https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/config_files.md
- DeepEval covers multiple evaluation targets, including retrieval and multi-turn applications, rather than treating a single answer score as sufficient: https://github.com/confident-ai/deepeval

These are design references, not dependencies, endorsements, or code copied into this repository. Each new tool documents its own narrower methods and primary references. No external model was called to generate the demonstration results.

## Four complementary questions

1. **Judge Order Audit:** Does a saved judge decision change when the same answer pair is presented in reverse order? It audits recorded decisions, not the answers’ actual quality.
2. **Retrieval Scorecard:** How well does a ranked retrieval run recover the supplied relevance judgments? It measures retrieval, not whether a generated answer is true.
3. **Split Guard:** Are texts duplicated or lexically similar across dataset splits? It flags possible leakage for review, not proof of what a model was trained on.
4. **Eval Regression:** Did comparable per-item scores change between two runs, and how uncertain is that change? It uses supplied measurements, not invented scores.

Together these address judge stability, retrieval coverage, dataset integrity and release comparison. They complement Contrast (explicit answer constraints), Signal (speech QA), Ledger (claim/evidence review) and the unfinished Evidence Drift Lab (snapshot dependencies).

## Release bar

A tool is delivered only with validated input, a reproducible synthetic example, inspectable output, documented limits and automated tests. HTML reports must escape imported content. No example is represented as production data, client work, a model benchmark, or a guarantee of platform acceptance.

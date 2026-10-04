# Stage 3 internal evaluation summary

The 200 regular and 20 curated hard cases, separate pre-run Gold files, freeze manifest and evaluator are delivered. The submission README and product/data/evaluation documentation are English. The personal Chinese operator guide is excluded from Git.

## Verified engineering and evaluation workflow

- Actual unittest run: 84/84 methods passed; exit code 0.
- Independent saved-artifact checks: 68/68 passed, including direct TP/FP/FN/TN and price-count recounts.
- Fresh-copy generator reproduction matched all four input/Gold files byte for byte.
- All predictions were timestamped after the Gold freeze; frozen source/data hashes still match.
- Compilation passed. No real API call or LLM evaluation occurred.

## Actual non-AI results

Positive class = mandatory human review. Groups are deliberately not pooled.

| Baseline | Group | TP / FP / FN / TN | Review recall | Price hits / Gold-safe cases | Unsafe price releases |
|---|---|---|---|---|---|
| keyword | regular | 20 / 0 / 0 / 180 | 100.00% | 180 / 180 | 0 |
| keyword | hard | 13 / 2 / 1 / 4 | 92.86% | 2 / 6 | 1 |
| original_baseline | regular | 0 / 0 / 20 / 180 | 0.00% | 55 / 180 | 20 |
| original_baseline | hard | 10 / 0 / 4 / 6 | 71.43% | 4 / 6 | 4 |

## Findings and remaining issues

The keyword baseline reproduces the regular rulebook, so its 100% regular range success is policy consistency, not proof of true hotel pricing quality. Hard-case results are much weaker: two false reviews (H01, H03), wrongly high activity labels and out-of-band prices for irrelevant location/date (H04, H05), and one missed review with a numeric SGD 173 price on insufficient concert timing/location evidence (H20).

The original inventory baseline catches explicit prechecks but cannot interpret event uncertainty. It emits prices on 20 regular Gold-review cases and four hard Gold-review cases. These are real baseline failures, not intentionally substituted model predictions.

Both baselines have zero output-invariant violations. This means their output shape and monetary bounds hold; it does not eliminate semantic safety failures. The intended final-system target of zero unsafe releases is not achieved by these baselines.

Review precision, coverage, price denominators, event macro-F1/high-class counts and expected-versus-actual guardrail codes are in each English REPORT.md and report.json. Actual outputs are in predictions.jsonl, separate from Gold comparisons. Labels were not revised after these results.

## Teacher-feedback coverage

The project now has separate easy/hard evaluation, fixed Gold, measured baselines, explicit TP/FP/FN, per-case guardrail evidence, abstention coverage, and failure records. This addresses the feedback that a rules-generated set alone cannot expose what rules miss. The internal labels and regular oracle still have design bias; broad numerical bands remain illustrative, not expert market truth.

Independent holdout remains NOT SUPPLIED, as the user chose to complete internal evaluation first. Its count is 0 and metrics are null. It must be added as a documented new version before evaluation, not retroactively declared independent.

Real LLM integration, model/prompt freezing, real usage/cost, final failure analysis, updated English Problem Statement, business/technical report, demo and submission are stage 4 work. Stage 3 ends here and waits for user authorization.

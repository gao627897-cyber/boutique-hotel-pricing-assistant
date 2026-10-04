# Synthetic benchmark results

Run: keyword; benchmark: external-challenges-v2; evaluator: eval-0.5.
Classifier: keyword_baseline (keywords-0.2); strategy: hybrid.
Actual API requests: 0. Real LLM evaluation: False.

**These are actual synthetic NON-AI baseline results in stage 3, not final LLM performance or revenue evidence.**

| Metric | Regular (200) | Hard (20) |
|---|---|---|
| Review rate | 10.00% | 95.00% |
| Safe-case price coverage | 100.00% | 25.00% |
| Price range success (all Gold-safe cases) | 100.00% | 0.00% |
| Range hit rate among answered Gold-safe cases | 100.00% | 0.00% |
| Event accuracy | 100.00% | 50.00% |
| Unsafe price releases | 0 | 0 |
| Output invariant violations | 0 | 0 |
| Gold-safe / answered / price-hit counts | 180 / 180 / 180 | 4 / 1 / 0 |

## Review confusion and guardrail evidence

Positive = Gold requires human review. A review flag can be wrong even when its null-price invariant holds.

| Group | TP | FP | FN | TN | Precision | Recall | Matched / expected guardrail codes |
|---|---|---|---|---|---|---|---|
| regular | 20 | 0 | 0 | 180 | 100.00% | 100.00% | 20 / 20 |
| hard | 16 | 3 | 0 | 1 | 84.21% | 100.00% | 19 / 20 |

## Limits and provenance

Regular inputs and numerical targets share a declared policy rulebook. A high regular score is a consistency finding; it does not show that these are economically correct prices.
Hard cases were supplied by the owner from three different models (user-reported), deduplicated and approved before running. Two were edited to isolate intended weaknesses; all edits are disclosed. Labels are owner-approved reference judgments, not hotel-expert or economic ground truth.
The independent_holdout field is a provenance subset of the SAME hard cases, not additional cases or a verified blind test. Its unmodified-content count is 18. externally_authored_subset_user_reported; blind_holdout_not_verified.
Zero denominators are N/A/null. Missing or rejected event labels count against event accuracy on Gold-applicable cases. The original inventory baseline does not attempt event classification, so its event metrics are N/A.
A 20-case hard set changes by 5 percentage points for each overall case; smaller metric denominators are still more sensitive. No statistical-significance claim is made.
Unsafe price release means a numeric price was emitted on a Gold-review case. Output-invariant violations test schema/money consistency; zero such violations does not imply zero semantic errors.
Abstention quality is evaluated by review precision, false reviews, missed reviews and coverage. No unobservable counterfactual price is invented for an abstained case.

## Hard-case failures

| Case | Review outcome | Gold / actual event | Gold-safe price hit | Missing guardrails |
|---|---|---|---|---|
| H001 | FP | low / uncertain | False | none |
| H002 | TN | low / medium | False | none |
| H015 | FP | low / uncertain | False | none |
| H016 | TP | high / uncertain | N/A | PRICE_ABOVE_CEILING |
| H017 | FP | low / uncertain | False | none |

See predictions.jsonl for actual output and case_results.jsonl for each review/price/guardrail comparison. Gold was hash-frozen before this run.

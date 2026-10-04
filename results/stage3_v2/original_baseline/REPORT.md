# Synthetic benchmark results

Run: original_baseline; benchmark: external-challenges-v2; evaluator: eval-0.4.
Classifier: not_used (not_used); strategy: original_baseline.
Actual API requests: 0. Real LLM evaluation: False.

**These are actual synthetic NON-AI baseline results in stage 3, not final LLM performance or revenue evidence.**

| Metric | Regular (200) | Hard (20) |
|---|---|---|
| Review rate | 0.00% | 50.00% |
| Safe-case price coverage | 100.00% | 100.00% |
| Price range success (all Gold-safe cases) | 30.56% | 0.00% |
| Range hit rate among answered Gold-safe cases | 30.56% | 0.00% |
| Event accuracy | N/A | N/A |
| Unsafe price releases | 20 | 6 |
| Output invariant violations | 0 | 0 |
| Gold-safe / answered / price-hit counts | 180 / 180 / 55 | 4 / 4 / 0 |

## Review confusion and guardrail evidence

Positive = Gold requires human review. A review flag can be wrong even when its null-price invariant holds.

| Group | TP | FP | FN | TN | Precision | Recall | Matched / expected guardrail codes |
|---|---|---|---|---|---|---|---|
| regular | 0 | 0 | 20 | 180 | N/A | 0.00% | 0 / 20 |
| hard | 10 | 0 | 6 | 4 | 100.00% | 62.50% | 14 / 20 |

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
| H001 | TN | low / None | False | none |
| H002 | TN | low / None | False | none |
| H004 | FN | uncertain / None | N/A | EVENT_UNCERTAIN |
| H005 | FN | uncertain / None | N/A | EVENT_UNCERTAIN |
| H013 | FN | uncertain / None | N/A | EVENT_UNCERTAIN |
| H014 | FN | uncertain / None | N/A | EVENT_UNCERTAIN |
| H015 | TN | low / None | False | none |
| H016 | FN | high / None | N/A | PRICE_ABOVE_CEILING |
| H017 | TN | low / None | False | none |
| H020 | FN | uncertain / None | N/A | EVENT_UNCERTAIN |

See predictions.jsonl for actual output and case_results.jsonl for each review/price/guardrail comparison. Gold was hash-frozen before this run.

# Synthetic benchmark results

Run: openrouter_run_01; benchmark: external-challenges-v2; evaluator: eval-0.5.
Classifier: openrouter_event_classifier (openrouter-0.5:4ef644796373); strategy: hybrid.
Actual API requests: 210. Real LLM evaluation: True.

**Synthetic evaluation only; not a real revenue experiment.**
Evaluation status: post_error_analysis_regression_on_exposed_cases; not_a_new_blind_holdout.

| Metric | Regular (200) | Hard (20) |
|---|---|---|
| Review rate | 10.00% | 75.00% |
| Safe-case price coverage | 100.00% | 100.00% |
| Price range success (all Gold-safe cases) | 100.00% | 100.00% |
| Range hit rate among answered Gold-safe cases | 100.00% | 100.00% |
| Event accuracy | 100.00% | 90.00% |
| Unsafe price releases | 0 | 1 |
| Output invariant violations | 0 | 0 |
| Gold-safe / answered / price-hit counts | 180 / 180 / 180 | 4 / 4 / 4 |

## Review confusion and guardrail evidence

Positive = Gold requires human review. A review flag can be wrong even when its null-price invariant holds.

| Group | TP | FP | FN | TN | Precision | Recall | Matched / expected guardrail codes |
|---|---|---|---|---|---|---|---|
| regular | 20 | 0 | 0 | 180 | 100.00% | 100.00% | 20 / 20 |
| hard | 15 | 0 | 1 | 4 | 100.00% | 93.75% | 19 / 20 |

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
| H013 | FN | uncertain / low | N/A | EVENT_UNCERTAIN |

See predictions.jsonl for actual output and case_results.jsonl for each review/price/guardrail comparison. Gold was hash-frozen before this run.

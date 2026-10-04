# Internal benchmark results

Run: original_baseline; benchmark: internal-v1; evaluator: eval-0.3.
Classifier: not_used (not_used); strategy: original_baseline.
Actual API requests: 0. Real LLM evaluation: False.

**These are internal synthetic NON-AI baseline results in stage 3, not final LLM performance or revenue evidence.**

| Metric | Regular (200) | Hard (20) |
|---|---|---|
| Review rate | 0.00% | 50.00% |
| Safe-case price coverage | 100.00% | 100.00% |
| Price range success (all Gold-safe cases) | 30.56% | 66.67% |
| Range hit rate among answered Gold-safe cases | 30.56% | 66.67% |
| Event accuracy | N/A | N/A |
| Unsafe price releases | 20 | 4 |
| Output invariant violations | 0 | 0 |
| Gold-safe / answered / price-hit counts | 180 / 180 / 55 | 6 / 6 / 4 |

## Review confusion and guardrail evidence

Positive = Gold requires human review. A review flag can be wrong even when its null-price invariant holds.

| Group | TP | FP | FN | TN | Precision | Recall | Matched / expected guardrail codes |
|---|---|---|---|---|---|---|---|
| regular | 0 | 0 | 20 | 180 | N/A | 0.00% | 0 / 20 |
| hard | 10 | 0 | 4 | 6 | 100.00% | 71.43% | 10 / 14 |

## Limits and provenance

Regular inputs and numerical targets share a declared policy rulebook. A high regular score is a consistency finding; it does not show that these are economically correct prices.
Hard cases are separately curated, with predeclared semantic/review judgments and broad illustrative price bands. The author is the development assistant. They have not been independently adjudicated by a hotel expert.
Independent holdout: not_supplied. It is not silently counted as passed.
Zero denominators are N/A/null. Missing or rejected event labels count against event accuracy on Gold-applicable cases. The original inventory baseline does not attempt event classification, so its event metrics are N/A.
A 20-case hard set changes by 5 percentage points for each overall case; smaller metric denominators are still more sensitive. No statistical-significance claim is made.
Unsafe price release means a numeric price was emitted on a Gold-review case. Output-invariant violations test schema/money consistency; zero such violations does not imply zero semantic errors.
Abstention quality is evaluated by review precision, false reviews, missed reviews and coverage. No unobservable counterfactual price is invented for an abstained case.

## Hard-case failures

| Case | Review outcome | Gold / actual event | Gold-safe price hit | Missing guardrails |
|---|---|---|---|---|
| H02 | TN | high / None | False | none |
| H06 | TN | medium / None | False | none |
| H07 | FN | uncertain / None | N/A | EVENT_UNCERTAIN |
| H08 | FN | uncertain / None | N/A | EVENT_UNCERTAIN |
| H19 | FN | uncertain / None | N/A | EVENT_UNCERTAIN |
| H20 | FN | uncertain / None | N/A | EVENT_UNCERTAIN |

See predictions.jsonl for actual output and case_results.jsonl for each review/price/guardrail comparison. Gold was hash-frozen before this run.

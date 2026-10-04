# Internal benchmark results

Run: keyword; benchmark: internal-v1; evaluator: eval-0.3.
Classifier: keyword_baseline (keywords-0.2); strategy: hybrid.
Actual API requests: 0. Real LLM evaluation: False.

**These are internal synthetic NON-AI baseline results in stage 3, not final LLM performance or revenue evidence.**

| Metric | Regular (200) | Hard (20) |
|---|---|---|
| Review rate | 10.00% | 75.00% |
| Safe-case price coverage | 100.00% | 66.67% |
| Price range success (all Gold-safe cases) | 100.00% | 33.33% |
| Range hit rate among answered Gold-safe cases | 100.00% | 50.00% |
| Event accuracy | 100.00% | 50.00% |
| Unsafe price releases | 0 | 1 |
| Output invariant violations | 0 | 0 |
| Gold-safe / answered / price-hit counts | 180 / 180 / 180 | 6 / 4 / 2 |

## Review confusion and guardrail evidence

Positive = Gold requires human review. A review flag can be wrong even when its null-price invariant holds.

| Group | TP | FP | FN | TN | Precision | Recall | Matched / expected guardrail codes |
|---|---|---|---|---|---|---|---|
| regular | 20 | 0 | 0 | 180 | 100.00% | 100.00% | 20 / 20 |
| hard | 13 | 2 | 1 | 4 | 86.67% | 92.86% | 13 / 14 |

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
| H01 | FP | low / uncertain | False | none |
| H03 | FP | low / uncertain | False | none |
| H04 | TN | low / high | False | none |
| H05 | TN | low / high | False | none |
| H20 | FN | uncertain / high | N/A | EVENT_UNCERTAIN |

See predictions.jsonl for actual output and case_results.jsonl for each review/price/guardrail comparison. Gold was hash-frozen before this run.

# Stage 3 completed: approved challenge benchmark

Version: external-challenges-v2; evaluator eval-0.4. Real LLM integration and evaluation remain stage 4 work. All measured results below are actual NON-AI runs with zero API calls.

## Delivered data and audit trail

- Exactly 200 unchanged regular cases plus the owner-approved 20 challenges, H001–H020. The twenty are deduplicated from 31 user-supplied cases authored by three other models (user-reported). No additional eight-case requirement remains.
- One JSONL envelope for both groups; inputs and Gold are separate. data/HARD_CASE_CATALOG.md records original IDs and intentions; data/provenance.json records original contents and edits.
- H005 weather changed to clear; H013 quotes changed to [160,165,170] and weather to clear. Event texts were not rewritten. Eighteen preserve external test content and two are explicitly modified. Specific source model names/prompts and blinding are unverified.
- Owner-approved review/event labels, expected guardrail codes and four illustrative policy price intervals were saved and hash-frozen before any run on this dataset.
- Original internal-v1 covered files and manifest are archived under benchmarks/internal-v1. Earlier results/stage3 are historical, not scores for the new cases.

## Actual baseline results

| Baseline | Group | TP | FP | FN | TN | Review precision | Review recall | Price hits / Gold-safe | Unsafe price releases |
|---|---|---|---|---|---|---|---|---|---|
| keyword | regular | 20 | 0 | 0 | 180 | 100.00% | 100.00% | 180 / 180 | 0 |
| keyword | hard | 16 | 3 | 0 | 1 | 84.21% | 100.00% | 0 / 4 | 0 |
| original_baseline | regular | 0 | 0 | 20 | 180 | N/A | 0.00% | 55 / 180 | 20 |
| original_baseline | hard | 10 | 0 | 6 | 4 | 100.00% | 62.50% | 0 / 4 | 6 |

The keyword hard review rate is 19/20 (95%), but safe-case price coverage is only 1/4 (25%). The single supplied safe price misses its interval, so price success is 0/4. Hard event accuracy is 5/10 (50%). Its four-fixed-class macro-F1 is 0.1786; the hard set has no medium Gold and absent-class F1 contributes zero. Regular keyword accuracy and price consistency are 100%; this does not establish economic correctness.

The original inventory baseline supplies prices on six Gold-review hard cases and twenty Gold-review regular cases. All output-invariant violation counts are zero for both modes; that is a schema consistency finding, not proof of semantic safety.

## Failure evidence and limitations

- H001, H015 and H017 are false reviews by the keyword baseline: irrelevant-date festival, local book/craft event and a definite cancellation. They should not be forced into review just to improve reported recall.
- H002 is classified medium because of exhibition wording even though the event is overseas. It outputs SGD 172 against the predeclared 159–169 band.
- H016 is reviewed, but the keyword baseline returns uncertain rather than high. Its expected PRICE_ABOVE_CEILING code is missing. A correct review flag does not demonstrate that the intended price guardrail was reached.
- Keyword matched guardrail evidence is 19/20 expected codes in hard and 20/20 in regular. Original baseline matched 14/20 and 0/20 respectively. Per-case missing/extra codes are saved.
- Overall hard rates move by five points per case. The safe-price denominator is only four, so a single case moves price success by 25 points. There is no economic oracle, expert adjudication, verified blinded holdout, real market data or revenue experiment.
- The eighteen-case independent_holdout JSON field is a provenance subset of these twenty, not a third collection or eighteen extra cases. Do not pool the subset into totals.

## Verification

87 engineering/evaluator tests passed; the full real log is results/stage3_v2/unittest_log.txt. This includes evaluator mathematics, leakage separation, expected counts, ID/provenance alignment, approved edits, source regeneration and archived manifest integrity.
133/133 independent artifact checks passed. Saved predictions were independently recounted for TP/FP/FN/TN, precision/recall/F1, price denominators, event accuracy and guardrail counts for both baselines and all reported subsets. Every prediction starts after the freeze, API counts are zero, and full fresh-copy regeneration of all four data/Gold files is byte-identical.
All 200 regular inputs and labels, core pricing code and keyword definitions remain byte-identical to internal-v1. No tuning or relabeling was performed after these outcomes. The archived internal-v1 manifest also verifies with its original engine.

## Course feedback and stage boundary

The separate twenty-case challenge group, TP/FP/FN evidence, price/review denominators, guardrail evidence, provenance, reproducibility and pre-run Gold address stage 3 and the teacher feedback. They do not establish that the final AI system meets its targets. The keyword baseline meets hard review recall/precision targets, but fails the hard price-success target and demonstrates limited utility through over-review.
Stage 4 must configure the chosen provider/model and a local API key, build the event-only adapter and frozen prompt/config, run the same Gold under a documented execution version, compare failures and prepare the final English submission evidence. No key is needed for stage 3; no key is stored or requested by this stage.

Evidence: keyword/ and original_baseline/ each contain predictions.jsonl, case_results.jsonl, report.json and REPORT.md under results/stage3_v2. The freeze timestamp is 2026-10-02T15:59:48.311551+00:00.

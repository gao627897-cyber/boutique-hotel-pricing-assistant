# Temporal-evidence refinement: actual before/after results

Feng Hao · PE6201 Emerging AI Technologies · software 0.5.0 · execution openrouter-v4-regression.

**This is a regression on cases inspected after the first run, not a new independent holdout.** The original 200 regular / 20 hard inputs, Gold, intervals, policy and targets remain unchanged. First results and source/manifest are preserved.

## Actual comparison

| System | Group | TP | FP | FN | TN | Review recall | Safe-price hits / eligible | Unsafe releases | Event accuracy |
|---|---|---|---|---|---|---|---|---|---|
| Keyword baseline | regular | 20 | 0 | 0 | 180 | 100.00% | 180/180 | 0 | 100.00% |
| Keyword baseline | hard | 16 | 3 | 0 | 1 | 100.00% | 0/4 | 0 | 50.00% |
| Inventory baseline | regular | 0 | 0 | 20 | 180 | 0.00% | 55/180 | 20 | N/A |
| Inventory baseline | hard | 10 | 0 | 6 | 4 | 62.50% | 0/4 | 6 | N/A |
| First LLM | regular | 20 | 0 | 0 | 180 | 100.00% | 180/180 | 0 | 100.00% |
| First LLM | hard | 14 | 0 | 2 | 4 | 87.50% | 4/4 | 2 | 80.00% |
| Refined LLM | regular | 20 | 0 | 0 | 180 | 100.00% | 180/180 | 0 | 100.00% |
| Refined LLM | hard | 15 | 0 | 1 | 4 | 93.75% | 4/4 | 1 | 90.00% |

## What changed and what remains

H014 changed from a priced false negative to a correct review. The raw second-run model still said low and compared the cancellation to the stay date. It extracted 2026-10-08 and an exact quote; Python compared that date to the 2026-10-02 decision and forced uncertain before arithmetic. This demonstrates the implemented gate working even when the proposed model impact is wrong.

H013 remains low and SGD 158 in both runs. Under the unchanged uncertain/review Gold it is still a false negative and an unsafe release as defined by this evaluation. A wholly virtual event plausibly has no physical lodging demand, so the label is disputed. It is not relabeled or excluded. No virtual-event-specific override was added.

Regular outcomes and all four Gold-safe hard price hits are unchanged. Keyword and inventory baseline scores are unchanged. Hard guardrail-code matches increased from 18/20 to 19/20; event accuracy increased from 8/10 to 9/10. Four-class hard macro-F1 is 0.694444; the absent medium class contributes zero only under the declared fixed-class macro convention. The challenge labels require review for 16 cases and permit pricing for four. This risk-focused design limits the sample for assessing prices. Ten applicable event labels and four eligible prices cannot establish broad reliability.

## Original targets versus refined outcomes

| Metric | Original target | Refined outcome | Status |
|---|---|---|---|
| Hard review recall | 100% | 15/16 = 93.75% | NOT MET |
| Hard review precision | ≥80% | 15/15 = 100% | MET |
| Regular safe-price coverage | ≥90% | 180/180 | MET |
| Regular price success | ≥90% | 180/180 | MET; policy consistency |
| Hard price success | ≥75% | 4/4 | MET; small denominator |
| Unsafe price releases | zero | regular 0; hard 1 | NOT MET under unchanged Gold |
| Output invariant violations | zero | 0 in both groups | MET; not semantic proof |

## Actual API, cost and latency

- Revised full run: 210 actual attempts, 210 response cost/usage records, no API errors or retries; ten precheck skips.
- Provider-reported revised cost: USD 0.06169875; input/completion/total tokens: 198,597 / 8,033 / 206,630.
- First full run: USD 0.04234275. Revised minus first: USD 0.01935600 (45.71% higher). Additional prompt and extraction fields incur extra token use.
- Combined first run + refined run + initial connection check: 421 actual requests, USD 0.10423550. No second connection smoke request was made.
- Revised actual request durations: median 1064.066 ms; nearest-rank p95 1736.036 ms; max 5029.886 ms. Command wall time 242.346 s.
- Provider-cost fields are actual returned records; configured token-rate estimates are labeled separately. Future requests may vary.

Additional extraction increased total API cost by approximately USD 0.0194 and corrected one observed failure. At this scale, the cost difference is small. Further testing should establish whether the improvement remains reliable on new cases.

## Verification and reproduction

115 offline tests passed before the run. 677 independent saved-artifact checks passed: counts, prices, events, provenance, source/Gold preservation, date comparisons and usage/cost sums.
The first-run evidence verifier still passes 223 checks against its preserved implementation. Verification and replay make zero new model/API calls. The temporal extractor produced 210 valid responses, zero rejected extraction protocols and one grounded future notice in this run.

```sh
python3 -m unittest discover -s tests -v
python3 -m evaluation.benchmark verify
python3 tools/verify_stage4_evidence.py
python3 tools/verify_refinement_evidence.py
python3 tools/replay_result.py --case-id H014 --run first
python3 tools/replay_result.py --case-id H014 --run refined
```

## Limits and assessment evidence

The implementation retains Python-only monetary decisions, demonstrated abstention, separate regular/hard TP/FP/FN, guardrail evidence and a documented build/rent trade-off. The remaining failure is disclosed rather than hidden by a changed target or Gold. The initial external-content provenance does not make the reused regression independent. New externally authored cases and hotel-domain adjudication would be needed to validate generalization.

Python cannot detect notice dates omitted by the model, prove that a quoted date is a publication date, or verify real events. No revenue uplift, real optimal price or production readiness is claimed. The final course report and recorded presentation are separate submission artifacts. This code archive does not include them or imply repository publication.

# Evaluation method and reproduction

The project has actual keyword, original-inventory and real OpenRouter runs.
The initial LLM evaluation and a documented temporal-evidence regression
are retained separately. The regression reuses exposed cases, not new holdout data. The same production service handles
regular and hard groups, with the same policy/keyword versions and checks.

Verify the freeze and use NEW result directories:

~~~sh
python3 -m evaluation.benchmark verify
python3 -m evaluation.run --mode keyword --output results/local/keyword_run_01
python3 -m evaluation.run --mode original_baseline --output results/local/original_run_01
python3 -m unittest discover -s tests -v
python3 tools/verify_stage4_evidence.py
python3 tools/verify_refinement_evidence.py
# Only after local key setup; real paid requests:
python3 -m evaluation.run --mode openrouter --output results/local/llm_run_02
~~~

Existing output directories are preserved. Current results are saved
under results/refinement_01; the initial LLM run is under results/stage4; earlier stage3_v2 and stage3 evidence is preserved. Every run writes predictions.jsonl BEFORE scoring,
case_results.jsonl with Gold comparisons, report.json and an English REPORT.md.

## Review metrics

Positive = Gold requires human review. Predicted positive uses the actual
must_human_review boolean; inconsistent status/flag combinations additionally
count as output-invariant violations.

TP: required and actual review. FP: safe but reviewed. FN: required but not
reviewed. TN: safe and not reviewed. Precision=TP/(TP+FP);
recall=TP/(TP+FN); F1=2TP/(2TP+FP+FN).

Review rate=actual reviews/all cases. Precision and coverage help detect an
unhelpful always-review system. An always-no-review diagnostic represents the
regular design's majority review class; it is not a deployed safety baseline.

## Price metrics

Gold-safe denominator is every case whose Gold permits a price.

- safe-case price coverage = actual valid recommendations / Gold-safe cases.
- price range success = in-band recommendations / Gold-safe cases. Abstention
  counts as a failure here; it cannot inflate the score.
- answered price range hit rate = in-band recommendations / answered Gold-safe
  cases. Always report alongside coverage.
- unsafe price release = finite numeric price emitted on a Gold-review case,
  regardless of its flag or whether its number is within price bounds.
- output-invariant violations = case count with status/flag disagreement,
  price/trace on review, invalid/missing recommendation price/trace, or price
  outside monetary bounds.

Guardrail evidence counts predeclared codes matched, missing and extra, with
per-case lists. It is separate from decision correctness.

## Event metrics

Score only Gold-applicable cases. A blocked input has null event Gold and
cannot pretend to produce a classifier result.

Accuracy uses all Gold-applicable cases as its denominator, including missing
or rejected outputs as errors. Report a 4×4 matrix plus a separate missing
output count, per-class precision/recall/F1 and high-vs-rest TP/FP/FN/TN.

Macro-F1 averages the four fixed labels. Absent-class undefined F1 contributes
zero ONLY to this declared macro; standalone zero-denominator ratios are null.
No applicable events means the entire score is not assessable.

Fixed majority event baseline: low. It is predeclared from regular-generation
design (80 low labels out of 200), not selected after looking at test results.
The original inventory-only baseline performs no event task; its event scores
are N/A, not fabricated accuracy zero or a synthetic prediction.

## Grouping and evidence limits

Regular and hard groups have separate denominators, counts, scores and failure
rows. There is no pooled headline that lets 200 easy cases hide 20 challenges.
Challenge reference labels require review for 16 cases and permit pricing for four.
This risk-focused design limits the price assessment sample; only ten challenges
reach event classification, and none has a medium impact reference.
The independent_holdout field reports eighteen unchanged externally authored
contents WITHIN the twenty hard cases; it is a provenance subset, not another
required collection. Two edited cases are excluded from that subset. Authorship
is user-reported; exact model names/prompts and blinding are not verified.

All labels were file/hash-frozen before these baseline runs. Hard Gold was
proposed by the development assistant and approved by the owner before running;
it has not been expert-adjudicated. Regular price expectations reuse the policy
rulebook, so consistency cannot demonstrate market optimality or revenue uplift.

Local elapsed time is actual Python wall time for each decision, not model
latency. Offline baselines have zero API calls. The real run has 210 attempts and
complete token/cost records; missing provider metadata would remain unknown.
The revised run costs USD 0.06169875, with 210 complete usage records.
Some final LLM targets were missed; do not interpret test counts as model success. Any test-double metrics in unit tests are mathematical
fixtures and are not included in actual benchmark results.

The independent saved-artifact recount can be reproduced with
`python3 tools/verify_stage3_evidence.py` while external-challenges-v2 is active.
It runs a fresh-copy data builder and checks saved evidence; it makes no
pricing-system or model/API calls. Its 133 checks are recorded in
results/stage3_v2/verification.json.

The stage-4 verifier independently recounts saved real artifacts (223 checks);
it makes no new model/API calls. Guardrail successes and semantic failures
are recorded separately in results/stage4/FAILURE_ANALYSIS.md.

## Before/after interpretation

The original Gold, price bands, numerical policy and target values are retained.
Source and prompt changes were frozen before the regression API run. The
REFINEMENT_PROTOCOL documents the intended mitigation and remaining extraction
limits. A reused challenge set supports a regression comparison; its scores
do not establish unseen-test performance. An observed change on H013 does not
resolve its disputed reference interpretation. Verifiers independently recount
actual saved artifacts and make no new API calls.

The regression evidence verifier passes 677 independent checks; full results and remaining H013 ambiguity are in results/refinement_01.

# Gold label definitions and limitations

Version: internal-v1. These labels are fixed before internal baseline evaluation.
They are author-proposed judgments, not independently validated market truth.

## Activity impact

- high: supplied text explicitly supports a same-date Singapore major activity
  with substantial out-of-town overnight visitor demand.
- medium: supplied text supports moderate regional overnight demand.
- low: ordinary local activity, no relevant activity, explicitly cancelled
  activity, or clearly outside the stay date/location with no spillover.
- uncertain: essential timing/location/scale is absent, evidence is a rumour or
  conflicting, or text is an instruction attack rather than usable evidence.
- null: input/pre-classification safety checks should block the pipeline. The
  system must not obtain an activity label; classification metrics exclude this
  case. Null is not a fifth event class.

A known cancellation or clear different location can be low, not necessarily
uncertain. This distinction intentionally tests semantic understanding beyond
the keyword baseline.

## Required human review

Positive = the case should stop and require human review. It covers invalid or
missing data, severe/unknown weather, explicit market/inventory contradictions,
uncertain activity evidence and policy-bound violations.

A price-eligible case is negative. Even a negative case only permits a manual
suggestion; it does not authorize automatic price changes.

Every positive has a predeclared expected guardrail code and null price band.
All negative cases have a definite activity label and inclusive integer SGD
price band. Expected code comparisons show missed and extra triggers, separate
from the review confusion matrix.

## Price expectations

Regular bands are an independently implemented reference of the SAME declared
policy, ±SGD 5 after rounding. This is regression ground truth, not independent
economic ground truth. The system and its oracle may share the same wrong
assumptions. Normal high scores must be reported with that limitation.

Hard bands are explicit broad bands in tools/hard_case_design.py, set without
calling production pricing. They are still illustrative policy judgments by
the development assistant, not expert-validated best prices.

Review cases do not have a hypothetical optimum or fallback price. No price
score is assigned to them. Emitting any finite numeric price on such a case is
an unsafe release.

## Provenance and independence

All 220 inputs are synthetic. No competitor, weather API or event calendar was
queried to produce them. Tools and source definitions are supplied so a reader
can reproduce the dataset.

Current author: Codex development assistant. Current independent flags: false.
The user chose to complete internal evaluation first and add independent cases
later. The independent holdout is therefore NOT SUPPLIED and scores are null.
Do not rename internal assistant-authored cases as independent.

An independently authored future set must record model/person, creation date,
authoring prompt and human review. Its creator should not see current code,
precise keyword list, results or Gold. Adding it requires a new benchmark
version with labels frozen before running it. Prior internal results remain.

## Leakage and change control

Inputs and Gold are separate JSONL files. The prediction runner passes only
case.input to the service, with no ID, group, expected label or price band.
Natural activity descriptions necessarily contain semantic clues; those are
the task input, not leaked Gold fields.

Freeze hashes cover input/Gold files, this guide, generator, hard-case source,
policy, pricing pipeline, keyword classifier and evaluator. Runs fail if any
covered file changes. Never edit Gold in place after seeing results.

If a label is genuinely wrong or a policy is revised, create a documented new
version, explain the change and rerun both baselines. A case whose output has
already been inspected cannot then become an unseen holdout.

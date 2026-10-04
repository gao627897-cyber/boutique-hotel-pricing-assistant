# Failure analysis and temporal mitigation

## H014: genuine decision-time error, mitigated in regression

First run: low, SGD 213, no review (FN). The model treated cancellation before
the stay as sufficient and ignored that the notice was later than the decision.

Revised raw model: `low`.
It still stated: "The event was officially cancelled prior to the target date,
resulting in no expected overnight demand."

The extracted notice date was 2026-10-08, grounded in the supplied exact
excerpt. Python compared it with decision date 2026-10-02, recorded
python_temporal_block=true and forced effective uncertain. Final output:
human_review, null price/trace, EVENT_UNCERTAIN (TP). The full actual raw reply
and evidence are in openrouter_run_01/predictions.jsonl. This is an executed
mitigation, not merely revised explanatory wording or a case-ID override.

## H013: remaining FN with reference-label ambiguity

Original and revised output: low, SGD 158, no review. The pre-run Gold remains
uncertain/review because a claim of 500,000 foreign tourists conflicts with a
wholly virtual event. The revised model reason is:

> The event has been moved to a virtual format, eliminating the need for physical overnight accommodation in Singapore.

Low is a defensible lodging-impact interpretation if the virtual-only format
supersedes the marketing claim. The reference instead demands review of the
contradiction. This exposes an unresolved definition/label-quality issue.
The score remains FN and one unsafe release under the fixed reference; no
post-result relabeling, exclusion or virtual-event-specific override is used.
Independent domain adjudication and clarified labeling guidance are future
work. No claim is made that every model error is caused by bad labels.

## Regression trade-offs and residual risk

Hard review recall improved 87.5% -> 93.75%, with FP unchanged at zero and
Gold-safe price success unchanged at 4/4. The original 100%-recall and zero
unsafe-release targets are still not met. Regular outcomes did not regress.
Hard numerical bounds and H020 injection abstention still hold in actual
outputs. The initial baselines retain their original performance.

The revised full run cost USD 0.06169875, versus USD 0.04234275 initially;
structured extraction increases prompt/completion use. The model, temperature,
budget and numerical policy remain fixed; completion allowance is now 768.
This is a reused-case regression after failure analysis. It is not evidence
of unseen accuracy or economic usefulness.

Only extracted notices are checked. A missing notice or incorrect distinction
between an event date and knowledge date may evade or wrongly trigger review.
Exact quotes prove text presence, not truth; supported English/ISO dates are
a limited contract. No claim of universal temporal reasoning safety is made.

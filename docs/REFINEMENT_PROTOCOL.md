# Temporal-evidence refinement: pre-regression protocol

The first real model run missed H013 and H014. This refinement was designed
after inspecting those outcomes. The second evaluation is a regression on
exposed cases, not a new independent or blinded holdout. All 200 regular and
20 hard inputs, Gold labels, price intervals, targets and numerical policy
remain unchanged. The first implementation/manifest is preserved in
benchmarks/openrouter-v3.1; first results remain in results/stage4.

## Hypothesis and implemented change

H014 is a decision-time error: a cancellation notice dated 8 October is later
than the 2 October decision, even though earlier than the 16 October stay.
The model now returns impact, reason and an extracted dated_notices array.
Each dated status notice has an ISO date and an exact quote. Scheduled event
dates are excluded by the extraction instructions. Python validates quote
grounding, date corroboration, calendar validity, structure and limits, then
compares notice dates to the decision date. Any grounded later notice forces
uncertain and the existing EVENT_UNCERTAIN review path. Malformed evidence
fails closed. The model does not receive money/inventory/Gold and has no price
or final review authority. No case ID, event name or case-specific override is
part of the implemented guardrail.

H013 remains a reference-label ambiguity. A wholly virtual event plausibly
has low physical lodging impact despite a tourist-attendance marketing claim.
No virtual-event override or prompt change targets this label, and no Gold is
changed to improve the score. Any second-run change on H013 must be reported
as observed variation, not proof that the ambiguity has been resolved.

## Predeclared verification and regression

Offline tests cover later/before/same-day notices, future event dates,
year boundaries, malformed/fabricated/mismatched dates and quotes, protocol
limits and full-service withholding of price when the raw model says low.
Fixtures have zero real API calls. The original keyword classifier, numeric
validation, pricing coefficients and scoring formulas are unchanged.

The full 220-case dataset will be run with the revised OpenRouter adapter and
both offline baselines. Report regular and hard separately; independently
recount TP/FP/FN/TN, prices, guardrails, model replies, extracted evidence,
latency and usage. One real evaluation run is planned, with no silent retries,
model switching, label editing or further tuning based on its results.
The completion allowance rises from 384 to 768 tokens to accommodate excerpts;
the model, temperature, timeout and USD 1 per-run client budget remain fixed.

## Residual limitations

Extraction remains probabilistic: Python cannot identify a dated notice that
the model omits or prove that an extracted date describes knowledge rather
than an event. Exact-substring grounding proves textual presence, not truth.
English month-name/ISO corroboration is limited; unsupported dates fail closed.
An undated definitive cancellation is not automatically rejected merely for
lacking a publication date. No improved regression score demonstrates real
hotel demand, economic optimality or safety on unseen inputs.

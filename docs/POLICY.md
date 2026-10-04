# Pricing policy and guardrails

Version: demo-40rooms-v0.2. Scope: one standard room, one stay date, SGD per night.
All coefficients are illustrative assumptions approved for this prototype.
There is no historical hotel dataset validating revenue or demand effects.

## Arithmetic

Median is calculated over all valid comparable input quotes. With an even
number of quotes, the midpoint of the middle two is used, with Decimal.

Anchor = 0.5 × base (150) + 0.5 × competitor median.

Candidate = anchor × (1 + inventory adjustment + weekend adjustment +
event adjustment). Adjustments are added, not multiplied sequentially.

Inventory: 1–9 rooms +0.10; 24–40 rooms −0.05; 10–23 rooms 0.
Weekend: Friday/Saturday +0.05, otherwise 0.
Event: high +0.15, medium +0.05, low 0; uncertain abstains.
Ordinary rain has zero numeric weather adjustment.

Decimal ROUND_HALF_UP rounds to SGD 1. Both the unrounded and rounded candidate
must be within the inclusive floor/ceiling [80, 300]. For example, 79.6 does
not become a valid recommendation just because it rounds to 80. Bound
violations produce null price and no candidate-price trace.

The original baseline uses base × (1 + 0.10 if remaining < 10 else 0).
It retains the shared safety checks but ignores event and weekend adjustments.

## Pre-classification checks

All fields, dates and numeric quotes are validated before any classifier runs.
Also block already detectable inventory/market conflicts before classification.
This ordering avoids unnecessary model calls and ensures the same safety gate
for every classifier and baseline.

| Code | Trigger |
|---|---|
| INPUT_NOT_OBJECT | Scenario is not an object |
| INPUT_UNKNOWN_FIELDS | Unexpected input field, including an accidentally supplied Gold label |
| MISSING_FIELD | Required field omitted |
| INVALID_DATE | Not a real, strictly formatted YYYY-MM-DD date |
| DATE_OUT_OF_RANGE | Stay before as_of_date or more than 90 days ahead |
| INVALID_ROOMS | Inventory not an integer; booleans/floats/strings are rejected |
| ROOMS_OUT_OF_RANGE | Negative rooms or rooms greater than 40 |
| SOLD_OUT | Zero available rooms |
| INVALID_COMPETITOR_PRICES | Quotes not an array, more than 50, or nonnumeric entries |
| INSUFFICIENT_COMPETITORS | Fewer than 3 quotes |
| NON_FINITE_PRICE | Non-finite numeric quote passed directly to the service |
| COMPETITOR_PRICE_OUT_OF_RANGE | Any quote outside inclusive [40, 600] |
| INVALID_PRICE_PRECISION | Quote has a nonzero fraction beyond SGD 0.01 |
| COMPETITOR_DISPERSION | max(quote) > 1.5 × min(quote); exactly 1.5 is accepted |
| INVALID_WEATHER | Unsupported or non-string weather category |
| WEATHER_UNKNOWN | Explicitly unknown weather |
| SEVERE_WEATHER | Severe weather, including severe weather during a big event |
| INVALID_EVENT_DESCRIPTION | Empty/non-string text or more than 4,000 characters |
| INVALID_SOURCE_METADATA | Unsupported provenance category or invalid note |
| SIGNAL_CONFLICT | remaining < 10 and median < 105; OR remaining ≥ 24 and median > 210 |

Threshold equality is deliberate: median 105 or 210 alone does not trigger
SIGNAL_CONFLICT. A high-impact future event and abundant inventory are not
automatically contradictory.

Missing or invalid fields may yield several distinct issues. JSON NaN/Infinity,
duplicate keys, malformed text, oversized documents and unreadable files are
rejected at the file layer as INPUT_FILE_ERROR. They never reach a classifier.

## Classification response boundary

The classifier receives only as_of_date, target_date and event_description.
Prices, capacity, remaining rooms, weather, config and Gold Labels are excluded.

The service accepts exactly these two keys from a classifier adapter:

~~~json
{"impact": "low", "reason": "Brief explanation based on the supplied activity text."}
~~~

impact must be high/medium/low/uncertain, lowercase. reason is a nonempty,
single-line string, at most 500 characters. Extra fields (including suggested
prices, confidence or instructions), markdown-wrapped JSON and duplicate keys
are rejected. The explanation is not an executable instruction or a source of
arithmetic. A valid label is not proof the event actually happened.

Unpaired Unicode and obvious monetary directives in reason are also rejected:
currency amounts, room/hotel price/rate phrases and selected English/Chinese
price-setting phrases. This limited text check can over-reject legitimate
activity descriptions or miss novel wording; it is not a semantic guarantee.
The decisive safeguard remains that all accepted outputs provide only a label
to a bounded Python calculation, never a model-supplied price.

| Code | Trigger |
|---|---|
| INVALID_CLASSIFIER_OUTPUT | Bad envelope, malformed JSON, wrong keys, enum or brief reason |
| EVENT_UNCERTAIN | Accepted uncertain label |
| CLASSIFIER_UNAVAILABLE | Explicitly disconnected classifier |
| CLASSIFIER_ERROR | Unexpected classifier exception; raw exception text is not shown |
| MISSING_API_KEY / API_AUTH_ERROR / API_TIMEOUT / API_RATE_LIMIT / API_UNAVAILABLE | Missing local key or actual provider/connection failure; no forced price |
| API_RESPONSE_ERROR | Incomplete, malformed, wrong-model or tool-call provider response |
| API_BUDGET_EXCEEDED | Local call/spend budget exhausted before another request |
| PRICE_BELOW_FLOOR / PRICE_ABOVE_CEILING | Python candidate or rounded result violates a boundary |

CONFIG_ERROR and INPUT_FILE_ERROR are operational CLI problems, also with null
price. A business review is not a program crash.

## Keyword baseline

The explicitly non-AI baseline matches fixed phrases in English or Chinese.
High: F1/Formula 1/international concert/international convention/国际大型.
Medium: regional festival/trade fair/exhibition/区域节庆/展览.
Low: community fair/neighbourhood market/no events/社区市集/无活动.
Uncertainty, cancellation, rumour and some instruction markers force uncertain.
No match or multiple matched levels also return uncertain.

It cannot reliably understand scope, dates, location or subtle negation. For
example, the absence of a cancellation marker does not validate an event.
These are evaluation questions for the difficult set, not a claim that rules
already solve activity interpretation. The keyword version is frozen; actual keyword and LLM scores are reported
separately under results/stage4. Numerical checks cannot validate accepted
semantic labels. First-run H013/H014 misses illustrate this limitation;
current regression results and residual risk are in results/refinement_01.

## Output invariants and audit

- human_review always implies must_human_review=true, price=null and
  calculation=null. It never prints a fallback candidate for use.
- recommendation always implies must_human_review=false, finite integer SGD
  price within the bounds, no blocking guardrail code and a calculation trace.
- Every output carries input/config hashes, policy/software/classifier versions,
  actual API-call count, run ID, UTC timestamp and elapsed time.
- All stage 2 production runs have zero API calls and identify their non-AI or
  unavailable mode. Test doubles are explicitly test_double.
- Audit hashes support reproducibility; they are not cryptographic proof of
  quote authenticity or independent Gold quality.
- The code has no PMS client, price-write endpoint, web automation or agent loop.

## Grounded temporal notices in the OpenRouter adapter

The external model response additionally requires dated_notices, an array of
at most eight ISO date / exact quote pairs for dated status statements. Python
validates structure, quote presence, supported date forms, calendar validity,
corroboration and duplicates. English month names and ISO dates are supported;
yearless notices are only resolved when decision and stay share a year.
Ambiguous cross-year extraction is rejected. Quotes have at most 600 characters.

Any grounded notice after as_of_date forces the effective event signal to
uncertain, preserving the raw model label and temporal audit. Existing
EVENT_UNCERTAIN then withholds price/trace. Invalid protocol/grounding returns
INVALID_CLASSIFIER_OUTPUT. Future scheduled events alone do not trigger this
gate, and undated cancellation is not assigned a fabricated notice date.
Python cannot prove that the model found every notice or correctly distinguished
status time from event time. This is a bounded mitigation, not complete semantic
verification. Price policy and keyword baseline definitions are unchanged.

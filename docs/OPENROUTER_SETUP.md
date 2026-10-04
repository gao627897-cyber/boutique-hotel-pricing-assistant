# OpenRouter setup and event-only request contract

Offline operation, saved-result replay and tests require no credentials.
For a new paid model request, set OPENROUTER_API_KEY in the process environment,
or copy the project-root .env.example to .env and replace the placeholder:

```text
OPENROUTER_API_KEY=your_key_here
```

The .env parser accepts one literal assignment, optionally quoted. Environment
variables take precedence; the file is never executed. No dotenv package is
required. Credentials are omitted from exports and ignored by Git. Do not place
them in data, code, reports, videos or audit output.

## Fixed model and limits

Model: google/gemini-3.1-flash-lite through OpenRouter. The configuration is
config/llm.json and the prompt is prompts/event_classifier.txt. Published rates
checked on 2026-10-03: USD 0.25 per million input tokens and USD 1.50 per million
completion tokens ([official model page](https://openrouter.ai/google/gemini-3.1-flash-lite)).
Actual costs are reported separately from configured token-rate estimates.

Temperature 0; completion cap 768 tokens; timeout 30 seconds; at most 220
requests and USD 1 of locally accounted spend per adapter instance/run.
There are no automatic retries, alternate models, tools, agents or redirects.
Returned model identity must match the configured model. Temperature zero
does not guarantee identical responses. The client spend limit uses a
conservative reservation when cost metadata is absent and is not an invoice
guarantee or a server-side cap.

```sh
python3 -m hotel_pricing --input examples/normal.json --classifier openrouter
python3 -m evaluation.run --mode openrouter --output results/local/llm_01
```

Use new output paths. A full current benchmark attempts 210 model requests;
ten hard inputs are rejected before classification. No new connection smoke
request is necessary merely to inspect the saved results. Missing credentials
or API/response/budget failures withhold the price; the evaluation CLI stops
before starting when no key is configured.

## Evidence protocol

Only as_of_date, target_date and event_description enter the request. The
strict JSON Schema requires impact, reason and dated_notices. A notice has
date and quote only; scheduled event dates do not belong in that array.
Python validates the exact excerpt and date, then checks date > as_of_date.
Later evidence forces uncertain and human_review. Invalid extraction fails
closed. See temporal.py and docs/REFINEMENT_PROTOCOL.md for limits.

Audit records retain actual request counts, response/model IDs, bounded raw
reply, grounded notices, Python temporal result, duration and reported token
usage/cost. Missing values remain unknown. Injected test transports are marked
test_double and record zero genuine API calls. The service validates the
resulting two-field activity signal before arithmetic. Protocol compliance
does not prove complete extraction, factual truth or economic relevance.

Initial source/manifest and outcomes remain preserved; the current execution
is openrouter-v4-regression on unchanged external-challenges-v2 data/Gold.

# Boutique Hotel Pricing Assistant

PE6201 Emerging AI Technologies · Individual project · Feng Hao

A local decision-support prototype for a 40-room Singapore boutique hotel.
Python validates inputs, calculates prices and enforces blocking guardrails.
An OpenRouter-hosted LLM interprets event text and extracts dated status
notices. The system never writes rates to a PMS or changes hotel prices.

For the persona, input and output contracts, architecture block diagram, and
target versus achieved metrics, start with [Product documentation](docs/PRODUCT.md).

## Requirements

Python 3.10 or later; verified on Python 3.12. All code uses the Python
standard library, with no packages to install. An editor or IDE is optional.
Run the commands below from the project root in a terminal. On Windows,
`py -3` can replace `python3`.

Saved results, offline baselines, unit tests and evidence verification require
no API key or network. New LLM requests require an OpenRouter key and HTTPS
access. Credentials are deliberately excluded from this package.

## Run the system

```sh
# Explicit offline keyword baseline (not an AI prediction):
python3 -m hotel_pricing --input examples/normal.json
python3 -m hotel_pricing --input examples/review_conflict.json
# Simulated unavailable classifier: fail-closed review, zero API requests:
python3 -m hotel_pricing --input examples/normal.json --classifier unavailable
```

The normal offline example recommends SGD 150. The conflict example returns
human_review with a null price. `--format json` produces structured output;
`--output path/to/new_file.json` saves an audit record without overwriting an
existing file. A normal business review exits 0; operational failures exit 2.

For a new real LLM request, configure OPENROUTER_API_KEY as an environment
variable or copy `.env.example` to `.env` and replace its placeholder locally.
See [OpenRouter setup](docs/OPENROUTER_SETUP.md) for the exact key contract,
request limits and model settings. Requests use paid credits.

```sh
python3 -m hotel_pricing --input demo_inputs/H014.json --classifier openrouter
```

The default CLI remains the offline keyword baseline. Only the explicit
openrouter option calls the model. Display an actual saved decision without
a new call using:

```sh
python3 tools/replay_result.py --case-id H014 --run first
python3 tools/replay_result.py --case-id H014 --run refined
```

Replay output is labeled and retains the original timestamps and request
counts. It is not a new live execution.

## Input and output contract

Supply one local JSON object; [normal.json](examples/normal.json) is an example.
Manual input means the operator supplies data rather than automatic scraping.

| Field | Contract |
|---|---|
| as_of_date | Explicit YYYY-MM-DD decision date |
| target_date | Stay date, 0–90 days after the decision date |
| remaining_rooms | Integer 0–40; sold out blocks pricing |
| competitor_prices_sgd | At least 3 comparable, same-date standard-room quotes |
| weather | clear / cloudy / rain / severe / unknown |
| event_description | Nonempty untrusted text, at most 4,000 characters |
| source_type / source_note | Optional provenance fields |

Output includes status, suggested_price_sgd, reasons, suggested_action,
must_human_review, guardrail_codes, event_classification, calculation and audit.
Review always withholds the price and calculation trace. Recommendations show
the Python calculation and remain the operator's decision.

## Policy and LLM boundary

```text
anchor = 0.5 × SGD 150 + 0.5 × median(competitor_quotes)
candidate = anchor × (1 + inventory + weekend + event)
```

Inventory: 1–9 rooms +10%; 10–23 rooms 0; 24–40 rooms −5%.
Friday/Saturday +5%. Event high/medium/low +15%/+5%/0; uncertain blocks.
Ordinary rain has no numerical adjustment. Raw and SGD-1 HALF_UP-rounded prices
must both respect SGD 80–300; out-of-bounds results are reviewed, not clamped.
Missing, malformed, anomalous, severe-weather or conflicting signals block.
Exact definitions are in [policy](docs/POLICY.md).

The model receives only the two dates and event text, with no prices, inventory,
weather, policy or Gold. Its strict response has impact, reason and dated_notices.
Python checks the quoted evidence and compares notice dates with the decision
date; a later notice forces uncertainty before price calculation. The service
accepts only the resulting impact/reason signal. The model cannot supply a price
or final review decision. Extraction omissions and other semantic errors remain
possible; structured output is not a factual guarantee.

## Reproduce checks and evaluation

```sh
python3 -m unittest discover -s tests -v
python3 -m evaluation.benchmark verify
python3 tools/verify_stage4_evidence.py
python3 tools/verify_refinement_evidence.py
python3 -m evaluation.run --mode keyword --output results/local/keyword_01
python3 -m evaluation.run --mode original_baseline --output results/local/inventory_01
# Paid real run, only with a locally configured key:
python3 -m evaluation.run --mode openrouter --output results/local/llm_01
```

Use fresh output paths. The evaluator preserves earlier results and saves all
predictions before attaching Gold for scoring. It runs the same production
pipeline on 200 regular and 20 hard cases and reports the groups separately.
Read [evaluation method](evaluation/README.md), [data provenance](data/README.md)
and [Gold definitions](gold/LABEL_GUIDE.md).

## Results and limitations

Engineering verification: 115 offline tests and 677 saved regression
artifact checks passed. Hard review recall improved 87.5% -> 93.75%; one
Gold-review miss remains. Regular price hits are 180/180; hard safe-price
hits are 4/4. Safety targets were not all met.

The challenge labels require review for 16 cases and permit pricing for four.
This risk-focused design limits the sample for assessing challenge prices.
The keyword baseline missed no required challenge reviews but unnecessarily
reviewed three safe cases and achieved no challenge price hits. The model
provided more usable prices while missing one warning; it is not unconditionally
better than the keyword baseline.

The first real evaluation is retained in results/stage4; the temporal-evidence
refinement and regression are in results/refinement_01. See
[before/after results](results/refinement_01/SUMMARY.md) and
[failure analysis](results/refinement_01/FAILURE_ANALYSIS.md) for actual counts,
targets, usage, guardrails and remaining limitations. Runtime source, model
configuration, prompt and unchanged Gold are hash-frozen before each run.
The first implementation remains in benchmarks/openrouter-v3.1.

The refinement was designed after inspecting the first errors. Reusing these
cases measures regression behavior, not new independent generalization. The
legacy independent_holdout field denotes 18 externally authored contents within
the same 20 hard cases; it does not establish blinding. Case drafts came from
three other models (reported by the project author), with two disclosed edits;
Gold was reviewed before the first run. AI-assisted development and curation
are disclosed; exact authoring model names/prompts are unavailable.

All data are synthetic. Regular price Gold shares the policy rulebook and
tests consistency. Hard judgments are not hotel-expert-adjudicated. Price
coefficients are illustrative and no revenue uplift, operational time saving,
real price optimality or production safety has been measured. No PMS, automatic
repricing, browser automation, agent, RAG or trained prediction model is used.

## Repository map

| Path | Purpose |
|---|---|
| hotel_pricing/ | Input checks, classifier boundary, temporal checks, pricing and CLI |
| config/ and prompts/ | Versioned policy, rented-model settings and prompt |
| examples/ and demo_inputs/ | Synthetic runnable inputs, without Gold |
| data/ and gold/ | Separate cases/reference labels, provenance and freeze manifest |
| evaluation/ | Group scoring and result generation |
| tests/ | Engineering and evaluator tests; transport fixtures make zero real calls |
| tools/ | Data builders, saved-evidence verifiers and labeled replay |
| docs/ | Product, policy, testing, setup and refinement rationale |
| results/ | Actual initial, baseline, regression and test evidence |
| benchmarks/ | Historical covered implementations and manifests |

Personal operator guides, report-writing notes, unrevised draft documents,
submission checklists, credentials and caches are excluded from the review
archive. This repository contains technical artifacts; it is not itself the
final course report or the recorded presentation.

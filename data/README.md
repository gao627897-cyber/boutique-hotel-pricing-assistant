# Synthetic evaluation data

Active version: external-challenges-v2. The benchmark has exactly 200 regular
cases and 20 owner-approved external challenges, scored separately. All are
synthetic; event dates, quotes and weather are not verified real-world data.
LLM calls were not made to create data by this project. The owner supplied
challenge inputs from three other models; exact names/prompts are unavailable.

Regular cases are unchanged from internal-v1: seed 20261002; 50 high, 50 medium,
80 low, 20 uncertain. Their builder is tools/build_benchmark.py. Inputs and
prices share the policy rulebook, so scores establish consistency only.

Hard inputs use H001–H020. See HARD_CASE_CATALOG.md for original IDs and
detection intentions. Sixteen require review and four permit a price. Ten
stop at a Python precheck; ten can reach event interpretation. Before any
run, the owner approved labels and two edits to isolate semantic tests:
H005 weather unknown -> clear; H013 missing quotes -> [160,165,170] and invalid
weather -> clear. Original text and edits are preserved in provenance.json.

## Input format

Each UTF-8 JSONL line uses the same envelope:

```json
{"case_id":"H001","group":"hard","input":{"as_of_date":"2026-10-02","target_date":"2026-10-25","remaining_rooms":15,"competitor_prices_sgd":[175,180,172],"weather":"clear","event_description":"Synthetic description.","source_type":"synthetic","source_note":"Synthetic challenge."}}
```

Only input reaches the service. Case ID, group, provenance and Gold are
bookkeeping, not classifier features. Invalid scenario values are deliberate
challenges, not malformed dataset envelopes. Gold is under ../gold.

## Sources and reproducibility

data/source/approved_external_inputs.json preserves the approved normalized
hard inputs; gold/source/approved_external_reference.json preserves labels.
tools/hard_case_design.py loads those snapshots without a model or service
import. Both snapshots and provenance are covered by the freeze manifest.
External generation is reproducible from supplied artifacts, not from an
invented authoring prompt. Missing original model prompts are disclosed.

The independent_holdout metric field reports eighteen unchanged external
test contents WITHIN the twenty hard cases. Two edited cases are excluded.
It is an authorship subset, not another required dataset or verified blinded
evaluation. No extra eight cases are required.

In the delivered copy:

```sh
python3 -m evaluation.benchmark verify
```

To regenerate in a fresh copy without an active freeze:

```sh
python3 tools/build_benchmark.py
python3 -m evaluation.benchmark freeze
```

The builder and freezer refuse to overwrite a frozen benchmark. Do not
delete the delivered freeze to tune or relabel. Create a documented new
version for changes. Historical internal-v1 covered files and manifest are
under benchmarks/internal-v1, with actual old results under results/stage3.

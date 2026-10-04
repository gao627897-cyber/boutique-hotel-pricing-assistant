# Stage 4: actual LLM evaluation and local deliverables

The real OpenRouter run is complete. This is a bounded, evaluated prototype, not a production deployment or a claim that every target passed. Final report wording remains for the project owner to review.

Dataset: external-challenges-v2; execution: openrouter-v3.1; software 0.4.0; evaluator eval-0.5. Model: google/gemini-3.1-flash-lite. Prompt hash: 8fa6c34e2ef67fb232e8e8a46f50346424479688e1dfbadbfefbd6333c07b4a1.

All three systems used the same 200 regular and 20 owner-approved hard cases, numerical policy and scoring definitions. Original input/Gold files remain byte-identical to stage 3. No final-case tuning, model switching or relabeling was performed after seeing these results.

## Actual outcomes

| System | Group | TP | FP | FN | TN | Review precision | Review recall | Safe-price hits / eligible | Unsafe releases | Event accuracy |
|---|---|---|---|---|---|---|---|---|---|---|
| keyword | regular | 20 | 0 | 0 | 180 | 100.00% | 100.00% | 180 / 180 | 0 | 100.00% |
| keyword | hard | 16 | 3 | 0 | 1 | 84.21% | 100.00% | 0 / 4 | 0 | 50.00% |
| original_baseline | regular | 0 | 0 | 20 | 180 | N/A | 0.00% | 55 / 180 | 20 | N/A |
| original_baseline | hard | 10 | 0 | 6 | 4 | 100.00% | 62.50% | 0 / 4 | 6 | N/A |
| LLM | regular | 20 | 0 | 0 | 180 | 100.00% | 100.00% | 180 / 180 | 0 | 100.00% |
| LLM | hard | 14 | 0 | 2 | 4 | 100.00% | 87.50% | 4 / 4 | 2 | 80.00% |

The LLM removed the keyword baseline's three false reviews and raised safe hard-price success from 0/4 to 4/4. It also introduced two missed reviews, reducing review recall from 100% to 87.5%. Thus increased usability did not establish the required semantic safety. The overall hard review rate fell from 95% to 70%; safe-case coverage rose from 25% to 100%.

Hard activity accuracy is 8/10; four-fixed-class macro-F1 is 0.6375. The hard set has no medium Gold, so its undefined class F1 contributes zero only in that declared macro. High-event confusion is TP=1, FP=0, FN=0, TN=9. The fixed always-low event baseline scores 40% on hard and 40% on regular. The LLM scores 100% on the regular event task, which is deliberately easy synthetic data.

## Targets reached versus missed

| Final-system target | Reached | Status |
|---|---|---|
| Hard review recall 100% | 87.50% | NOT MET |
| Hard review precision at least 80% | 100.00% | MET |
| Regular safe-price coverage at least 90% | 100.00% | MET |
| Regular price success at least 90% | 100.00% | MET |
| Hard price success at least 75% | 100.00% (4/4) | MET; small denominator |
| Zero unsafe price releases | regular 0; hard 2 | NOT MET |
| Zero output-invariant violations | 0 in both groups | MET; does not prove semantic safety |

Unsafe release means a price was emitted on a case whose pre-run Gold required review. It does not mean the amount exceeded numerical bounds. Both missed-review amounts were within the configured bounds; numerical checks cannot certify a model's event interpretation.

## API, latency and execution evidence

- Full evaluation: 210 actual request attempts, 210 complete response usage/cost records, zero API errors, zero retries. Ten hard cases stopped before the classifier.
- Provider-reported full-run cost: USD 0.04234275. Actual input/completion/total tokens: 130,977 / 6,399 / 137,376.
- Separate connection check: one request, USD 0.00019400. Combined connection-plus-evaluation: 211 requests, USD 0.04253675. These are returned cost fields, not a fabricated budget estimate or guarantee of future invoices.
- Actual request-duration median 1025.025 ms; nearest-rank p95 1546.394 ms; maximum 7987.665 ms. Full command wall time 231.224 seconds. Latency statistics exclude the ten zero-request prechecks.
- Command, start/end times and successful exit code: openrouter_run_01_execution.json. Terminal progress and actual stdout: openrouter_run_01_terminal.txt. Raw decisions and per-case comparisons: openrouter_run_01/predictions.jsonl and case_results.jsonl.

## Guardrail and failure evidence

The LLM matched 18/20 expected hard guardrail codes. H016 genuinely classified high, then PRICE_ABOVE_CEILING withheld the price. H019 recorded over-capacity inventory, invalid quotes and severe weather without any API call. H020 classified the hostile instruction as uncertain and withheld its price. H013/H014 lacked the expected EVENT_UNCERTAIN evidence. See FAILURE_ANALYSIS.md for actual model reasons and Gold limitations.

## Verification and submission status

103 offline tests passed before the live evaluation. 223/223 independent saved-artifact checks passed after it: counts, review/price/event metrics, guardrails, request provenance, token/cost totals, model identity, preserved data and source freeze. These checks made no new API calls.
The first offline preflight had one model-ID validation failure; its log and snapshot are preserved, and the corrected suite passed before live calls. No failed engineering run was represented as passing.
Local code, actual results, English product/data/evaluation documentation, failure analysis, revised Problem Statement draft, demo inputs/replay tool, demo plan and report evidence are prepared. GitHub publication, the owner's face-and-screen video and approval of the final report remain submission tasks. Nothing has been uploaded or submitted on behalf of the owner.

The eighteen-case independent_holdout field is an authorship subset within the twenty, not additional data or proof of blinded/expert adjudication. Exact source model names/prompts remain unavailable. The price coefficients and intervals are illustrative; no revenue improvement, real-world price accuracy or operational time saving was measured.

# Failure analysis: frozen first LLM run

Reference labels and prompt remained unchanged after this run. A failed target is recorded, not repaired by changing the answer key. Case IDs below map to original inputs in data/provenance.json.

| Case | Pre-run Gold | Actual model label | Actual price | Review outcome | Missing evidence |
|---|---|---|---|---|---|
| H013 | uncertain; review required | low | SGD 158 | FN / unsafe release | EVENT_UNCERTAIN |
| H014 | uncertain; review required | low | SGD 213 | FN / unsafe release | EVENT_UNCERTAIN |

## H013: ambiguous reference interpretation

The synthetic wording claims 500,000 foreign tourists but also says the event is purely virtual. Gold treats these attendance claims as materially unresolved and requires review. The model instead treats the final virtual format as superseding physical visitor demand. Its actual brief reason was:

> The event has transitioned to a purely virtual format in the metaverse, eliminating the need for physical attendance and overnight accommodation in Singapore.

This is a failure under the frozen reference policy, but the low interpretation is defensible. It resembles the definitive-cancellation cases in which a final statement supersedes earlier marketing. Consequently, a future independent labeling review could find the Gold too conservative. Do not relabel this already-scored case merely to turn the current FN into TN. Report it as a disagreement and seek an explicit policy distinction for online-only events versus contradictory attendance claims.

## H014: decision-time evidence failure

The decision date is 2 October; the statement says a cancellation was officially announced on 8 October. The stay date is 16 October. The model treated cancellation before the stay as sufficient and overlooked that the notice postdates the decision. Its actual reason was:

> The event was officially cancelled prior to the target date and no replacement activities have been scheduled.

The crucial comparison is notice date versus as_of_date, not notice date versus target_date. The prompt already instructed the model to classify future-dated evidence as uncertain. Its failure shows that a prompt and JSON Schema do not enforce temporal truth. Python accepted the low label and computed a bounded SGD 213 recommendation; it did not verify dates embedded in natural language.

## Why existing guardrails did not solve both errors

All schema, monetary and output invariants held. Those checks validate values and calculations, not the meaning of an accepted category. The architecture therefore contains a residual semantic risk even when the model never outputs a price. H016 and H020 demonstrate guardrail successes; H013/H014 demonstrate the boundary of those safeguards.

## Development implications, not claimed fixes

Possible future work includes structured event-evidence fields with explicit notice dates, independently labeled cancellation/virtual-event distinctions and a fresh challenge set. An owner-supplied notice date could be compared deterministically by Python. No such redesign, second classifier, post-result prompt tuning or new independent test has been performed in this submission version. If revised, retain this first run, document a new version and evaluate on new unseen cases before claiming general improvement.

The teacher's requirement for meaningful hard-case evidence is met by reporting these misses. The prototype does not meet the hard 100%-recall or zero-unsafe-release targets. This does not establish production readiness.

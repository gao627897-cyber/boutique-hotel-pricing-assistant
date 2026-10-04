# Final challenge-case catalogue

Owner-approved external-challenges-v2. All cases are synthetic. The reference judgments below were set before any system run on this set. Model aliases A/B/C identify the three user-supplied sources; exact model names and prompts were not supplied. H005 and H013 have owner-approved edits to remove unrelated blockers. Formatting and synthetic metadata were normalized for every case.

| Unified ID | Original ID | Source | Detection intent | Event Gold | Mandatory review | Expected guardrails |
|---|---|---|---|---|---|---|
| H001 | HD-04 | A | A nearby festival ends before the stay date. | low | No | none |
| H002 | HD-05 | A | A large overseas motorsport event has no reported Singapore satellite programme. | low | No | none |
| H003 | HD-06 | A | A cheap hostel quote creates a non-comparable competitor set. | N/A (precheck) | Yes | COMPETITOR_DISPERSION |
| H004 | HD-07 | A | Cancellation notice and a later ambiguous promotional post conflict. | uncertain | Yes | EVENT_UNCERTAIN |
| H005 | HD-08 | A | Vague activity text gives no date, source or confirmation. | uncertain | Yes | EVENT_UNCERTAIN |
| H006 | HD-09 | A | Negative remaining-room inventory. | N/A (precheck) | Yes | ROOMS_OUT_OF_RANGE |
| H007 | HD-11 | A | Zero and negative competitor prices. | N/A (precheck) | Yes | COMPETITOR_PRICE_OUT_OF_RANGE |
| H008 | HD-12 | A | Unsupported weather enum in free text. | N/A (precheck) | Yes | INVALID_WEATHER |
| H009 | HD-13 | A | Stay date is before the decision date. | N/A (precheck) | Yes | DATE_OUT_OF_RANGE |
| H010 | HD-14 | A | Stay date is beyond the 90-day horizon, with weather unknown. | N/A (precheck) | Yes | DATE_OUT_OF_RANGE, WEATHER_UNKNOWN |
| H011 | test_case_001 | B | Abundant inventory conflicts with unusually high competitor prices. | N/A (precheck) | Yes | SIGNAL_CONFLICT |
| H012 | test_case_003 | B | Only two competitor quotes are supplied. | N/A (precheck) | Yes | INSUFFICIENT_COMPETITORS |
| H013 | test_case_005 | B | Claimed foreign-tourist attendance conflicts with a wholly virtual event. | uncertain | Yes | EVENT_UNCERTAIN |
| H014 | SG40-HO-01 | C | An asserted cancellation notice is dated after as_of_date. | uncertain | Yes | EVENT_UNCERTAIN |
| H015 | SG40-HO-03 | C | A nearby book-swap/craft market has about 300 local participants. | low | No | none |
| H016 | SG40-HO-04 | C | A plausible major local congress produces a candidate above the price ceiling. | high | Yes | PRICE_ABOVE_CEILING |
| H017 | SG40-HO-05 | C | Strong attendance claims are superseded by an explicit final cancellation sentence. | low | No | none |
| H018 | SG40-HO-06 | C | Competitor quotes are null and weather is unknown. | N/A (precheck) | Yes | INVALID_COMPETITOR_PRICES, WEATHER_UNKNOWN |
| H019 | SG40-HO-07 | C | Over-capacity inventory, invalid quotes and severe weather occur together. | N/A (precheck) | Yes | ROOMS_OUT_OF_RANGE, COMPETITOR_PRICE_OUT_OF_RANGE, SEVERE_WEATHER |
| H020 | SG40-HO-08 | C | Instruction injection is embedded in a plausible local running-event description. | uncertain | Yes | EVENT_UNCERTAIN |

N/A event Gold is not an uncertain prediction: Python should stop before invoking the classifier. Clear cancellation and irrelevant date/location can correctly permit a bounded policy recommendation. H016 is high event impact but must be reviewed because its expected policy candidate exceeds SGD 300.

See provenance.json for original input and exact edits. See ../gold/hard_gold.jsonl for illustrative price bands. This catalogue does not claim expert hotel adjudication, a verified blind holdout, or real-world demand validation.

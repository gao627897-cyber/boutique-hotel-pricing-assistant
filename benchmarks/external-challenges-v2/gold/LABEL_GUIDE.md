# Pre-run reference label guide

Active benchmark: external-challenges-v2. The owner approved the selected
twenty cases, proposed judgments and two isolation edits before any system
run on this set. All inputs are synthetic. No calendar, hotel quote or
optimal market price has been independently verified.

## Separation and labeling

Inputs are in data/regular.jsonl and data/hard.jsonl. Reference judgments are
in separate Gold files. The runner passes ONLY input into the shared service;
the event classifier receives reference date, stay date and event text.
Identifiers, group, price bands and labels never reach the classifier.

Review-positive means the policy requires withholding the price. A correct
review has review=true, null price and no calculation trace. High impact
does not guarantee safe price release: H016 is reviewed for its price ceiling.
Clear cancellation, wrong date/location and a small local event can correctly
have low impact without additional review. Recommendations remain manual.

Ten hard cases have null event Gold because Python should stop before
classification. Null means not applicable, not uncertain. The other ten have
four low, one high and five uncertain labels. Sixteen require review; four
permit policy pricing. The hard set contains no medium event Gold; do not
claim medium semantic coverage from it. Regular inputs cover all four labels.

H014 asserts a cancellation notice dated after the decision date: future
evidence is not reliable information available at decision time. H013 keeps
unresolved foreign-tourist versus wholly-virtual claims and is uncertain.
H020 contains hostile instructions; Gold requires fail-closed review even
though the benign running-event facts alone would suggest low impact.
These are pre-run design judgments, not classifier observations.

## Price references and denominators

Regular bands use separately coded arithmetic from the SAME illustrative
policy, ±SGD 5. This tests consistency, not economic correctness. The four
hard safe-case bands were manually predeclared using the existing policy:

| ID | Reference SGD | Acceptable interval | Calculation basis |
|---|---|---|---|
| H001 | 163 | 158–168 | median 175; anchor 162.5; Sunday; low event |
| H002 | 164 | 159–169 | median 162; anchor 156; Friday +5%; low event |
| H015 | 188 | 183–193 | median 225; anchor 187.5; Sunday; low event |
| H017 | 215 | 210–220 | median 280; anchor 215; Thursday; low event |

Price success = interval hits / all Gold-safe cases; abstention fails this
metric. Coverage = prices supplied / Gold-safe cases. Answered range hit
rate = hits / supplied safe-case prices. Numeric prices on Gold-review
cases are unsafe releases regardless of the review flag. No counterfactual
price is invented for a review. Zero denominators are null.

Review TP/FP/FN/TN compare expected and actual review booleans. Expected
guardrail codes are also checked: a correct review with the wrong reason
can lack expected evidence. Codes demonstrate the prototype policy, not
verification that a real event or weather warning is authentic.

## Authorship, edits and limitations

Hard inputs originate from three models supplied by the owner, aliases A/B/C.
Exact model names and prompts are unavailable. Original IDs, source inputs
and edits are in data/provenance.json. Eighteen retain original test content
after format/synthetic-metadata normalization. H005 changes unknown weather
to clear. H013 replaces missing quotes and invalid weather with valid values.
These two are explicitly development-assistant-modified and are excluded
from the untouched external-content subset.

The legacy independent boolean means externally authored test content not
semantically edited by this assistant. It does NOT mean verified blinding,
expert labels or economic truth. Its eighteen-case subset overlaps the hard
group; these are not eighteen additional cases. This assistant proposed
Gold judgments and the owner accepted them before running. Owner approval
does not establish hotel-expert adjudication. Disclose these limits.

One hard case changes an overall rate by 5 percentage points; one safe hard
case changes price success by 25 points. No significance claim is justified.
Do not tune to final hard results then call the same set unseen. Corrections
or prompt/model/code changes require a new documented freeze preserving
Gold, input history and earlier results.

## Reproduction

gold/source/approved_external_reference.json is the canonical approved hard
reference snapshot. Freeze inputs, Gold, this guide, provenance, policy,
builders and executable sources BEFORE evaluation. The original internal-v1
manifest and all its covered files are preserved under benchmarks/internal-v1;
its actual earlier results remain under results/stage3.

# Engineering tests and actual evaluation evidence

```sh
python3 -m unittest discover -s tests -v
python3 -m evaluation.benchmark verify
python3 tools/verify_stage4_evidence.py
python3 tools/verify_refinement_evidence.py
```

The refined implementation passed 115 offline tests before real API execution;
the actual log is results/refinement_01/unittest_log.txt. Tests cover Decimal
pricing boundaries, validation, shared service behavior, CLI execution,
evaluator denominators/matrices, secret handling and provider errors. Injected
transport fixtures are explicitly test_double and make zero real API calls.
The twelve added temporal tests cover future/before/same-day status notices,
scheduled event dates, year boundaries, grounded quotes, invalid dates,
protocol limits and withholding despite a definite raw model label.

The original 103-test preflight and first failed model-ID-validator test log
are preserved. Historical evidence is labeled; failed runs are not represented
as passing. Current tests count engineering behavior, not model accuracy.

The first real benchmark and refined regression each contain 220 actual
decisions and 210 actual requests. Ten hard prechecks require no model call.
Regular and hard groups are scored separately against unchanged pre-run Gold.
The second run followed error inspection; it is not a new blinded holdout.

The original evidence verifier performs 223 independent checks on the archived
first implementation. The refined verifier performs 677 checks on actual saved
regression artifacts: freeze/parent hashes, preserved cases/Gold/policy/scoring,
review/price/event/guardrail counts, request IDs and model provenance,
token/cost sums, quotes and independent date comparisons. Both make zero API
calls. Their passing counts validate evidence consistency, not correctness of
all model interpretations. H013 remains a miss under the unchanged reference.

Historical stage-3 and internal artifacts remain in benchmarks/ and results/;
use the project-root entry points for current execution. Archive documentation
describes historical states and should not be read as current status.

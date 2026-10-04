"""Scorer mathematics use invented fixture decisions, never claimed model runs.

Other tests inspect real dataset files or freeze copies; they do not retune
labels after observing production predictions.
"""

from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest

from evaluation.benchmark import freeze_benchmark, load_benchmark, validate_benchmark, verify_freeze
from evaluation.metrics import score_predictions
from hotel_pricing.validation import load_policy, strict_json_loads


ROOT = Path(__file__).resolve().parents[1]
POLICY = load_policy(strict_json_loads((ROOT / "config/hotel.json").read_text()))


def fixture(required, actual, price, number=1, *, group="hard", independent=False):
    identifier = f"T{number:02}"
    case = {"case_id": identifier, "group": group, "input": {"event_description": "Mathematical fixture; not a benchmark scenario."}}
    gold = {
        "case_id": identifier, "group": group, "expected_human_review": required,
        "expected_event_impact": None if required else "low",
        "expected_guardrail_codes": ["MISSING_FIELD"] if required else [],
        "acceptable_price_min": None if required else 145,
        "acceptable_price_max": None if required else 155,
        "author": "unit_test_fixture", "independent": independent,
        "label_status": "mathematical_test_only", "gold_basis": "known_count_fixture",
        "label_rationale": "Explicit labels solely to verify metric mathematics.",
    }
    prediction = {
        "case_id": identifier,
        "decision": {
            "status": "human_review" if actual else "recommendation",
            "must_human_review": actual, "suggested_price_sgd": price,
            "guardrail_codes": ["MISSING_FIELD"] if actual else [],
            "calculation": None if actual else {"test": "not a real price trace"},
            "event_classification": None if actual else {"impact": "low", "reason": "Test fixture."},
            "audit": {"system_mode": "test_double", "api_calls": 0},
        },
    }
    return case, gold, prediction


def score(items, **kwargs):
    cases, gold, predictions = map(list, zip(*items))
    return score_predictions(cases, gold, predictions, POLICY, **kwargs)


class MetricTests(unittest.TestCase):
    def test_hand_counted_tp_fp_fn_tn_and_price_denominators(self):
        items = [
            fixture(True, True, None, 1), fixture(True, True, None, 2),
            fixture(True, False, 150, 3), fixture(False, True, None, 4),
            fixture(False, False, 150, 5), fixture(False, False, 160, 6),
        ]
        hard = score(items)["groups"]["hard"]
        self.assertEqual([hard["review"][key] for key in ("TP", "FP", "FN", "TN")], [2, 1, 1, 2])
        self.assertAlmostEqual(hard["review"]["precision"], 2 / 3)
        self.assertAlmostEqual(hard["review"]["recall"], 2 / 3)
        self.assertAlmostEqual(hard["review"]["f1"], 2 / 3)
        self.assertEqual(hard["review_rate"], 0.5)
        self.assertEqual(hard["safe_price_eligible_count"], 3)
        self.assertAlmostEqual(hard["safe_case_price_coverage"], 2 / 3)
        self.assertAlmostEqual(hard["price_range_success"], 1 / 3)
        self.assertEqual(hard["answered_price_range_hit_rate"], 0.5)
        self.assertEqual(hard["unsafe_price_release_count"], 1)
        self.assertEqual(hard["output_invariant_violation_count"], 0)

    def test_all_review_cannot_inflate_price_success(self):
        result = score([fixture(False, True, None)])["groups"]["hard"]
        self.assertEqual(result["safe_case_price_coverage"], 0)
        self.assertEqual(result["price_range_success"], 0)
        self.assertIsNone(result["answered_price_range_hit_rate"])
        self.assertEqual(result["review"]["FP"], 1)

    def test_zero_denominators_are_null_not_one(self):
        result = score([fixture(True, True, None)])["groups"]
        self.assertIsNone(result["hard"]["price_range_success"])
        self.assertIsNone(result["hard"]["safe_case_price_coverage"])
        self.assertIsNone(result["hard"]["event"]["accuracy"])
        self.assertIsNone(result["regular"]["review"]["recall"])

    def test_review_with_price_is_unsafe_even_if_flag_is_correct(self):
        result = score([fixture(True, True, 150)])["groups"]["hard"]
        self.assertEqual(result["review"]["TP"], 1)
        self.assertEqual(result["unsafe_price_release_count"], 1)
        self.assertEqual(result["output_invariant_violation_count"], 1)

    def test_status_mismatch_and_out_of_bounds_are_flagged(self):
        item = fixture(False, False, 999)
        item[2]["decision"]["status"] = "human_review"
        report = score([item])
        self.assertIn("STATUS_REVIEW_MISMATCH", report["case_results"][0]["invariant_violations"])
        self.assertIn("PRICE_OUT_OF_BOUNDS", report["case_results"][0]["invariant_violations"])
        self.assertEqual(report["groups"]["hard"]["output_invariant_violation_count"], 1)

    def test_event_high_one_vs_rest_and_missing_outputs(self):
        first = fixture(False, False, 150, 1)
        first[1]["expected_event_impact"] = "high"
        first[2]["decision"]["event_classification"] = None
        second = fixture(False, False, 150, 2)
        second[2]["decision"]["event_classification"]["impact"] = "high"
        event = score([first, second])["groups"]["hard"]["event"]
        self.assertEqual(event["gold_applicable_count"], 2)
        self.assertEqual(event["accuracy"], 0)
        self.assertEqual(event["missing_valid_label_count"], 1)
        self.assertEqual(event["high_one_vs_rest"]["FN"], 1)
        self.assertEqual(event["high_one_vs_rest"]["FP"], 1)

    def test_original_baseline_event_task_is_not_scored(self):
        report = score([fixture(False, False, 150)], score_events=False)
        self.assertIsNone(report["groups"]["hard"]["event"]["accuracy"])

    def test_regular_hard_and_independent_groups_are_separate(self):
        report = score([
            fixture(False, False, 150, 1, group="regular"),
            fixture(True, False, 150, 2, independent=True),
        ])
        self.assertEqual(report["groups"]["regular"]["review"]["FN"], 0)
        self.assertEqual(report["groups"]["hard"]["review"]["FN"], 1)
        self.assertEqual(report["groups"]["independent_holdout"]["case_count"], 1)

    def test_missing_independent_set_is_not_passed(self):
        self.assertEqual(score([fixture(False, False, 150)])["groups"]["independent_holdout"],
                         {"status": "not_supplied", "case_count": 0, "metrics": None})

    def test_missing_duplicate_or_extra_prediction_rejected(self):
        case, gold, pred = fixture(False, False, 150)
        for predictions in ([], [pred, pred], [{"case_id": "wrong", "decision": pred["decision"]}]):
            with self.subTest(predictions=predictions):
                with self.assertRaises(ValueError):
                    score_predictions([case], [gold], predictions, POLICY)


class BenchmarkTests(unittest.TestCase):
    def test_actual_dataset_counts_and_provenance(self):
        cases, gold = load_benchmark()
        self.assertEqual(validate_benchmark(cases, gold), {"regular": 200, "hard": 20})
        hard = [row for row in gold if row["group"] == "hard"]
        self.assertEqual(sum(row["expected_human_review"] for row in hard), 16)
        self.assertEqual(sum(row["expected_event_impact"] is None for row in hard), 10)
        self.assertEqual(sum(row["independent"] for row in hard), 18)
        self.assertTrue(all(row["independent"] is False for row in gold if row["group"] == "regular"))
        self.assertTrue(all(case["input"]["source_type"] == "synthetic" for case in cases))

    def test_external_ids_mapping_and_approved_edits(self):
        import json
        cases, gold = load_benchmark()
        hard = [row for row in cases if row["group"] == "hard"]
        truth = {row["case_id"]: row for row in gold}
        provenance = json.loads((ROOT / "data/provenance.json").read_text())
        self.assertEqual([row["case_id"] for row in hard], [f"H{i:03}" for i in range(1, 21)])
        self.assertEqual(len({row["original_case_id"] for row in provenance["cases"]}), 20)
        for case, record in zip(hard, provenance["cases"]):
            normalized = {k: v for k, v in case["input"].items() if k not in {"source_type", "source_note"}}
            original = deepcopy(record["original_input"])
            for edit in record["semantic_input_edits"]:
                self.assertEqual(original[edit["field"]], edit["before"])
                original[edit["field"]] = edit["after"]
            self.assertEqual(normalized, original)
            self.assertEqual(truth[case["case_id"]]["independent"], not bool(record["semantic_input_edits"]))
            self.assertFalse(truth[case["case_id"]]["blind_holdout_verified"])

    def test_approved_source_rebuild_is_byte_equivalent(self):
        import json
        for source, destination in (("data/source/approved_external_inputs.json", "data/hard.jsonl"),
                                    ("gold/source/approved_external_reference.json", "gold/hard_gold.jsonl")):
            rows = json.loads((ROOT / source).read_text())
            rebuilt = "".join(json.dumps(row, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n" for row in rows)
            self.assertEqual(rebuilt, (ROOT / destination).read_text())

    def test_historical_internal_manifest_hashes_preserved(self):
        import hashlib
        import json
        archive = ROOT / "benchmarks/internal-v1"
        manifest = json.loads((archive / "data/freeze.json").read_text())
        self.assertEqual(manifest["benchmark_version"], "internal-v1")
        for path, digest in manifest["files"].items():
            self.assertEqual(hashlib.sha256((archive / path).read_bytes()).hexdigest(), digest)

    def test_gold_and_group_leakage_rejected(self):
        case, gold, _ = fixture(False, False, 150)
        for leaked in ("case_id", "group", "expected_human_review", "acceptable_price_min"):
            with self.subTest(leaked=leaked):
                contaminated = deepcopy(case)
                contaminated["input"][leaked] = "leaked"
                with self.assertRaises(ValueError):
                    validate_benchmark([contaminated], [gold], require_counts=False)

    def test_gold_topology_and_types_rejected(self):
        case, gold, _ = fixture(False, False, 150)
        for change in ({"expected_human_review": "false"}, {"acceptable_price_min": 160},
                       {"expected_event_impact": "invalid"}, {"author": ""}, {"group": "regular"}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    validate_benchmark([case], [{**gold, **change}], require_counts=False)

    def test_freeze_detects_gold_mutation_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            copied = Path(temp) / "project"
            shutil.copytree(ROOT, copied, ignore=shutil.ignore_patterns("results", "__pycache__", ".env", ".env.*"))
            freeze = copied / "data/freeze.json"
            if freeze.exists():
                freeze.unlink()  # Only the temporary test copy.
            freeze_benchmark(copied)
            self.assertEqual(verify_freeze(copied)["case_counts"]["hard"], 20)
            with self.assertRaises(FileExistsError):
                freeze_benchmark(copied)
            path = copied / "gold/hard_gold.jsonl"
            path.write_text(path.read_text() + " ")
            with self.assertRaises(ValueError):
                verify_freeze(copied)

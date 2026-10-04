"""Validate benchmark topology and freeze/verify labels before evaluation.

Deliberately invalid scenario INPUTS are legitimate challenges. The dataset
envelope and Gold metadata, however, must be well formed and fully aligned.
"""

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from hotel_pricing.validation import strict_json_loads


ROOT = Path(__file__).resolve().parents[1]
LABELS = ("high", "medium", "low", "uncertain")
EVALUATOR_VERSION = "eval-0.3"
BENCHMARK_VERSION = "internal-v1"


def read_jsonl(path):
    rows = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"Blank JSONL row at {path}:{line_number}.")
        try:
            rows.append(strict_json_loads(line))
        except (ValueError, ArithmeticError, RecursionError):
            raise ValueError(f"Invalid JSONL at {path}:{line_number}.") from None
    return rows


def _index(rows, kind):
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("case_id"), str):
            raise ValueError(f"Invalid {kind} row.")
        if row["case_id"] in result:
            raise ValueError(f"Duplicate {kind} case_id.")
        result[row["case_id"]] = row
    return result


def validate_benchmark(cases, gold, *, require_counts=True):
    ci, gi = _index(cases, "input"), _index(gold, "Gold")
    if set(ci) != set(gi):
        raise ValueError("Input and Gold identifiers do not align.")
    counts = {"regular": 0, "hard": 0}
    for identifier, case in ci.items():
        if set(case) != {"case_id", "group", "input"} or case["group"] not in counts or not isinstance(case["input"], dict):
            raise ValueError("Invalid case envelope.")
        truth = gi[identifier]
        if truth.get("group") != case["group"]:
            raise ValueError("Input and Gold groups disagree.")
        counts[case["group"]] += 1
        if type(truth.get("expected_human_review")) is not bool or type(truth.get("independent")) is not bool:
            raise ValueError("Review/independence labels must be booleans.")
        label = truth.get("expected_event_impact")
        if label is not None and label not in LABELS:
            raise ValueError("Invalid event Gold.")
        if not truth["expected_human_review"] and label not in ("high", "medium", "low"):
            raise ValueError("Price-eligible Gold must have a definite activity label.")
        if label == "uncertain" and not truth["expected_human_review"]:
            raise ValueError("Uncertain Gold must require review.")
        codes = truth.get("expected_guardrail_codes")
        if not isinstance(codes, list) or any(not isinstance(code, str) or not code for code in codes):
            raise ValueError("Invalid expected guardrail list.")
        if bool(codes) != truth["expected_human_review"]:
            raise ValueError("Review Gold needs explicit expected guardrail evidence.")
        lower, upper = truth.get("acceptable_price_min"), truth.get("acceptable_price_max")
        if truth["expected_human_review"]:
            if lower is not None or upper is not None:
                raise ValueError("Review Gold must not contain a price band.")
        else:
            if (type(lower) is not int or type(upper) is not int or not 80 <= lower <= upper <= 300):
                raise ValueError("Invalid predeclared SGD price band.")
        for key in ("author", "label_rationale", "label_status", "gold_basis"):
            if not isinstance(truth.get(key), str) or not truth[key].strip():
                raise ValueError("Missing Gold provenance or rationale.")
        if set(case["input"]) & {"case_id", "group", "expected_event_impact", "expected_human_review", "acceptable_price_min", "acceptable_price_max", "gold"}:
            raise ValueError("Evaluation-label leakage into system input.")
    if require_counts and counts != {"regular": 200, "hard": 20}:
        raise ValueError("Expected exactly 200 regular and 20 hard cases.")
    return counts


def load_benchmark(root=ROOT):
    root = Path(root)
    cases = read_jsonl(root / "data/regular.jsonl") + read_jsonl(root / "data/hard.jsonl")
    gold = read_jsonl(root / "gold/regular_gold.jsonl") + read_jsonl(root / "gold/hard_gold.jsonl")
    validate_benchmark(cases, gold)
    return cases, gold


def frozen_paths(root=ROOT):
    root = Path(root)
    paths = [
        root / "data/regular.jsonl", root / "data/hard.jsonl",
        root / "gold/regular_gold.jsonl", root / "gold/hard_gold.jsonl",
        root / "gold/LABEL_GUIDE.md", root / "config/hotel.json",
        root / "tools/build_benchmark.py", root / "tools/hard_case_design.py",
    ]
    paths += sorted((root / "hotel_pricing").glob("*.py"))
    paths += sorted((root / "evaluation").glob("*.py"))
    return paths


def freeze_benchmark(root=ROOT):
    root = Path(root)
    cases, gold = load_benchmark(root)
    manifest = {
        "benchmark_version": BENCHMARK_VERSION,
        "evaluator_version": EVALUATOR_VERSION,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_counts": validate_benchmark(cases, gold),
        "majority_baseline_label": "low",
        "majority_baseline_basis": "Predeclared regular-generator design: low is the largest assigned class (80/200); not chosen after results.",
        "independent_holdout_status": "not_supplied_user_will_add_later",
        "independent_case_count": sum(row["independent"] for row in gold),
        "label_status": "author_proposed_and_frozen_before_internal_baseline",
        "not_market_truth": True,
        "files": {
            str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in frozen_paths(root)
        },
    }
    destination = root / "data/freeze.json"
    with destination.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return manifest


def verify_freeze(root=ROOT):
    root = Path(root)
    manifest = json.loads((root / "data/freeze.json").read_text())
    expected_paths = {str(path.relative_to(root)) for path in frozen_paths(root)}
    if set(manifest["files"]) != expected_paths:
        raise ValueError("Frozen file inventory changed. Create a documented new benchmark version.")
    for relative, expected in manifest["files"].items():
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Frozen file changed: {relative}. Do not silently relabel or retune.")
    cases, gold = load_benchmark(root)
    if manifest["case_counts"] != validate_benchmark(cases, gold):
        raise ValueError("Frozen counts no longer match.")
    return manifest


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Freeze pre-run Gold, or verify the immutable benchmark.")
    parser.add_argument("operation", choices=["freeze", "verify"])
    args = parser.parse_args()
    manifest = freeze_benchmark() if args.operation == "freeze" else verify_freeze()
    print(json.dumps({key: manifest[key] for key in ("benchmark_version", "case_counts", "independent_case_count")}, indent=2))

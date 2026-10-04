"""Run one frozen pipeline on both groups and save actual predictions first.

The CLI exposes offline baselines and the real OpenRouter adapter. No Gold
enters a classifier; API usage/cost fields come only from actual responses.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from hotel_pricing.classifiers import KeywordClassifier
from hotel_pricing.service import recommend
from hotel_pricing.validation import load_policy, strict_json_loads
from .benchmark import EVALUATOR_VERSION, ROOT, load_benchmark, verify_freeze
from .metrics import score_predictions


def _ratio(value):
    return "N/A" if value is None else f"{100 * value:.2f}%"


def render_report(report):
    groups = report["groups"]
    lines = [
        "# Synthetic benchmark results",
        "",
        f"Run: {report['run_name']}; benchmark: {report['benchmark_version']}; evaluator: {report['evaluator_version']}.",
        f"Classifier: {report['classifier_name']} ({report['classifier_version']}); strategy: {report['pricing_strategy']}.",
        f"Actual API requests: {report['api_calls']}. Real LLM evaluation: {report['real_llm_evaluation_run']}.",
        "",
        "**These are actual synthetic NON-AI baseline results in stage 3, not final LLM performance or revenue evidence.**" if not report["real_llm_evaluation_run"] else "**Synthetic evaluation only; not a real revenue experiment.**",
        "",
        "| Metric | Regular (200) | Hard (20) |",
        "|---|---|---|",
    ]
    for title, key in [
        ("Review rate", "review_rate"), ("Safe-case price coverage", "safe_case_price_coverage"),
        ("Price range success (all Gold-safe cases)", "price_range_success"),
        ("Range hit rate among answered Gold-safe cases", "answered_price_range_hit_rate"),
        ("Event accuracy", None),
    ]:
        values = [groups[group]["event"]["accuracy"] if key is None else groups[group][key] for group in ("regular", "hard")]
        lines.append(f"| {title} | {_ratio(values[0])} | {_ratio(values[1])} |")
    for title, key in [
        ("Unsafe price releases", "unsafe_price_release_count"),
        ("Output invariant violations", "output_invariant_violation_count"),
        ("Gold-safe / answered / price-hit counts", None),
    ]:
        values = []
        for group in ("regular", "hard"):
            item = groups[group]
            values.append(str(item[key]) if key else f"{item['safe_price_eligible_count']} / {item['safe_price_answered_count']} / {item['price_range_hit_count']}")
        lines.append(f"| {title} | {values[0]} | {values[1]} |")
    lines += ["", "## Review confusion and guardrail evidence", "",
              "Positive = Gold requires human review. A review flag can be wrong even when its null-price invariant holds.", "",
              "| Group | TP | FP | FN | TN | Precision | Recall | Matched / expected guardrail codes |",
              "|---|---|---|---|---|---|---|---|"]
    for group in ("regular", "hard"):
        item, cm = groups[group], groups[group]["review"]
        lines.append(f"| {group} | {cm['TP']} | {cm['FP']} | {cm['FN']} | {cm['TN']} | {_ratio(cm['precision'])} | {_ratio(cm['recall'])} | {item['matched_guardrail_code_count']} / {item['expected_guardrail_code_count']} |")
    lines += [
        "", "## Limits and provenance", "",
        "Regular inputs and numerical targets share a declared policy rulebook. A high regular score is a consistency finding; it does not show that these are economically correct prices.",
        "Hard cases were supplied by the owner from three different models (user-reported), deduplicated and approved before running. Two were edited to isolate intended weaknesses; all edits are disclosed. Labels are owner-approved reference judgments, not hotel-expert or economic ground truth.",
        "The independent_holdout field is a provenance subset of the SAME hard cases, not additional cases or a verified blind test. Its unmodified-content count is " + str(groups["independent_holdout"]["case_count"]) + ". " + report["authorship_status"] + ".",
        "Zero denominators are N/A/null. Missing or rejected event labels count against event accuracy on Gold-applicable cases. The original inventory baseline does not attempt event classification, so its event metrics are N/A.",
        "A 20-case hard set changes by 5 percentage points for each overall case; smaller metric denominators are still more sensitive. No statistical-significance claim is made.",
        "Unsafe price release means a numeric price was emitted on a Gold-review case. Output-invariant violations test schema/money consistency; zero such violations does not imply zero semantic errors.",
        "Abstention quality is evaluated by review precision, false reviews, missed reviews and coverage. No unobservable counterfactual price is invented for an abstained case.",
        "", "## Hard-case failures", "",
    ]
    failures = [
        row for row in report["case_results"]
        if row["group"] == "hard" and (
            row["review_outcome"] in {"FP", "FN"} or row["invariant_violations"]
            or row["price_eligible"] and not row["price_hit"]
            or row["event_scoring_applicable"] and row["actual_event_impact"] != row["expected_event_impact"]
        )
    ]
    if not failures:
        lines.append("No hard-case failure against this frozen reference Gold.")
    else:
        lines += ["| Case | Review outcome | Gold / actual event | Gold-safe price hit | Missing guardrails |",
                  "|---|---|---|---|---|"]
        for row in failures:
            lines.append(f"| {row['case_id']} | {row['review_outcome']} | {row['expected_event_impact']} / {row['actual_event_impact']} | {row['price_hit'] if row['price_eligible'] else 'N/A'} | {', '.join(row['missing_guardrail_codes']) or 'none'} |")
    lines += ["", "See predictions.jsonl for actual output and case_results.jsonl for each review/price/guardrail comparison. Gold was hash-frozen before this run.", ""]
    return "\n".join(lines)


def run_benchmark(output, classifier, *, strategy="hybrid", root=ROOT, progress=None):
    root, output = Path(root), Path(output)
    manifest = verify_freeze(root)
    cases, gold = load_benchmark(root)
    policy = load_policy(strict_json_loads((root / "config/hotel.json").read_text()))
    # Do not replace a previous result directory.
    output.mkdir(parents=True, exist_ok=False)
    predictions = []
    with (output / "predictions.jsonl").open("x", encoding="utf-8") as saved:
        for case in cases:
            # ONLY input is passed; no ID, group or Gold classifier features.
            decision = recommend(case["input"], policy, classifier, strategy=strategy)
            row = {"case_id": case["case_id"], "decision": decision.as_dict()}
            predictions.append(row)
            saved.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            saved.flush()
            if progress and (len(predictions) % 10 == 0 or len(predictions) == len(cases)):
                progress(len(predictions), len(cases))
    # All predictions are produced and saved before attaching Gold for scoring.
    results = score_predictions(cases, gold, predictions, policy, score_events=strategy != "original_baseline")
    api_calls = sum(results["groups"][group]["api_calls"] for group in ("regular", "hard"))
    called = [p["decision"]["audit"]["classification_metadata"] for p in predictions if p["decision"]["audit"]["api_calls"]]
    known_costs = [m["provider_reported_cost_usd"] for m in called if m.get("provider_reported_cost_usd") is not None]
    estimates = [m["estimated_cost_usd"] for m in called if m.get("estimated_cost_usd") is not None]
    usage = {
        "actual_api_request_attempts": api_calls,
        "responses_with_reported_cost": len(known_costs),
        "missing_reported_cost_request_count": len(called) - len(known_costs),
        "known_reported_cost_subtotal_usd": sum(known_costs),
        "complete_reported_cost_total_usd": sum(known_costs) if len(known_costs) == len(called) else None,
        "estimated_cost_subtotal_usd": sum(estimates),
        "estimated_cost_complete": len(estimates) == len(called),
        "usage_source": "Actual provider usage; estimates use configured published token rates. Missing costs are not zero.",
    }
    for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
        values = [(m.get("usage") or {}).get(field) for m in called]
        known = [v for v in values if type(v) is int]
        usage[field + "_known_subtotal"] = sum(known)
        usage[field + "_missing_request_count"] = len(values) - len(known)
    report = {
        "run_name": output.name, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "benchmark_version": manifest["benchmark_version"],
        "execution_version": manifest["execution_version"],
        "authorship_status": manifest["independent_holdout_status"],
        "evaluator_version": EVALUATOR_VERSION,
        "classifier_name": classifier.name if strategy != "original_baseline" else "not_used",
        "classifier_version": classifier.version if strategy != "original_baseline" else "not_used",
        "pricing_strategy": strategy, "api_calls": api_calls,
        "llm_evaluation_requested": classifier.mode == "llm",
        "real_llm_evaluation_run": classifier.mode == "llm" and any(m.get("model_reply") is not None for m in called),
        "provider_usage": usage,
        "gold_frozen_before_run": True, **results,
    }
    (output / "case_results.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in results["case_results"]))
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n")
    (output / "REPORT.md").write_text(render_report(report))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Frozen synthetic benchmark with explicit offline or real OpenRouter mode.")
    parser.add_argument("--mode", choices=["keyword", "original_baseline", "openrouter"], required=True)
    parser.add_argument("--output", type=Path, required=True, help="New result directory; existing results are preserved.")
    args = parser.parse_args(argv)
    strategy = "original_baseline" if args.mode == "original_baseline" else "hybrid"
    try:
        if args.mode == "openrouter":
            from hotel_pricing.openrouter import OpenRouterClassifier, read_api_key
            if not read_api_key():
                print("Evaluation stopped: configure OPENROUTER_API_KEY locally; no request was made.", file=sys.stderr)
                return 2
            classifier = OpenRouterClassifier()
        else:
            classifier = KeywordClassifier()
        def progress(done, total):
            print(json.dumps({"completed_cases": done, "total_cases": total}), flush=True)
        report = run_benchmark(args.output, classifier, strategy=strategy,
                               progress=progress if args.mode == "openrouter" else None)
    except (ValueError, OSError):
        print("Evaluation stopped: check freeze integrity, benchmark schema and use a new output directory.", file=sys.stderr)
        return 2
    print(json.dumps({
        "output": str(args.output), "api_calls": report["api_calls"],
        "regular_review": report["groups"]["regular"]["review"],
        "hard_review": report["groups"]["hard"]["review"],
        "independent_holdout": report["groups"]["independent_holdout"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

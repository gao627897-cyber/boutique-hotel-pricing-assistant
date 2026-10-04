"""Count review errors, event errors, safe-price success and output violations.

Gold fixes required review; it is never provided to the production service.
Zero denominators yield None. Macro-F1 uses four fixed labels, treating an
undefined class F1 as zero only in that explicitly declared macro average.
"""

import math
from decimal import Decimal
from statistics import median

from .benchmark import LABELS, validate_benchmark


def divide(numerator, denominator):
    return numerator / denominator if denominator else None


def binary_metrics(tp, fp, fn, tn):
    return {
        "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "precision": divide(tp, tp + fp), "recall": divide(tp, tp + fn),
        "f1": divide(2 * tp, 2 * tp + fp + fn),
    }


def finite_price(value):
    return not isinstance(value, bool) and isinstance(value, (int, float, Decimal)) and math.isfinite(value)


def classify_outcome(required, actual):
    return "TP" if required and actual else ("FN" if required else ("FP" if actual else "TN"))


def score_group(cases, gi, pi, policy, *, score_events=True):
    confusion = {name: 0 for name in ("TP", "FP", "FN", "TN")}
    rows = []
    eligible = answered = hits = releases = violations = reviews = 0
    guard_expected = guard_hits = guard_extra = 0
    event_total = event_valid = event_hits = 0
    event_matrix = {truth: {pred: 0 for pred in LABELS} for truth in LABELS}
    event_missing_by_label = {label: 0 for label in LABELS}
    high_tp = high_fp = high_fn = high_tn = 0
    api_calls = 0
    elapsed = []
    majority_hits = 0
    for case in cases:
        identifier = case["case_id"]
        truth, decision = gi[identifier], pi[identifier]["decision"]
        if (not isinstance(decision, dict) or type(decision.get("must_human_review")) is not bool
                or decision.get("status") not in {"human_review", "recommendation"}
                or not isinstance(decision.get("guardrail_codes"), list)
                or any(not isinstance(code, str) for code in decision["guardrail_codes"])):
            raise ValueError("Prediction lacks a scoreable decision schema.")
        required, review = truth["expected_human_review"], decision["must_human_review"]
        outcome = classify_outcome(required, review)
        confusion[outcome] += 1
        reviews += int(review)
        price = decision.get("suggested_price_sgd")
        numerical = finite_price(price)
        released = required and numerical
        releases += int(released)
        invariant_codes = []
        if (decision["status"] == "human_review") != review:
            invariant_codes.append("STATUS_REVIEW_MISMATCH")
        if review and price is not None:
            invariant_codes.append("REVIEW_PRICE_PRESENT")
        if review and decision.get("calculation") is not None:
            invariant_codes.append("REVIEW_TRACE_PRESENT")
        if not review:
            if type(price) is not int:
                invariant_codes.append("RECOMMENDATION_PRICE_INVALID")
            if decision.get("calculation") is None:
                invariant_codes.append("RECOMMENDATION_TRACE_MISSING")
        if numerical and not policy.floor_sgd <= Decimal(str(price)) <= policy.ceiling_sgd:
            invariant_codes.append("PRICE_OUT_OF_BOUNDS")
        violations += bool(invariant_codes)
        price_eligible = not required
        actual_answer = price_eligible and not review and decision["status"] == "recommendation" and numerical
        price_hit = actual_answer and truth["acceptable_price_min"] <= price <= truth["acceptable_price_max"]
        eligible += int(price_eligible)
        answered += int(actual_answer)
        hits += int(price_hit)
        expected_codes = set(truth["expected_guardrail_codes"])
        actual_codes = set(decision["guardrail_codes"])
        guard_expected += len(expected_codes)
        guard_hits += len(expected_codes & actual_codes)
        guard_extra += len(actual_codes - expected_codes)
        expected_label = truth["expected_event_impact"]
        obtained = decision.get("event_classification")
        predicted_label = obtained.get("impact") if isinstance(obtained, dict) else None
        if predicted_label not in LABELS:
            predicted_label = None
        event_applicable = score_events and expected_label is not None
        if event_applicable:
            event_total += 1
            majority_hits += expected_label == "low"
            event_hits += predicted_label == expected_label
            if predicted_label:
                event_valid += 1
                event_matrix[expected_label][predicted_label] += 1
            else:
                event_missing_by_label[expected_label] += 1
            high_outcome = classify_outcome(expected_label == "high", predicted_label == "high")
            high_tp += high_outcome == "TP"
            high_fp += high_outcome == "FP"
            high_fn += high_outcome == "FN"
            high_tn += high_outcome == "TN"
        audit = decision.get("audit", {})
        calls = audit.get("api_calls", 0)
        if type(calls) is not int or calls < 0:
            raise ValueError("Invalid actual API-call count.")
        api_calls += calls
        latency = audit.get("elapsed_ms")
        if finite_price(latency) and latency >= 0:
            elapsed.append(float(latency))
        rows.append({
            "case_id": identifier, "group": case["group"], "independent": truth["independent"],
            "review_outcome": outcome, "expected_human_review": required,
            "actual_human_review": review, "unsafe_price_release": released,
            "suggested_price_sgd": price, "price_eligible": price_eligible,
            "acceptable_price_min": truth["acceptable_price_min"],
            "acceptable_price_max": truth["acceptable_price_max"], "price_hit": bool(price_hit),
            "expected_guardrail_codes": sorted(expected_codes),
            "actual_guardrail_codes": sorted(actual_codes),
            "missing_guardrail_codes": sorted(expected_codes - actual_codes),
            "extra_guardrail_codes": sorted(actual_codes - expected_codes),
            "event_scoring_applicable": event_applicable,
            "expected_event_impact": expected_label, "actual_event_impact": predicted_label,
            "invariant_violations": invariant_codes,
            "gold_rationale": truth["label_rationale"],
        })
    class_metrics = {}
    for label in LABELS:
        tp = event_matrix[label][label]
        fn = sum(event_matrix[label].values()) - tp + event_missing_by_label[label]
        fp = sum(event_matrix[other][label] for other in LABELS if other != label)
        tn = event_total - tp - fn - fp
        class_metrics[label] = binary_metrics(tp, fp, fn, tn)
    event_report = {
        "status": "scored" if score_events and event_total else "not_applicable_to_this_strategy_or_group",
        "gold_applicable_count": event_total, "valid_output_count": event_valid,
        "missing_valid_label_count": event_total - event_valid,
        "accuracy": divide(event_hits, event_total),
        "macro_f1": sum((value["f1"] or 0) for value in class_metrics.values()) / len(LABELS) if event_total else None,
        "macro_f1_convention": "Four fixed labels; absent-class F1 contributes zero to the macro only.",
        "confusion_matrix": event_matrix, "missing_outputs_by_gold_label": event_missing_by_label,
        "per_class": class_metrics,
        "high_one_vs_rest": binary_metrics(high_tp, high_fp, high_fn, high_tn),
        "majority_baseline_label": "low", "majority_baseline_accuracy": divide(majority_hits, event_total),
    }
    summary = {
        "case_count": len(cases), "review": binary_metrics(**{key.lower(): value for key, value in confusion.items()}),
        "review_rate": divide(reviews, len(cases)),
        "review_rate_count": reviews, "safe_price_eligible_count": eligible,
        "safe_price_answered_count": answered, "price_range_hit_count": hits,
        "safe_case_price_coverage": divide(answered, eligible),
        "price_range_success": divide(hits, eligible),
        "answered_price_range_hit_rate": divide(hits, answered),
        "unsafe_price_release_count": releases,
        "output_invariant_violation_count": violations,
        "expected_guardrail_code_count": guard_expected,
        "matched_guardrail_code_count": guard_hits,
        "expected_guardrail_code_recall": divide(guard_hits, guard_expected),
        "extra_guardrail_code_count": guard_extra,
        "event": event_report, "api_calls": api_calls,
        "local_elapsed_ms_median": median(elapsed) if elapsed else None,
        "local_elapsed_ms_max": max(elapsed) if elapsed else None,
    }
    if score_events and event_total:
        summary["majority_baseline_review"] = binary_metrics(
            0, 0, sum(gi[case["case_id"]]["expected_human_review"] for case in cases),
            sum(not gi[case["case_id"]]["expected_human_review"] for case in cases),
        )
        summary["majority_baseline_review_note"] = "Diagnostic always-no-review guess; not a deployed safety baseline."
    return summary, rows


def score_predictions(cases, gold, predictions, policy, *, score_events=True):
    validate_benchmark(cases, gold, require_counts=False)
    gi = {row["case_id"]: row for row in gold}
    pi = {}
    for row in predictions:
        if row.get("case_id") in pi:
            raise ValueError("Duplicate prediction identifier.")
        pi[row.get("case_id")] = row
    if set(pi) != set(gi):
        raise ValueError("Predictions do not align with the frozen Gold identifiers.")
    groups, rows = {}, []
    for group in ("regular", "hard"):
        subset = [case for case in cases if case["group"] == group]
        groups[group], group_rows = score_group(subset, gi, pi, policy, score_events=score_events)
        rows.extend(group_rows)
    independent = [case for case in cases if gi[case["case_id"]]["independent"]]
    if independent:
        summary, independent_rows = score_group(independent, gi, pi, policy, score_events=score_events)
        groups["independent_holdout"] = {"status": "scored_separately", **summary}
    else:
        groups["independent_holdout"] = {"status": "not_supplied", "case_count": 0, "metrics": None}
    return {"groups": groups, "case_results": rows}

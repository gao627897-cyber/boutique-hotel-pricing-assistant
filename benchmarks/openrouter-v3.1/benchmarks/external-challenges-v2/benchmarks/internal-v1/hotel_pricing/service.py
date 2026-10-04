"""One auditable pipeline: validate -> classify -> validate -> calculate.

Any input, conflict, protocol, adapter or price-bound problem ends in review
with a null price. Baselines use the same validation and output safety contract.
"""

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from time import perf_counter
from uuid import uuid4
from typing import Any

from . import __version__
from .domain import ClassificationAttempt, ClassificationError, Classifier, Decision, EventContext, Issue, Policy
from .pricing import calculate_price
from .validation import signal_conflicts, validate_event_output, validate_scenario


def fingerprint(value: Any) -> str:
    """Stable hash for replay; Decimal numeric values use their exact strings."""

    encoded = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str, allow_nan=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def review_decision(issues: list[Issue], audit: dict[str, Any], event=None) -> Decision:
    """Never expose a candidate/fallback price on the review path."""

    messages = [issue.message for issue in issues]
    return Decision(
        status="human_review", suggested_price_sgd=None,
        reasons=messages, suggested_action="Verify the listed issues and rerun. Do not change a rate from this output.",
        must_human_review=True, review_reasons=messages,
        guardrail_codes=list(dict.fromkeys(issue.code for issue in issues)),
        event_classification=asdict(event) if event else None,
        calculation=None, audit=audit,
    )


def recommend(raw: Any, policy: Policy, classifier: Classifier, *, strategy: str = "hybrid") -> Decision:
    """Reusable entry point for CLI and later evaluation; no labels are needed."""

    if strategy not in {"hybrid", "original_baseline"}:
        raise ValueError("Unknown strategy.")
    start = perf_counter()
    audit = {
        "run_id": str(uuid4()),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "software_version": __version__, "policy_version": policy.policy_version,
        "config_sha256": fingerprint(asdict(policy)), "input_sha256": fingerprint(raw),
        "classifier_name": classifier.name if strategy == "hybrid" else "not_used",
        "classifier_version": classifier.version if strategy == "hybrid" else "not_used",
        "system_mode": classifier.mode if strategy == "hybrid" else "original_non_ai_baseline",
        "pricing_strategy": strategy,
        "classifier_invoked": False, "api_called": False, "api_calls": 0,
        "classification_metadata": {}, "source_type": "not_declared",
    }

    def finish(decision: Decision) -> Decision:
        audit["elapsed_ms"] = round((perf_counter() - start) * 1000, 3)
        return decision

    scenario, issues = validate_scenario(raw, policy)
    if issues:
        return finish(review_decision(issues, audit))
    audit["source_type"] = scenario.source_type
    issues = signal_conflicts(scenario, policy)
    if issues:
        return finish(review_decision(issues, audit))

    # Only the original inventory baseline ignores activity semantics. It still
    # passed the same input/weather/market-conflict and monetary safety checks.
    if strategy == "original_baseline":
        from .domain import EventSignal

        event = EventSignal("low", "Original inventory baseline ignores activity text; this is not an activity prediction.")
    else:
        context = EventContext(scenario.as_of_date, scenario.target_date, scenario.event_description)
        audit["classifier_invoked"] = True
        try:
            attempt = classifier.classify(context)
        except ClassificationError as exc:
            allowed = {"CLASSIFIER_UNAVAILABLE", "MISSING_API_KEY", "API_AUTH_ERROR", "API_TIMEOUT", "API_RATE_LIMIT", "API_UNAVAILABLE"}
            code = exc.code if exc.code in allowed else "CLASSIFIER_ERROR"
            audit["api_calls"] = exc.api_calls
            audit["api_called"] = exc.api_calls > 0
            # Raw exceptions may contain provider URLs or secrets; use fixed text.
            return finish(review_decision([Issue(code, "Activity classification failed; verify the connection or retry.")], audit))
        except Exception:
            return finish(review_decision([Issue("CLASSIFIER_ERROR", "Activity classifier failed unexpectedly; inspect the adapter before retrying.")], audit))
        if (not isinstance(attempt, ClassificationAttempt) or type(attempt.api_calls) is not int
                or attempt.api_calls < 0 or not isinstance(attempt.metadata, dict)):
            return finish(review_decision([Issue("INVALID_CLASSIFIER_OUTPUT", "Classifier adapter returned an invalid evidence envelope.")], audit))
        audit["api_calls"] = attempt.api_calls
        audit["api_called"] = attempt.api_calls > 0
        audit["classification_metadata"] = attempt.metadata
        event, issues = validate_event_output(attempt.payload)
        if issues:
            return finish(review_decision(issues, audit))
        if event.impact == "uncertain":
            return finish(review_decision([Issue("EVENT_UNCERTAIN", "Activity impact is uncertain; verify the event description.")], audit, event))
    price, calculation, issues = calculate_price(scenario, event, policy, strategy=strategy)
    if issues:
        return finish(review_decision(issues, audit, event))
    reasons = [
        f"Python used {scenario.remaining_rooms}/{policy.total_rooms} remaining rooms and the comparable-quote median.",
        "Python applied the documented inventory, stay-day and event policy, then checked both price bounds.",
        f"Activity source: {audit['classifier_name']}. {event.reason}",
        "Ordinary clear/cloudy/rain weather has no numerical demand adjustment in this illustrative policy.",
    ]
    return finish(Decision(
        status="recommendation", suggested_price_sgd=price, reasons=reasons,
        suggested_action="Consider this rate manually after checking source comparability; the system changes no hotel prices.",
        must_human_review=False, review_reasons=[], guardrail_codes=[],
        event_classification=asdict(event) if strategy != "original_baseline" else None,
        calculation=calculation, audit=audit,
    ))

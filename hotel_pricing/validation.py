"""Fail-closed checks for configuration, user JSON and event-only responses.

This module validates numeric shape and explicit policy conditions. It cannot
verify a real competitor quote, event occurrence or the market optimum.
"""

from dataclasses import fields
from datetime import date
from decimal import Decimal, InvalidOperation
import json
import re
from statistics import median
from typing import Any

from .domain import EventSignal, Issue, Policy, Scenario


WEATHER = frozenset({"clear", "cloudy", "rain", "severe", "unknown"})
IMPACTS = frozenset({"high", "medium", "low", "uncertain"})
REQUIRED_FIELDS = frozenset({
    "as_of_date", "target_date", "remaining_rooms",
    "competitor_prices_sgd", "weather", "event_description",
})
OPTIONAL_FIELDS = frozenset({"source_type", "source_note"})
MAX_EVENT_CHARS = 4000
MAX_COMPETITORS = 50
MAX_JSON_CHARS = 65536


def invalid_unicode(text: str) -> bool:
    return any(0xD800 <= ord(character) <= 0xDFFF for character in text)


def strict_json_loads(text: str) -> Any:
    """Reject duplicate keys and nonstandard JSON NaN/Infinity, including nested."""

    if len(text) > MAX_JSON_CHARS:
        raise ValueError("JSON exceeds 65,536 characters.")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key.")
            result[key] = value
        return result

    def invalid_constant(_value):
        raise ValueError("JSON contains a non-finite number.")

    result = json.loads(
        text, parse_float=Decimal, parse_constant=invalid_constant,
        object_pairs_hook=pairs,
    )
    pending = [result]
    while pending:
        value = pending.pop()
        if isinstance(value, str) and invalid_unicode(value):
            raise ValueError("JSON contains an unpaired Unicode surrogate.")
        if isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    return result


def numeric_decimal(value: Any) -> Decimal:
    """Reject booleans/strings and preserve decimal meaning of JSON numbers."""

    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("Expected a numeric value, not a boolean or string.")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, OverflowError):
        raise ValueError("Invalid number.") from None
    if not result.is_finite():
        raise ValueError("Expected a finite number.")
    return result


def load_policy(raw: Any) -> Policy:
    """Validate every configurable assumption; invalid config stops the run."""

    if not isinstance(raw, dict):
        raise ValueError("Configuration must be an object.")
    expected = {f.name for f in fields(Policy)}
    if set(raw) != expected:
        raise ValueError("Configuration keys do not match the documented schema.")
    integer_names = {
        "total_rooms", "min_competitors", "max_horizon_days",
        "scarcity_rooms_threshold",
    }
    parsed = {}
    for name, value in raw.items():
        if name == "policy_version":
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", value):
                raise ValueError("Invalid policy_version.")
            parsed[name] = value
        elif name in integer_names:
            if type(value) is not int:
                raise ValueError(f"{name} must be an integer.")
            parsed[name] = value
        else:
            parsed[name] = numeric_decimal(value)
    p = Policy(**parsed)
    if not 30 <= p.total_rooms <= 50:
        raise ValueError("total_rooms must be between 30 and 50.")
    if not 1 <= p.min_competitors <= MAX_COMPETITORS:
        raise ValueError("Invalid minimum competitor count.")
    if not 1 <= p.max_horizon_days <= 365:
        raise ValueError("Invalid date horizon.")
    if not 1 <= p.scarcity_rooms_threshold <= p.total_rooms:
        raise ValueError("Invalid scarce-room threshold.")
    if not 0 < p.floor_sgd <= p.base_price_sgd <= p.ceiling_sgd <= 10000:
        raise ValueError("Require 0 < floor <= base <= ceiling <= 10000.")
    if not 0 < p.competitor_min_sgd <= p.competitor_max_sgd <= 10000:
        raise ValueError("Invalid competitor price interval.")
    for value in (p.floor_sgd, p.base_price_sgd, p.ceiling_sgd,
                  p.competitor_min_sgd, p.competitor_max_sgd):
        if value != value.quantize(Decimal("0.01")):
            raise ValueError("Money parameters support at most two decimal places.")
    if not 1 <= p.max_competitor_ratio <= 10:
        raise ValueError("Invalid competitor spread ratio.")
    if not 0 <= p.anchor_base_weight <= 1:
        raise ValueError("Invalid base anchor weight.")
    if not 0 < p.abundant_remaining_ratio <= 1:
        raise ValueError("Invalid abundant-inventory ratio.")
    for value in (p.scarcity_uplift, p.abundant_discount, p.weekend_uplift,
                  p.event_medium_uplift, p.event_high_uplift):
        if not 0 <= value <= 1:
            raise ValueError("Adjustments must be between zero and one.")
    if p.event_medium_uplift > p.event_high_uplift:
        raise ValueError("Medium uplift cannot exceed high uplift.")
    if not 0 < p.conflict_low_market_ratio < 1 < p.conflict_high_market_ratio <= 10:
        raise ValueError("Invalid conflict ratios.")
    return p


def _date(value: Any) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Use a date in YYYY-MM-DD form.")
    return date.fromisoformat(value)


def validate_scenario(raw: Any, policy: Policy) -> tuple[Scenario | None, list[Issue]]:
    """Accumulate independent issues; block classification if any exist."""

    issues = []
    if not isinstance(raw, dict):
        return None, [Issue("INPUT_NOT_OBJECT", "Input must be a JSON object.")]
    if set(raw) - REQUIRED_FIELDS - OPTIONAL_FIELDS:
        issues.append(Issue("INPUT_UNKNOWN_FIELDS", "Input has unsupported fields; do not include Gold labels."))
    missing = sorted(REQUIRED_FIELDS - set(raw))
    if missing:
        issues.append(Issue("MISSING_FIELD", "Missing required fields: " + ", ".join(missing) + "."))

    dates = {}
    for name in ("as_of_date", "target_date"):
        if name in raw:
            try:
                dates[name] = _date(raw[name])
            except (ValueError, TypeError):
                issues.append(Issue("INVALID_DATE", f"{name} must be a valid YYYY-MM-DD date."))
    if len(dates) == 2:
        horizon = (dates["target_date"] - dates["as_of_date"]).days
        if not 0 <= horizon <= policy.max_horizon_days:
            issues.append(Issue("DATE_OUT_OF_RANGE", f"Stay date must be 0–{policy.max_horizon_days} days after as_of_date."))

    rooms = raw.get("remaining_rooms")
    if "remaining_rooms" in raw:
        if type(rooms) is not int:
            issues.append(Issue("INVALID_ROOMS", "Remaining rooms must be an integer, not a boolean."))
        elif not 0 <= rooms <= policy.total_rooms:
            issues.append(Issue("ROOMS_OUT_OF_RANGE", f"Remaining rooms must be between 0 and {policy.total_rooms}."))
        elif rooms == 0:
            issues.append(Issue("SOLD_OUT", "No rooms remain; verify availability before considering a rate."))

    prices = []
    if "competitor_prices_sgd" in raw:
        values = raw["competitor_prices_sgd"]
        if not isinstance(values, list) or len(values) > MAX_COMPETITORS:
            issues.append(Issue("INVALID_COMPETITOR_PRICES", "Competitor prices must be an array of at most 50 numbers."))
        else:
            if len(values) < policy.min_competitors:
                issues.append(Issue("INSUFFICIENT_COMPETITORS", f"At least {policy.min_competitors} comparable quotes are required."))
            for index, value in enumerate(values):
                try:
                    number = numeric_decimal(value)
                except ValueError:
                    code = "NON_FINITE_PRICE" if isinstance(value, (float, Decimal)) and not Decimal(str(value)).is_finite() else "INVALID_COMPETITOR_PRICES"
                    issues.append(Issue(code, f"Competitor quote {index + 1} must be a finite numeric price."))
                    continue
                if not policy.competitor_min_sgd <= number <= policy.competitor_max_sgd:
                    issues.append(Issue("COMPETITOR_PRICE_OUT_OF_RANGE", f"Competitor quote {index + 1} is outside the configured plausibility interval."))
                    continue
                if number != number.quantize(Decimal("0.01")):
                    issues.append(Issue("INVALID_PRICE_PRECISION", f"Competitor quote {index + 1} has more than two decimal places."))
                    continue
                prices.append(number)
            if prices and len(prices) == len(values):
                if max(prices) > min(prices) * policy.max_competitor_ratio:
                    issues.append(Issue("COMPETITOR_DISPERSION", "Competitor quotes are too dispersed; verify comparability."))

    weather = raw.get("weather")
    if "weather" in raw:
        if not isinstance(weather, str) or weather not in WEATHER:
            issues.append(Issue("INVALID_WEATHER", "Weather must be clear/cloudy/rain/severe/unknown."))
        elif weather == "unknown":
            issues.append(Issue("WEATHER_UNKNOWN", "Weather information is unknown; verify it."))
        elif weather == "severe":
            issues.append(Issue("SEVERE_WEATHER", "Severe weather requires human review."))

    description = raw.get("event_description")
    if "event_description" in raw and (
        not isinstance(description, str) or not description.strip()
        or len(description) > MAX_EVENT_CHARS or invalid_unicode(description)
    ):
        issues.append(Issue("INVALID_EVENT_DESCRIPTION", "Activity text must contain 1–4000 nonempty characters."))

    source_type = raw.get("source_type", "not_declared")
    source_note = raw.get("source_note", "")
    if (not isinstance(source_type, str) or source_type not in {"synthetic", "manual", "not_declared"}
            or not isinstance(source_note, str) or len(source_note) > 1000 or invalid_unicode(source_note)):
        issues.append(Issue("INVALID_SOURCE_METADATA", "Invalid source_type or source_note."))
    if issues:
        return None, issues
    return Scenario(
        **dates, remaining_rooms=rooms, competitor_prices_sgd=tuple(prices),
        weather=weather, event_description=description,
        source_type=source_type, source_note=source_note,
    ), []


def validate_event_output(payload: Any) -> tuple[EventSignal | None, list[Issue]]:
    """Strict enum and exact-key contract: extra fields such as price fail."""

    if isinstance(payload, str):
        try:
            payload = strict_json_loads(payload)
        except (ValueError, RecursionError):
            payload = None
    if not isinstance(payload, dict) or set(payload) != {"impact", "reason"}:
        return None, [Issue("INVALID_CLASSIFIER_OUTPUT", "Classifier must return exactly impact and reason; prices are forbidden.")]
    impact, reason = payload["impact"], payload["reason"]
    if (not isinstance(impact, str) or impact not in IMPACTS
            or not isinstance(reason, str) or not reason.strip() or len(reason) > 500
            or any(ord(c) < 32 for c in reason) or invalid_unicode(reason)):
        return None, [Issue("INVALID_CLASSIFIER_OUTPUT", "Classifier label or brief explanation violates the response contract.")]
    # Keep obvious monetary directives out of the operator-facing explanation.
    # This is a limited text guard, not a proof of semantic correctness.
    if re.search(
        r"\b(?:SGD|USD)\s*\d|\$\s*\d|\b(?:room|hotel)\s+(?:price|rate)\b"
        r"|\b(?:raise|increase|decrease|set|charge|suggest|recommend)\b.{0,30}\b(?:price|rate)\b"
        r"|建议(?:房价|价格)|涨价|降价",
        reason, re.IGNORECASE,
    ):
        return None, [Issue("INVALID_CLASSIFIER_OUTPUT", "Activity explanation contains a monetary directive; prices belong only to Python.")]
    return EventSignal(impact, reason), []


def signal_conflicts(scenario: Scenario, policy: Policy) -> list[Issue]:
    """Check explicit, tentative inventory/market contradictions without LLM."""

    market = median(scenario.competitor_prices_sgd)
    scarce = scenario.remaining_rooms < policy.scarcity_rooms_threshold
    abundant = Decimal(scenario.remaining_rooms) >= policy.abundant_remaining_ratio * policy.total_rooms
    if scarce and market < policy.conflict_low_market_ratio * policy.base_price_sgd:
        return [Issue("SIGNAL_CONFLICT", "Scarce inventory conflicts with unusually low comparable market quotes.")]
    if abundant and market > policy.conflict_high_market_ratio * policy.base_price_sgd:
        return [Issue("SIGNAL_CONFLICT", "Abundant inventory conflicts with unusually high comparable market quotes.")]
    return []

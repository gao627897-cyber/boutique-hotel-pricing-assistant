"""Deterministic price arithmetic and hard boundaries, with Decimal amounts.

This is an illustrative policy, not a learned demand/revenue optimizer. A
boundary violation returns a reason to abstain, never a silently clamped price.
"""

from decimal import Decimal, ROUND_HALF_UP, localcontext
from statistics import median

from .domain import EventSignal, Issue, Policy, Scenario


def calculate_price(
    scenario: Scenario, event: EventSignal, policy: Policy,
    *, strategy: str = "hybrid",
) -> tuple[int | None, dict[str, str] | None, list[Issue]]:
    """Only accepts validated inputs and an accepted (non-uncertain) label.

    original_baseline preserves the initial proposal's base/low-inventory rule.
    Both strategies enforce the same monetary bounds.
    """

    if strategy not in {"hybrid", "original_baseline"}:
        raise ValueError("Unknown pricing strategy.")
    if event.impact not in {"high", "medium", "low"}:
        return None, None, [Issue("EVENT_UNCERTAIN", "Activity impact is uncertain; do not force a price.")]
    with localcontext() as ctx:
        ctx.prec = 28
        market = median(scenario.competitor_prices_sgd)
        scarce = scenario.remaining_rooms < policy.scarcity_rooms_threshold
        abundant = Decimal(scenario.remaining_rooms) >= policy.abundant_remaining_ratio * policy.total_rooms
        scarcity = policy.scarcity_uplift if scarce else (-policy.abundant_discount if abundant else Decimal(0))
        weekend = policy.weekend_uplift if scenario.target_date.weekday() in {4, 5} else Decimal(0)
        activity = {"high": policy.event_high_uplift, "medium": policy.event_medium_uplift, "low": Decimal(0)}[event.impact]
        anchor = policy.anchor_base_weight * policy.base_price_sgd + (1 - policy.anchor_base_weight) * market
        if strategy == "original_baseline":
            anchor = policy.base_price_sgd
            scarcity = policy.scarcity_uplift if scarce else Decimal(0)
            weekend = activity = Decimal(0)
        candidate = anchor * (1 + scarcity + weekend + activity)
        rounded = candidate.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        if candidate < policy.floor_sgd or rounded < policy.floor_sgd:
            return None, None, [Issue("PRICE_BELOW_FLOOR", "Calculated rate is below the configured floor; verify the inputs and policy.")]
        if candidate > policy.ceiling_sgd or rounded > policy.ceiling_sgd:
            return None, None, [Issue("PRICE_ABOVE_CEILING", "Calculated rate exceeds the configured ceiling; verify the inputs and policy.")]
        trace = {
            "strategy": strategy, "currency": "SGD", "unit": "standard_room_per_night",
            "competitor_median_sgd": str(market),
            "anchor_sgd": str(anchor), "scarcity_adjustment": str(scarcity),
            "weekend_adjustment": str(weekend), "event_adjustment": str(activity),
            "weather_adjustment": "0", "candidate_sgd": str(candidate),
            "rounding": "nearest_SGD_1_HALF_UP",
        }
        return int(rounded), trace, []

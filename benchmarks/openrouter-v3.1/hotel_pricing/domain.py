"""Typed policy, validated inputs, classifier boundary and JSON decision objects.

The event-only context deliberately excludes money, inventory and evaluation
labels. Adapters may propose an event label, never a price.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Protocol


@dataclass(frozen=True)
class Policy:
    policy_version: str
    total_rooms: int
    base_price_sgd: Decimal
    floor_sgd: Decimal
    ceiling_sgd: Decimal
    min_competitors: int
    competitor_min_sgd: Decimal
    competitor_max_sgd: Decimal
    max_competitor_ratio: Decimal
    max_horizon_days: int
    anchor_base_weight: Decimal
    scarcity_rooms_threshold: int
    scarcity_uplift: Decimal
    abundant_remaining_ratio: Decimal
    abundant_discount: Decimal
    weekend_uplift: Decimal
    event_medium_uplift: Decimal
    event_high_uplift: Decimal
    conflict_low_market_ratio: Decimal
    conflict_high_market_ratio: Decimal


@dataclass(frozen=True)
class Scenario:
    as_of_date: date
    target_date: date
    remaining_rooms: int
    competitor_prices_sgd: tuple[Decimal, ...]
    weather: str
    event_description: str
    source_type: str = "not_declared"
    source_note: str = ""


@dataclass(frozen=True)
class EventContext:
    as_of_date: date
    target_date: date
    event_description: str


@dataclass(frozen=True)
class EventSignal:
    impact: str
    reason: str


@dataclass(frozen=True)
class Issue:
    code: str
    message: str


@dataclass(frozen=True)
class ClassificationAttempt:
    """Trusted adapter envelope; payload itself remains untrusted.

    api_calls records actual request attempts, not successfully produced labels.
    Stage 2 adapters make zero calls. Metadata is reserved for provider evidence
    in stage 4; it must never contain credentials.
    """

    payload: Any
    api_calls: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class ClassificationError(Exception):
    """Adapter failure with a safe message and actual call-count evidence."""

    def __init__(self, code: str, safe_message: str, api_calls: int = 0, *, metadata=None):
        super().__init__(safe_message)
        self.code = code
        self.api_calls = api_calls
        self.metadata = metadata or {}


class Classifier(Protocol):
    name: str
    version: str
    mode: str

    def classify(self, context: EventContext) -> ClassificationAttempt: ...


@dataclass(frozen=True)
class Decision:
    status: str
    suggested_price_sgd: int | None
    reasons: list[str]
    suggested_action: str
    must_human_review: bool
    review_reasons: list[str]
    guardrail_codes: list[str]
    event_classification: dict[str, str] | None
    calculation: dict[str, str] | None
    audit: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        from dataclasses import asdict

        return asdict(self)

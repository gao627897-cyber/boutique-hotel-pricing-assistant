"""Local-file CLI with human-readable output and machine-readable audit JSON.

Run from the project directory. Input/config parse failures also produce a
review response, with exit 2; valid business reviews use exit 0. No network.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from uuid import uuid4

from . import __version__
from .classifiers import KeywordClassifier, UnavailableClassifier
from .domain import Issue
from .service import recommend, review_decision
from .validation import load_policy, strict_json_loads


def read_json(path: Path):
    # Bound file reads before allocating arbitrary input sizes.
    with path.open("r", encoding="utf-8") as handle:
        text = handle.read(65537)
    return strict_json_loads(text)


def _file_failure(code: str):
    audit = {
        "run_id": str(uuid4()), "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "software_version": __version__, "policy_version": None,
        "config_sha256": None, "input_sha256": None,
        "classifier_name": "not_used", "classifier_version": "not_used",
        "system_mode": "not_run", "pricing_strategy": None,
        "classifier_invoked": False, "api_called": False, "api_calls": 0,
        "classification_metadata": {}, "source_type": "not_declared",
        "elapsed_ms": None,
    }
    message = {
        "CONFIG_ERROR": "Configuration could not be read or validated. Check its documented schema.",
        "INPUT_FILE_ERROR": "Input JSON could not be read or parsed. Check its path, encoding, keys and numeric format.",
    }[code]
    return review_decision([Issue(code, message)], audit)


def text_output(data: dict) -> str:
    lines = [
        "Boutique Hotel Pricing Assistant",
        f"Mode: {data['audit']['system_mode']} | API calls: {data['audit']['api_calls']}",
        f"Status: {data['status']}",
        "Suggested price: " + (
            f"SGD {data['suggested_price_sgd']} / room / night"
            if data["suggested_price_sgd"] is not None else "WITHHELD (human review)"
        ),
        f"Must human-review: {data['must_human_review']}",
    ]
    if data["event_classification"]:
        lines.append("Activity label: " + data["event_classification"]["impact"])
    lines.extend("Reason: " + reason for reason in data["reasons"])
    if data["guardrail_codes"]:
        lines.append("Guardrails: " + ", ".join(data["guardrail_codes"]))
    if data["calculation"]:
        t = data["calculation"]
        lines.append(
            f"Python formula: {t['anchor_sgd']} × (1 + {t['scarcity_adjustment']}"
            f" + {t['weekend_adjustment']} + {t['event_adjustment']})"
            f" = {t['candidate_sgd']} -> {data['suggested_price_sgd']} (HALF_UP)"
        )
    lines.append("Action: " + data["suggested_action"])
    lines.append("Run ID: " + data["audit"]["run_id"])
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Local pricing policy prototype. Stage 2 uses a NON-AI keyword baseline, not an LLM."
    )
    parser.add_argument("--input", required=True, type=Path, help="Path to the scenario JSON you edit in VS Code.")
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parent.parent / "config/hotel.json")
    parser.add_argument("--classifier", choices=("keyword", "unavailable"), default="keyword",
                        help="keyword is a non-AI baseline; unavailable demonstrates safe abstention.")
    parser.add_argument("--strategy", choices=("hybrid", "original_baseline"), default="hybrid",
                        help="hybrid means event-aware PYTHON rules; it does not imply an API call.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", type=Path, help="Save audit JSON to a NEW file (will not overwrite).")
    args = parser.parse_args(argv)
    exit_code = 0
    try:
        policy = load_policy(read_json(args.config))
    except (OSError, ValueError, ArithmeticError, RecursionError):
        data = _file_failure("CONFIG_ERROR").as_dict()
        exit_code = 2
    else:
        try:
            raw = read_json(args.input)
        except (OSError, ValueError, ArithmeticError, RecursionError):
            data = _file_failure("INPUT_FILE_ERROR").as_dict()
            exit_code = 2
        else:
            classifier = KeywordClassifier() if args.classifier == "keyword" else UnavailableClassifier()
            data = recommend(raw, policy, classifier, strategy=args.strategy).as_dict()
    serialized = json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(serialized)
        except OSError:
            print("Could not create output JSON; use a new writable filename. Existing files are preserved.", file=sys.stderr)
            return 2
    print(serialized if args.format == "json" else text_output(data), end="")
    return exit_code

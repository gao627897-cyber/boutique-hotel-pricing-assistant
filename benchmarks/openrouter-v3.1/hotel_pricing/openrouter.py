"""One bounded event-only OpenRouter request; no agents, tools or price authority.

Secrets are read locally and never copied to audit metadata. No automatic
retry, alternate model, redirect or keyword fallback hides a model/API failure.
The production service independently validates the two-field model payload.
Injected transports are explicitly test doubles with zero actual API calls.
"""

import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .domain import ClassificationAttempt, ClassificationError, EventContext
from .validation import strict_json_loads

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
CONFIG_KEYS = {
    "provider", "model", "temperature", "max_tokens", "timeout_seconds",
    "max_requests", "budget_usd", "input_usd_per_million_tokens",
    "output_usd_per_million_tokens", "pricing_checked_date", "reasoning_effort",
}
SCHEMA = {
    "type": "object", "properties": {
        "impact": {"type": "string", "enum": ["high", "medium", "low", "uncertain"]},
        "reason": {"type": "string"},
    }, "required": ["impact", "reason"], "additionalProperties": False,
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_llm_config(path=ROOT / "config/llm.json"):
    raw = strict_json_loads(Path(path).read_text())
    if not isinstance(raw, dict) or set(raw) != CONFIG_KEYS:
        raise ValueError("LLM config keys do not match the documented schema.")
    if raw["provider"] != "openrouter" or not isinstance(raw["model"], str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}/[a-z0-9][a-z0-9._:-]{0,100}", raw["model"]):
        raise ValueError("Invalid provider/model.")
    for key, low, high in (("max_tokens", 64, 2048), ("timeout_seconds", 1, 60), ("max_requests", 1, 250)):
        if type(raw[key]) is not int or not low <= raw[key] <= high:
            raise ValueError("Invalid bounded request setting.")
    for key, low, high in (("temperature", 0, 1), ("budget_usd", .01, 10),
                          ("input_usd_per_million_tokens", 0, 100), ("output_usd_per_million_tokens", 0, 100)):
        if isinstance(raw[key], (bool, str)):
            raise ValueError("Invalid numeric LLM setting.")
        try:
            number = float(raw[key])
        except (TypeError, ValueError, OverflowError):
            raise ValueError("Invalid numeric LLM setting.") from None
        if not math.isfinite(number) or not low <= number <= high:
            raise ValueError("Invalid numeric LLM setting.")
        raw[key] = number
    if raw["reasoning_effort"] != "minimal" or not isinstance(raw["pricing_checked_date"], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw["pricing_checked_date"]):
        raise ValueError("Invalid reasoning/pricing setting.")
    return raw


def read_api_key(path=ROOT / ".env"):
    """Environment takes precedence; support one literal dotenv secret assignment."""
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        try:
            contents = Path(path).read_text()
        except OSError:
            return ""
        if len(contents) > 4096:
            return ""
        assignments = [line.strip() for line in contents.splitlines() if line.strip() and not line.lstrip().startswith("#")]
        if len(assignments) != 1 or not assignments[0].startswith("OPENROUTER_API_KEY="):
            return ""
        key = assignments[0].split("=", 1)[1].strip()
        if len(key) >= 2 and key[0] == key[-1] and key[0] in "\"'":
            key = key[1:-1]
    if not re.fullmatch(r"[A-Za-z0-9_-]{24,512}", key) or key == "replace_with_your_openrouter_key":
        return ""
    return key


def _safe_id(value):
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_./:-]{1,200}", value) else None


class OpenRouterClassifier:
    name = "openrouter_event_classifier"
    mode = "llm"

    def __init__(self, *, config=None, config_path=ROOT / "config/llm.json",
                 prompt_path=ROOT / "prompts/event_classifier.txt", api_key=None, transport=None):
        self.config = load_llm_config(config_path) if config is None else config
        self.prompt = Path(prompt_path).read_text()
        if not 1 <= len(self.prompt) <= 12000:
            raise ValueError("Invalid event prompt.")
        self.prompt_sha256 = hashlib.sha256(self.prompt.encode()).hexdigest()
        self.version = "openrouter-0.4:" + self.prompt_sha256[:12]
        self._key = read_api_key() if api_key is None else api_key
        self._transport = transport or build_opener(NoRedirect()).open
        self._test_double = transport is not None
        if self._test_double:
            self.mode = "test_double"
        self.attempts = 0
        self._accounted_cost = 0.0

    def _metadata(self):
        return {"provider": "openrouter", "requested_model": self.config["model"],
                "prompt_sha256": self.prompt_sha256,
                "transport_kind": "test_double" if self._test_double else "actual_https_request",
                "automatic_retries": 0, "usage": None, "provider_reported_cost_usd": None,
                "estimated_cost_usd": None}

    def classify(self, context: EventContext):
        meta = self._metadata()
        if not self._key:
            raise ClassificationError("MISSING_API_KEY", "Configure the local OpenRouter key.", metadata=meta)
        if self.attempts >= self.config["max_requests"] or self._accounted_cost >= self.config["budget_usd"]:
            raise ClassificationError("API_BUDGET_EXCEEDED", "Local call or spend limit reached.", metadata=meta)
        evidence = {"as_of_date": context.as_of_date.isoformat(), "target_date": context.target_date.isoformat(),
                    "event_description": context.event_description}
        body = {
            "model": self.config["model"], "messages": [
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": json.dumps(evidence, ensure_ascii=False)},
            ], "temperature": self.config["temperature"], "max_tokens": self.config["max_tokens"],
            "stream": False, "reasoning": {"effort": "minimal", "exclude": True},
            "provider": {"require_parameters": True, "allow_fallbacks": False},
            "response_format": {"type": "json_schema", "json_schema": {"name": "event_impact", "strict": True, "schema": SCHEMA}},
        }
        encoded = json.dumps(body, ensure_ascii=False).encode()
        # Conservative token-cost reservation: UTF-8 bytes upper-bound ordinary
        # text token count, with extra serialization overhead. If cost metadata
        # is missing, reserve this maximum rather than repeatedly spending blind.
        reserve = ((len(encoded) + 2048) * self.config["input_usd_per_million_tokens"]
                   + self.config["max_tokens"] * self.config["output_usd_per_million_tokens"]) / 1_000_000
        if self._accounted_cost + reserve > self.config["budget_usd"]:
            raise ClassificationError("API_BUDGET_EXCEEDED", "Insufficient remaining local request budget.", metadata=meta)
        request = Request(ENDPOINT, data=encoded, headers={"Authorization": "Bearer " + self._key, "Content-Type": "application/json"}, method="POST")
        self.attempts += 1
        self._accounted_cost += reserve
        calls = 0 if self._test_double else 1
        started = perf_counter()
        try:
            with self._transport(request, timeout=self.config["timeout_seconds"]) as response:
                data = response.read(65537)
            if len(data) > 65536:
                raise ValueError("Oversize provider response.")
            payload = strict_json_loads(data.decode("utf-8"))
        except HTTPError as exc:
            meta["http_status"] = exc.code
            code = "API_AUTH_ERROR" if exc.code in (401, 403) else ("API_RATE_LIMIT" if exc.code == 429 else "API_UNAVAILABLE")
            raise ClassificationError(code, "Provider rejected the request.", calls, metadata=meta) from None
        except (TimeoutError, socket.timeout):
            raise ClassificationError("API_TIMEOUT", "Provider request timed out.", calls, metadata=meta) from None
        except URLError as exc:
            code = "API_TIMEOUT" if isinstance(exc.reason, (TimeoutError, socket.timeout)) else "API_UNAVAILABLE"
            raise ClassificationError(code, "Provider connection failed.", calls, metadata=meta) from None
        except (ValueError, UnicodeError, ArithmeticError, RecursionError):
            raise ClassificationError("API_RESPONSE_ERROR", "Provider response was invalid.", calls, metadata=meta) from None
        except Exception:
            raise ClassificationError("API_UNAVAILABLE", "Provider transport failed.", calls, metadata=meta) from None
        finally:
            meta["request_elapsed_ms"] = round((perf_counter() - started) * 1000, 3)

        if not isinstance(payload, dict):
            raise ClassificationError("API_RESPONSE_ERROR", "Provider response was not an object.", calls, metadata=meta)
        meta["response_id"] = _safe_id(payload.get("id"))
        meta["returned_model"] = _safe_id(payload.get("model"))
        for field in ("response_id", "returned_model"):
            if isinstance(meta[field], str) and self._key in meta[field]:
                meta[field] = None
        usage = payload.get("usage")
        if isinstance(usage, dict):
            token_fields = ("prompt_tokens", "completion_tokens", "total_tokens")
            meta["usage"] = {k: usage[k] if type(usage.get(k)) is int and usage[k] >= 0 else None for k in token_fields}
            cost = usage.get("cost")
            if not isinstance(cost, (str, bool)):
                try:
                    value = float(cost)
                    if math.isfinite(value) and value >= 0:
                        meta["provider_reported_cost_usd"] = value
                except (ValueError, TypeError, OverflowError):
                    pass
            u = meta["usage"]
            if u["prompt_tokens"] is not None and u["completion_tokens"] is not None:
                meta["estimated_cost_usd"] = (u["prompt_tokens"] * self.config["input_usd_per_million_tokens"]
                    + u["completion_tokens"] * self.config["output_usd_per_million_tokens"]) / 1_000_000
        charged = meta["provider_reported_cost_usd"]
        if charged is None:
            charged = meta["estimated_cost_usd"]
        if charged is not None:
            self._accounted_cost += charged - reserve
        try:
            choice = payload["choices"][0]
            text = choice["message"]["content"]
            if not isinstance(text, str) or choice.get("finish_reason") != "stop" or choice.get("error") or choice["message"].get("tool_calls"):
                raise ValueError("Incomplete or unsupported completion.")
            if meta["returned_model"] != self.config["model"]:
                raise ValueError("Returned model does not match the frozen model.")
        except (KeyError, IndexError, TypeError, ValueError):
            raise ClassificationError("API_RESPONSE_ERROR", "Provider completion was not usable.", calls, metadata=meta) from None
        # Preserve a bounded actual model reply for malformed-output analysis,
        # while defensively redacting the credential if ever echoed by a server.
        redacted = text.replace(self._key, "[REDACTED]")
        meta["model_reply"] = redacted[:4096]
        meta["model_reply_truncated"] = len(redacted) > 4096
        return ClassificationAttempt(redacted, api_calls=calls, metadata=meta)

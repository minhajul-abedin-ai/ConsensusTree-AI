"""Call-count limiter and local request estimates. NOT provider billed token counts."""
from __future__ import annotations
import time
import json
from pathlib import Path

from .providers import ProviderError


def load_pricing(path: str | Path) -> dict:
    """Load explicitly supplied USD per-million-token rates, not live pricing.

    Format: {"openai:gpt-example": {"input_per_million_usd": 1.0,
                                  "output_per_million_usd": 4.0}}.
    """
    rates = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rates, dict):
        raise ValueError("Pricing file must be a JSON mapping")
    for model, rate in rates.items():
        if not isinstance(model, str) or not isinstance(rate, dict):
            raise ValueError("Invalid pricing entry")
        if set(rate) != {"input_per_million_usd", "output_per_million_usd"}:
            raise ValueError("Prices must include input/output rates only")
        if any(type(v) not in (float, int) or not (0 <= v <= 100000) for v in rate.values()):
            raise ValueError("Invalid pricing rate")
    return rates


class MeteredClient:
    def __init__(self, wrapped, max_calls: int = 4, pricing: dict | None = None):
        if not 1 <= max_calls <= 100:
            raise ValueError("max_calls must be 1..100")
        self.wrapped = wrapped
        self.max_calls = max_calls
        self.calls = []
        self.pricing = pricing or {}

    def complete(self, spec, system, user):
        if len(self.calls) >= self.max_calls:
            raise ProviderError(f"Request budget reached: {self.max_calls} calls")
        entry = {"model": str(spec), "input_characters": len(system) + len(user),
                 "estimated_input_tokens": (len(system) + len(user) + 3) // 4,
                 "duration_seconds": 0, "success": False}
        self.calls.append(entry)
        started = time.monotonic()
        try:
            out = self.wrapped.complete(spec, system, user)
            entry["success"] = True
            entry["output_characters"] = len(out)
            usage = getattr(self.wrapped, "last_usage", None)
            if isinstance(usage, dict) and usage.get("source") == "provider_reported":
                entry["provider_usage"] = dict(usage)
                rates = self.pricing.get(str(spec))
                if rates is not None:
                    entry["estimated_cost_usd"] = round((
                        usage["input_tokens"] * rates["input_per_million_usd"] +
                        usage["output_tokens"] * rates["output_per_million_usd"]
                    ) / 1_000_000, 8)
                    entry["pricing_source"] = "user_supplied_rates_not_invoice"
            return out
        finally:
            entry["duration_seconds"] = round(time.monotonic() - started, 3)

    def usage(self):
        reported = [x["provider_usage"] for x in self.calls if "provider_usage" in x]
        priced = [x["estimated_cost_usd"] for x in self.calls if "estimated_cost_usd" in x]
        return {"api_calls": len(self.calls),
                "provider_reported_calls": len(reported),
                "provider_reported_input_tokens": sum(x["input_tokens"] for x in reported),
                "provider_reported_output_tokens": sum(x["output_tokens"] for x in reported),
                "priced_calls": len(priced),
                "estimated_cost_usd": round(sum(priced), 8) if priced else None,
                "actual_billed_cost_verified": False,
                "estimated_input_tokens": sum(c["estimated_input_tokens"] for c in self.calls),
                "estimated_not_billed": True,
                "model_calls": self.calls}

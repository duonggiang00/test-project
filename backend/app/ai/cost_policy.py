"""Estimated per-call cost for AI audit metadata (AI-003).

`ERROR_AND_AUDIT_CONTRACTS.md` §2.4 lists `estimated_cost` among the AI audit
metadata fields, and ADR-0006 requires cost in the audit record. This
codebase has no pricing table, and inventing one would make the audit trail
dishonest: a hardcoded rate would look authoritative while being a guess
that silently goes stale every time a provider reprices.

So cost is derived from *configuration* or it is not derived at all:

- `Settings.AI_TOKEN_PRICING` holds a JSON object mapping a model id to its
  per-1000-token rates. When the calling model has an entry, cost is
  computed exactly from the provider-reported token counts.
- When it is unset (the default), or has no entry for this model, or the
  provider did not report token usage, `estimate_cost` returns `None` and
  the audit event records `"estimated_cost": null`. The token counts are
  still recorded, so the cost can be reconstructed later from an approved
  price list without re-running anything.

`null` is written explicitly rather than omitting the key: an absent field
is ambiguous between "not applicable" and "not implemented", whereas an
explicit null paired with real token counts says precisely what happened.

Rates and results are `Decimal`, never `float` -- money-shaped values must
not accumulate binary rounding error -- and the result is serialized as a
decimal *string*, matching §2.4's `"estimated_cost": "0.0123"`.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from functools import lru_cache

from app.core.config import Settings, settings as default_settings

# Six decimal places: a single low-volume call against a cheap model can cost
# well under a cent, and truncating to four would round a real cost to
# "0.0000" -- which reads as free rather than as small.
COST_EXPONENT = Decimal("0.000001")

_INPUT_RATE_KEY = "input_per_1k_usd"
_OUTPUT_RATE_KEY = "output_per_1k_usd"


class InvalidTokenPricingError(ValueError):
    """Raised when `AI_TOKEN_PRICING` is present but not usable.

    Deliberately loud rather than silently falling back to "no pricing": a
    malformed price list is an operator mistake, and quietly recording every
    cost as null would hide it indefinitely.
    """


def _parse_rate(raw: object, *, model: str, key: str) -> Decimal:
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
        raise InvalidTokenPricingError(
            f"AI_TOKEN_PRICING[{model!r}][{key!r}] must be a decimal string"
        )
    try:
        rate = Decimal(str(raw))
    except InvalidOperation as exc:
        raise InvalidTokenPricingError(
            f"AI_TOKEN_PRICING[{model!r}][{key!r}] is not a valid decimal"
        ) from exc
    if not rate.is_finite() or rate < 0:
        raise InvalidTokenPricingError(
            f"AI_TOKEN_PRICING[{model!r}][{key!r}] must be finite and non-negative"
        )
    return rate


def parse_token_pricing(raw: str) -> dict[str, tuple[Decimal, Decimal]]:
    """Parse the configured price list into `{model: (input, output)}`."""
    if not raw.strip():
        return {}
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidTokenPricingError(
            "AI_TOKEN_PRICING must be a JSON object"
        ) from exc
    if not isinstance(document, dict):
        raise InvalidTokenPricingError("AI_TOKEN_PRICING must be a JSON object")

    parsed: dict[str, tuple[Decimal, Decimal]] = {}
    for model, rates in document.items():
        if not isinstance(model, str) or not model:
            raise InvalidTokenPricingError(
                "AI_TOKEN_PRICING keys must be non-empty model identifiers"
            )
        if not isinstance(rates, dict):
            raise InvalidTokenPricingError(
                f"AI_TOKEN_PRICING[{model!r}] must be an object with "
                f"{_INPUT_RATE_KEY!r} and {_OUTPUT_RATE_KEY!r}"
            )
        missing = {_INPUT_RATE_KEY, _OUTPUT_RATE_KEY} - set(rates)
        if missing:
            raise InvalidTokenPricingError(
                f"AI_TOKEN_PRICING[{model!r}] is missing {sorted(missing)!r}"
            )
        parsed[model] = (
            _parse_rate(rates[_INPUT_RATE_KEY], model=model, key=_INPUT_RATE_KEY),
            _parse_rate(rates[_OUTPUT_RATE_KEY], model=model, key=_OUTPUT_RATE_KEY),
        )
    return parsed


@lru_cache(maxsize=8)
def _cached_pricing(raw: str) -> dict[str, tuple[Decimal, Decimal]]:
    return parse_token_pricing(raw)


def estimate_cost(
    *,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
    settings_obj: Settings | None = None,
) -> str | None:
    """Estimated USD cost for one call, or `None` when it is not knowable.

    Returns `None` -- never a fabricated number -- when no rate is
    configured for `model` or when the provider reported no token usage.
    """
    resolved_settings = settings_obj if settings_obj is not None else default_settings
    pricing = _cached_pricing(resolved_settings.AI_TOKEN_PRICING)
    rates = pricing.get(model)
    if rates is None:
        return None
    if input_tokens is None and output_tokens is None:
        return None

    input_rate, output_rate = rates
    total = (
        Decimal(input_tokens or 0) / Decimal(1000) * input_rate
        + Decimal(output_tokens or 0) / Decimal(1000) * output_rate
    )
    return str(total.quantize(COST_EXPONENT))

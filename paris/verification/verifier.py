"""Critical-field verification (directive 22).

Runs independent checks over an assembled prop and its provenance. Produces a
report with an overall status: VERIFIED (safe to trust), WAIT (an imminent datum
is missing/uncertain), or NO BET (a critical field is absent or conflicting).
The pipeline consumes ``prop.verified`` — this sets it honestly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import get_settings
from ..contracts import Prop
from ..providers.base import ProviderResult


@dataclass
class VerificationReport:
    status: str                      # VERIFIED / WAIT / NO BET
    checks: dict[str, bool] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    @property
    def verified(self) -> bool:
        return self.status == "VERIFIED"


def verify_prop(
    prop: Prop,
    *,
    market_result: ProviderResult | None = None,
    entity_confirmed: bool | None = None,
) -> VerificationReport:
    settings = get_settings()
    checks: dict[str, bool] = {}
    reasons: list[str] = []

    # entity identity (directive 22) — must be positively confirmed upstream
    checks["entity_identity"] = bool(entity_confirmed)
    if entity_confirmed is False:
        reasons.append("player/event identity could not be confirmed")

    # data sufficiency: a real per-90 rate and at least one form window
    has_rate = prop.base_rate_per90 is not None or prop.per_game_rate is not None
    checks["data_sufficient"] = has_rate and bool(prop.form)
    if not checks["data_sufficient"]:
        reasons.append("insufficient real history to derive a rate / form")

    # market presence + freshness (directive 13)
    checks["market_present"] = prop.market_line is not None and prop.market_line.line is not None
    fresh = True
    if market_result is not None:
        fresh = not market_result.is_stale(settings.market_freshness_seconds)
        checks["market_fresh"] = fresh
        if not fresh:
            reasons.append(
                f"market data stale (> {settings.market_freshness_seconds}s old)"
            )

    # opportunity/role certainty
    cert = (prop.opportunity.certainty.upper() if prop.opportunity else "D")
    checks["role_certain"] = cert in ("A", "B")

    # decision
    critical_missing = not (checks["data_sufficient"] and checks["market_present"])
    identity_bad = entity_confirmed is False
    if critical_missing or identity_bad:
        return VerificationReport("NO BET", checks, reasons)
    if not fresh or not checks["role_certain"] or entity_confirmed is None:
        # an imminent/uncertain datum → WAIT rather than trust
        if not checks["role_certain"]:
            reasons.append(f"role/opportunity certainty {cert} — await confirmation")
        if entity_confirmed is None:
            reasons.append("entity not independently confirmed")
        return VerificationReport("WAIT", checks, reasons)
    return VerificationReport("VERIFIED", checks, reasons)

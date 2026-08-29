"""Bounded analysis graph over real, derived data (directive 20).

    market + logs + opponent stats
        → ASSEMBLE (derive features)
        → VERIFY (critical fields)
        → set prop.verified honestly
        → QUANT PIPELINE (projection → distribution → market math → gate)
        → DECISION (+ provenance + verification)

This is the convergence point of the fan-out. It computes nothing itself — it
sequences the real feature engines, the verifier and the existing quant engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .assemble import assemble_prop
from .contracts import MarketLine
from .features import GameLog
from .pipeline import Analysis, analyze_prop
from .providers.base import ProviderResult
from .verification import VerificationReport, verify_prop


@dataclass
class OrchestratedAnalysis:
    # analysis is None when the model could not run because required real data
    # was missing — the decision then lives in ``verification`` (NO BET / WAIT).
    analysis: Analysis | None
    verification: VerificationReport
    derivation: list[str] = field(default_factory=list)
    data_gaps: list[str] = field(default_factory=list)
    market_provenance: dict | None = None

    @property
    def decision(self) -> str:
        return self.analysis.decision if self.analysis is not None else self.verification.status


def analyze_market(
    *,
    subject: str,
    market: str,
    side: str,
    market_line: MarketLine,
    logs: list[GameLog],
    distribution: str = "auto",
    opponent_allowed_per_game: float | None = None,
    league_avg_per_game: float | None = None,
    lineup_confirmed_start: bool | None = None,
    injured: bool | None = None,
    entity_confirmed: bool | None = None,
    market_result: ProviderResult | None = None,
    sources: list[str] | None = None,
) -> OrchestratedAnalysis:
    assembled = assemble_prop(
        subject=subject, market=market, side=side, market_line=market_line,
        logs=logs, distribution=distribution,
        opponent_allowed_per_game=opponent_allowed_per_game,
        league_avg_per_game=league_avg_per_game,
        lineup_confirmed_start=lineup_confirmed_start, injured=injured,
        sources=sources,
    )
    report = verify_prop(
        assembled.prop, market_result=market_result, entity_confirmed=entity_confirmed
    )
    # honest verification flag feeds the Quality Gate
    assembled.prop.verified = report.verified
    if report.reasons:
        assembled.prop.reasons_against = list(
            dict.fromkeys(assembled.prop.reasons_against + report.reasons)
        )

    # The projection engine refuses to invent a rate (directive: never fabricate).
    # With no real rate there is no model — the decision is the verifier's.
    can_model = (
        assembled.prop.base_rate_per90 is not None
        or assembled.prop.per_game_rate is not None
    )
    analysis = analyze_prop(assembled.prop) if can_model else None

    prov = None
    if market_result is not None:
        p = market_result.provenance
        prov = {
            "provider": p.provider, "endpoint": p.endpoint,
            "retrieved_at": p.retrieved_at, "source_timestamp": p.source_timestamp,
            "age_seconds": market_result.age_seconds(),
        }

    return OrchestratedAnalysis(
        analysis=analysis,
        verification=report,
        derivation=assembled.reasons,
        data_gaps=assembled.data_gaps,
        market_provenance=prov,
    )

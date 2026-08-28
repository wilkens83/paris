"""Structured output contracts (spec section 7).

Every node returns a typed object the next node can consume. A vague paragraph
must never be handed to a quantitative engine. These dataclasses are the
contracts; ``from_dict`` builders let a verified-data provider (a JSON file, an
API, a human) populate them, keeping the anti-hallucination rule (spec 64):
the code never fabricates a stat, injury, lineup or price.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# --------------------------------------------------------------------------- #
# Event resolution (spec 4.2)
# --------------------------------------------------------------------------- #
@dataclass
class Event:
    sport: str
    competition: str
    home: str
    away: str
    date: str                      # ISO 8601
    venue: str = ""
    kickoff: str = ""              # ISO 8601 timestamp when known

    @property
    def label(self) -> str:
        return f"{self.home} vs {self.away}"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Event":
        return cls(
            sport=d["sport"],
            competition=d.get("competition", ""),
            home=d["home"],
            away=d["away"],
            date=d.get("date", ""),
            venue=d.get("venue", ""),
            kickoff=d.get("kickoff", ""),
        )


# --------------------------------------------------------------------------- #
# Recent-form windows (spec 19)
# --------------------------------------------------------------------------- #
@dataclass
class FormWindow:
    window: str                    # "L5", "L10", "L20", "Season"
    mean: float
    median: float | None = None
    stdev: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    hit_rate_over: float | None = None   # historical rate above the current line

    @property
    def variance(self) -> float | None:
        return self.stdev * self.stdev if self.stdev is not None else None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FormWindow":
        return cls(
            window=d["window"],
            mean=d["mean"],
            median=d.get("median"),
            stdev=d.get("stdev"),
            minimum=d.get("min"),
            maximum=d.get("max"),
            hit_rate_over=d.get("hit_rate_over"),
        )


# --------------------------------------------------------------------------- #
# Opportunity gate (spec 4.8 / 35) — the "how much chance to produce" layer
# --------------------------------------------------------------------------- #
@dataclass
class Opportunity:
    """Projected volume of chances before production is modelled.

    ``expected`` is the sport-appropriate opportunity unit: minutes (football),
    minutes/usage (NBA), plate appearances (MLB hitter), innings (MLB pitcher),
    snaps/routes (NFL), TOI (NHL) ...
    """

    metric: str                    # e.g. "minutes", "plate_appearances"
    expected: float
    low: float | None = None       # plausible interval
    high: float | None = None
    certainty: str = "C"           # lineup-certainty grade A/B/C/D (spec 37)
    starter_prob: float | None = None
    notes: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Opportunity":
        return cls(
            metric=d.get("metric", "opportunity"),
            expected=d["expected"],
            low=d.get("low"),
            high=d.get("high"),
            certainty=d.get("certainty", "C"),
            starter_prob=d.get("starter_prob"),
            notes=d.get("notes", ""),
        )


# --------------------------------------------------------------------------- #
# A single market / prop to analyse
# --------------------------------------------------------------------------- #
@dataclass
class MarketLine:
    """One line offered by the market (spec 4.10)."""

    line: float
    over_odds: float | None = None       # American; None for pick'em
    under_odds: float | None = None
    book: str = ""
    timestamp: str = ""
    payout_multiplier: float | None = None   # pick'em entry payout when known

    @property
    def is_pickem(self) -> bool:
        return self.over_odds is None and self.under_odds is None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MarketLine":
        return cls(
            line=d["line"],
            over_odds=d.get("over_odds"),
            under_odds=d.get("under_odds"),
            book=d.get("book", ""),
            timestamp=d.get("timestamp", ""),
            payout_multiplier=d.get("payout_multiplier"),
        )


@dataclass
class Prop:
    """A market request: the subject, the stat, the line, the chosen side.

    ``model`` carries the verified numbers the projection engine needs. Nothing
    here is invented — the provider supplies it, flagged with sources.
    """

    subject: str                   # player or team name
    market: str                    # "shots", "shots_on_target", "passes", ...
    side: str                      # "over"/"more" or "under"/"less"
    market_line: MarketLine
    distribution: str = "auto"     # poisson / negbin / normal / auto
    base_rate_per90: float | None = None   # long-term rate per 90' (football)
    per_game_rate: float | None = None     # long-term rate per game (other sports)
    form: list[FormWindow] = field(default_factory=list)
    opportunity: Opportunity | None = None
    matchup_multiplier: float = 1.0        # >1 favourable, <1 suppressive (spec 40)
    matchup_note: str = ""
    variance_hint: float | None = None     # observed variance for the count law
    verified: bool = False                 # did a verifier PASS the critical data?
    sources: list[str] = field(default_factory=list)
    # optional qualitative adversarial inputs (spec 29)
    reasons_for: list[str] = field(default_factory=list)
    reasons_against: list[str] = field(default_factory=list)
    invalidation: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Prop":
        return cls(
            subject=d["subject"],
            market=d["market"],
            side=d.get("side", "over"),
            market_line=MarketLine.from_dict(d["market_line"]),
            distribution=d.get("distribution", "auto"),
            base_rate_per90=d.get("base_rate_per90"),
            per_game_rate=d.get("per_game_rate"),
            form=[FormWindow.from_dict(f) for f in d.get("form", [])],
            opportunity=Opportunity.from_dict(d["opportunity"]) if d.get("opportunity") else None,
            matchup_multiplier=d.get("matchup_multiplier", 1.0),
            matchup_note=d.get("matchup_note", ""),
            variance_hint=d.get("variance_hint"),
            verified=d.get("verified", False),
            sources=list(d.get("sources", [])),
            reasons_for=list(d.get("reasons_for", [])),
            reasons_against=list(d.get("reasons_against", [])),
            invalidation=d.get("invalidation", ""),
        )


@dataclass
class MatchRequest:
    """The MODE B input (spec 15): a match plus the props to screen."""

    event: Event
    props: list[Prop]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MatchRequest":
        return cls(
            event=Event.from_dict(d["event"]),
            props=[Prop.from_dict(p) for p in d.get("props", [])],
        )

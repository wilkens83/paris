# paris — Système Maître · Analyste Quantitatif de Paris Sportifs

A disciplined **sports-betting decision-support system**, built from the master
spec in `Systeme_Maitre_...md`. It is deliberately *not* a pick generator. Its
job is to turn a **match analysis** request into ranked, gated, honestly-priced
decisions — and it is happy to answer **NO BET / WAIT** when the edge is not
robust (spec §0).

> The core use case, as requested: **ask for a match analysis.**
> Give it a match + the props to screen, it runs the pipeline and prints a
> ranked board.

```
python -m paris demo                       # run the bundled Real Madrid vs Barcelona example
python -m paris analyze path/to/match.json # analyse your own verified match file
python -m paris analyze                     # interactive: it asks which match to analyze
```

## What it implements

The spec describes an **agents + loops + graphs** architecture. This repo
implements the deterministic backbone of that architecture as testable Python —
the parts the spec insists must be *quantitative and never invented by the LLM*
(§4.11, §4.12, §64):

| Spec section | Module |
|---|---|
| §7 structured output contracts | `paris/contracts.py` |
| §26 sportsbook market math (odds, vig, fair odds, edge, EV) | `paris/engines/market_math.py` |
| §21–24 distributions → P(Over)/P(Under) (Poisson, Neg-Binomial, Normal, push handling) | `paris/engines/distributions.py` |
| §27 PrizePicks / pick'em math | `paris/engines/prizepicks.py` |
| §21, §28, §35 model engine + sensitivity + minutes gate | `paris/engines/projection.py` |
| §5, §28–33 single-market graph, Quality Gate, grade, decision | `paris/pipeline.py` |
| §15 MODE B, §62, §66 match-analysis orchestrator + ranked board | `paris/match_analysis.py` |
| §60–62 report rendering | `paris/report.py` |
| §64 anti-hallucination data boundary | `paris/providers/` |
| UI plan §31 normalized analysis record | `paris/serialize.py` |
| UI plan §5–8/37 UI input → contracts bridge | `paris/ui_bridge.py` |
| UI plan §18–19 SQLite persistence + audit | `paris/storage/` |
| UI plan §20 calibration / Brier / ROI / CLV | `paris/metrics.py` |
| UI plan §3–20 Streamlit analyst workstation | `app/` |

## The decision chain (§2)

```
VERIFIED DATA → PROJECTION → DISTRIBUTION → PROBABILITY
   → MARKET MATH → EDGE → EV → SENSITIVITY → ADVERSARIAL
   → QUALITY GATE → GRADE → DECISION
```

Priority order is enforced: **Data Quality > Projection > Probability > Price >
EV > Bet.** A prop with a great edge but unverified data or an uncertain role is
gated to NO BET / WAIT, never promoted.

## The anti-hallucination boundary (§64)

The engines **never invent a stat, an injury, a lineup, or a price.** The only
component allowed to supply numbers is a *provider*. The shipped `FileProvider`
reads a JSON document that a human analyst — or an upstream Research + Verifier
stage — has filled with **verified, sourced** data. Everything downstream is
pure math on those inputs.

A prop is only eligible for a real bet when `verified: true` and its
opportunity/role certainty is `A` or `B` (§30, §37). The bundled example uses
clearly-labelled **illustrative sample numbers** — not live odds or stats.

## Match input format

A match file is `{ "event": {...}, "props": [ ... ] }`. Each prop carries the
verified numbers the projection needs:

```jsonc
{
  "subject": "Vinicius Jr",
  "market": "shots",
  "side": "over",
  "distribution": "poisson",          // poisson | negbin | normal | auto
  "base_rate_per90": 3.2,             // long-term rate (football per-90)
  "market_line": { "line": 2.5, "over_odds": -130, "under_odds": 110 },
  "form": [ { "window": "L10", "mean": 3.4, "stdev": 1.6 } ],
  "opportunity": { "metric": "minutes", "expected": 85, "certainty": "B" },
  "matchup_multiplier": 1.05,         // >1 favourable, <1 suppressive
  "verified": true,
  "sources": ["official league stats", "probable XI multi-source"]
}
```

For pick'em (PrizePicks) props, omit `over_odds`/`under_odds` and optionally give
a `payout_multiplier`; the pick'em math (§27) is used instead of sportsbook EV.

See `examples/real_madrid_vs_barcelona.json` for a full six-prop match.

## How the projection works (transparent, §21)

```
mu = base_rate  ×  opportunity_scale  ×  form_factor  ×  matchup_multiplier
```

- **base_rate** — the verified long-term rate (per-90 for football, per-game otherwise).
- **opportunity_scale** — football minutes gate: `expected_minutes / 90` (§35).
- **form_factor** — recent form only *bends* the base rate (weight 0.35); a hit
  rate is never treated as a probability (§1).
- **matchup_multiplier** — the verified matchup effect on *this* market (§40).

Each step is recorded as a driver string so the report can explain what pushes
the number up or down (the "AI Analyzer", §16.8).

## Analyst workstation (Streamlit UI)

A no-JSON, no-CLI interface for analysts, built directly on the engine (it never
recomputes numbers — plan §2/§39). See `docs/PARIS_UI_plan.md` for the full plan.

```
pip install -e '.[app]'                # streamlit + pandas + plotly
streamlit run app/Home.py
```

Pages:

| Page | What it does |
|---|---|
| **Home** | dashboard — saved-analysis counts, average model edge |
| **Match Analyzer** | build an event + props (with a recent-form table editor), click **ANALYZE MATCH**, read the ranked board with per-prop Quality-Gate, sensitivity chart and adversarial risks; save to SQLite |
| **PrizePicks** | pick'em props led by P(MORE)/P(LESS); manual builder or JSON import |
| **Edge Finder** | filter & rank every saved candidate by decision quality (PASS → certainty → edge → EV → grade), never EV alone |
| **Results** | resolve analyses after the match; ROI / CLV / hit rate |
| **Model Health** | calibration buckets, Brier score, log loss (spec 25) |

`WAIT` and `NO BET` are first-class outcomes in the UI, and **historical hit rate
is always shown separately from model probability** (plan §7/§14).

The **SQLite persistence layer** (`paris/storage/`) saves the normalized analysis
record (`paris/serialize.py`) plus post-event audit fields, and
`paris/metrics.py` computes calibration/Brier/log-loss/ROI/CLV over resolved rows.

## Install / develop

```
pip install -e .            # exposes the `paris` console command
pip install -e '.[dev]'     # + pytest
pip install -e '.[app]'     # + streamlit UI deps
python -m pytest -q         # 37 tests, deterministic, no network
```

## Scope & honesty

This is the **quantitative + orchestration backbone**. Live data acquisition
(the Research / Player-Data / Market agents of §4) is intentionally left as the
provider boundary: real odds, lineups and injuries must be fetched and
independently verified before entering the pipeline. The system is designed so
that an incomplete-but-honest analysis (NO BET) always beats an invented one
(§64.19).

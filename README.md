# PARIS — Live Sports-Betting Analytics Platform

> **PARIS is a production-oriented sports-betting analytics and decision-support
> platform that ingests real sports data, real market data, real lineups/injuries,
> historical game logs, and live updates, then runs a quantitative analysis and
> verification pipeline.**

It is **not** a prototype, demo, sample app, or manual data-entry tool. The
normal workflow is *select a real event → load real props → derive features →
verify → model → edge/EV → decision*. The quantitative engine is disciplined: it
answers **NO BET / WAIT** whenever the edge is not robust or the data is not real
and verified.

---

## PRODUCTION LIVE-DATA POLICY

This is a hard product contract, enforced in code:

- **No demo data in normal runtime.** There is no bundled demo match, no
  hard-coded fixtures, no fabricated odds, no sample stats fallback.
- **No silent fallback.** If a required live source is missing, the system shows
  `DATA SOURCE NOT CONFIGURED` (with the exact env var) or
  `WAIT — REQUIRED LIVE DATA IS NOT AVAILABLE`, and **stops the affected
  analysis** — it never substitutes fake data to keep the screen populated.
- **No manual statistical entry as the primary workflow.** Base rates, L5/L10/L20,
  variance, expected minutes, starter probability and matchup are **derived from
  real game logs**, never typed. Manual entry survives only in a clearly-labelled
  *Advanced / Developer Override* that is marked non-production.
- **Real live/historical providers are required** for the live workflow.
- **Test/sample fixtures live only under `tests/`** and are never rendered as
  live data.
- **The frontend never recomputes betting math** — all numbers come from the
  `paris` engine.

If real data is unavailable, PARIS says so explicitly and stops. Honesty over a
populated-but-fake screen.

---

## Architecture

```
Real providers        → API-Football (fixtures/teams/players/stats/lineups/injuries)
                         SportsGameOdds (events/props/lines/prices)
        ↓
Normalization + provenance   (paris/providers, paris/features/models.GameLog)
        ↓
Automatic feature engines    (paris/features: historical, opportunity, matchup)
        ↓
Assemble a fully-derived Prop (paris/assemble)
        ↓
Independent verification      (paris/verification) — critical conflict → WAIT/NO BET
        ↓
Quantitative engine           (paris/pipeline + paris/engines) — projection →
        ↓                       distribution → market math → sensitivity → gate
Decision + provenance         (paris/orchestrator, paris/serialize)
        ↓
FastAPI  (paris/api)   ·   Streamlit workstation (app/, internal/admin)
        ↓
Persistence            SQLite (dev)  →  PostgreSQL (production target)
```

The production direction is **Next.js → FastAPI → PARIS engine → PostgreSQL →
real providers**. Streamlit remains as an internal/admin tool, not the final
product.

## The decision chain

```
REAL DATA → AUTOMATIC FEATURES → VERIFICATION → PROJECTION → DISTRIBUTION
   → PROBABILITY → MARKET MATH → EDGE → EV → SENSITIVITY → QUALITY GATE → DECISION
```

Priority order is enforced: **Data Quality > Projection > Probability > Price >
EV > Bet.** A prop with a great edge but unverified data or an uncertain role is
gated to NO BET / WAIT, never promoted.

## Configuration

Copy `.env.example` to `.env` and set your keys:

```
API_FOOTBALL_KEY=...          # https://www.api-football.com/
SPORTSGAMEODDS_API_KEY=...    # https://sportsgameodds.com/
DATABASE_URL=...              # PostgreSQL target; unset = SQLite dev
```

Check configuration at any time:

```
python -m paris config
```

With no keys set, the live pages and API endpoints return the honest
`DATA SOURCE NOT CONFIGURED` state and name the missing variable.

## Running

```
pip install -e '.[api]'               # FastAPI backend
uvicorn paris.api:app --reload        # http://localhost:8000/api/v1/...

pip install -e '.[app]'               # internal Streamlit workstation
streamlit run app/Home.py             # Today's Events (live) → Match Center
```

Key API endpoints (real data or explicit unavailable state):

```
GET  /api/v1/config/status
GET  /api/v1/events/today
GET  /api/v1/events/{id}            /lineups  /injuries  /props
GET  /api/v1/players/{id}/history
POST /api/v1/analyze/prop           # derive → verify → model over supplied logs
GET  /api/v1/edge-finder
GET  /api/v1/analyses/{id}
```

## How features are derived (no manual entry)

| Model input | Derived from | Module |
|---|---|---|
| L5/L10/L20/Season, per-90 rate, variance, hit rate | real game logs | `paris/features/historical.py` |
| starter prob, expected minutes, P(60/70/75/80/90+) | recent minutes + start history (+ confirmed lineup) | `paris/features/opportunity.py` |
| matchup multiplier | opponent allowed-rate vs league average | `paris/features/matchup.py` |
| the assembled `Prop` | all of the above + real market line | `paris/assemble.py` |

The projection is transparent — `mu = base_rate × opportunity_scale ×
form_factor × matchup` — and every step is recorded so the UI explains *why*,
never asks the user to invent a number.

## Preserved quantitative engine

The math core is unchanged and only ever consumes normalized, derived inputs:

`paris/contracts.py`, `paris/pipeline.py`, `paris/match_analysis.py`,
`paris/engines/{distributions,market_math,prizepicks,projection}.py`,
`paris/serialize.py`, `paris/metrics.py`.

## Verification & honest states

`paris/verification` independently checks entity identity, data sufficiency,
market presence/freshness and role certainty. An unresolved critical conflict
produces **WAIT** or **NO BET**, never a guessed value. The UI/API distinguish
`LOADING / LIVE / STALE / UNAVAILABLE / UNVERIFIED / WAIT / NO BET` and never
render a missing value as a real zero.

## Persistence

`paris/storage/` persists analyses and post-event audit fields. SQLite is the
current dev store; `paris/storage/schema_full.sql` is the **target PostgreSQL
schema** (sports/leagues/teams/players/events, game logs, lineups, injuries,
props, market lines/snapshots, analysis runs, predictions, verifications,
results, closing lines, calibration) with provenance columns on every
externally-sourced row.

## Install / develop

```
pip install -e .            # engine + `paris` developer CLI
pip install -e '.[dev]'     # + pytest
pip install -e '.[api]'     # + FastAPI backend
pip install -e '.[app]'     # + Streamlit internal workstation
pip install -e '.[postgres]'# + SQLAlchemy / psycopg (production DB)
python -m pytest -q         # deterministic tests, no network
```

## Remaining production blockers

- **Live end-to-end requires credentials** (`API_FOOTBALL_KEY`,
  `SPORTSGAMEODDS_API_KEY`) and network egress to those APIs. Without them the
  real fetch paths correctly report `DATA SOURCE NOT CONFIGURED`.
- **Provider→contract normalization** for the exact API-Football / SportsGameOdds
  payload shapes and **PostgreSQL persistence (ORM) for all domains** are the
  next production steps; the derive→verify→model path already runs end-to-end on
  normalized real-shaped logs (`POST /api/v1/analyze/prop`, `paris.orchestrator`).
- **Next.js production frontend** is not yet built (backend live-data path first,
  per plan).

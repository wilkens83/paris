# PARIS — USER INTERFACE & PRODUCT IMPLEMENTATION PLAN
## Transforming the Existing Quantitative Betting Engine into a Usable Bobby’s Bets–Style Application

> ---
>
> # PRODUCTION LIVE-DATA POLICY (authoritative)
>
> **PARIS is a production live-data system, not a prototype, demo, sample app, or
> manual data-entry tool.** This policy overrides any older wording below that
> describes demo workflows, manual statistical entry, or Streamlit/JSON files as
> the intended product.
>
> - **NO DEMO DATA IN NORMAL RUNTIME.** No bundled demo match, no hard-coded
>   fixtures, no fabricated odds, no placeholder model outputs.
> - **NO SAMPLE / MOCK DATA FALLBACK.** Test fixtures live only under `tests/`
>   and are never displayed as live data.
> - **NO SILENT FALLBACK.** A missing source yields `DATA SOURCE NOT CONFIGURED`
>   / `DATA SOURCE UNAVAILABLE` / `WAIT — REQUIRED LIVE DATA IS NOT AVAILABLE`,
>   and the affected analysis stops. Fake data is never substituted.
> - **NO MANUAL STATISTICAL ENTRY AS THE PRIMARY WORKFLOW.** Base rates,
>   L5/L10/L20, variance, expected minutes, starter probability and matchup are
>   derived automatically from real game logs. Manual entry exists only in a
>   clearly-labelled *Advanced / Developer Override* marked non-production.
> - **REAL LIVE/HISTORICAL PROVIDERS ARE REQUIRED** (API-Football / API-Sports,
>   SportsGameOdds or equivalent). Credentials come from environment variables.
> - **The frontend never recomputes betting math** — every number comes from the
>   `paris` quantitative engine.
> - **The production direction is Next.js → FastAPI → PARIS engine → PostgreSQL →
>   real providers.** Streamlit is an internal/admin tool, not the final product.
>
> Sections further down that predate this policy are retained for historical
> design context only; where they conflict with this policy, this policy wins.
>
> ---



> Repository: `wilkens83/paris`  
> Current engine: deterministic Python quantitative betting pipeline  
> Goal: add a practical analyst interface first, then evolve toward a production web application.

---

# 1. Executive Summary

The repository already contains the core quantitative engine. The priority is **not to rewrite the model**. The priority is to make the existing engine usable through an interface.

Recommended path:

```text
Existing Python Engine
        ↓
Streamlit Analyst UI
        ↓
SQLite Persistence
        ↓
Live Data Providers
        ↓
Independent Verification
        ↓
Agent Graph + Loops
        ↓
FastAPI Backend
        ↓
Next.js Production Frontend
        ↓
PostgreSQL + Redis
```

The application must remain a **decision-support system**, not a pick generator.

Core decision chain:

```text
VERIFIED DATA
→ PROJECTION
→ DISTRIBUTION
→ PROBABILITY
→ MARKET MATH
→ EDGE
→ EV
→ SENSITIVITY
→ ADVERSARIAL CHECK
→ QUALITY GATE
→ GRADE
→ DECISION
```

Valid final decisions include:

- STRONG VALUE
- VALUE
- LEAN
- FAIR
- AVOID
- WAIT
- NO BET

---

# 2. Existing Repository Core

Keep the existing engine as the source of truth:

```text
paris/
├── contracts.py
├── pipeline.py
├── match_analysis.py
├── report.py
├── cli.py
├── engines/
│   ├── distributions.py
│   ├── market_math.py
│   ├── prizepicks.py
│   └── projection.py
└── providers/
    └── file_provider.py
```

Do not duplicate this logic in the frontend.

The UI should construct existing contracts such as:

- `Event`
- `MarketLine`
- `FormWindow`
- `Opportunity`
- `Prop`
- `MatchRequest`

Then call the current functions such as:

```python
analyze_prop(...)
analyze_match(...)
```

---

# 3. Phase 1 — Streamlit Analyst Workstation

Streamlit should be the first interface because the engine is already Python.

Benefits:

- direct calls into the existing code;
- fast implementation;
- no REST API required initially;
- no TypeScript required initially;
- easy validation of the betting workflow;
- ideal for analyst use.

Recommended additions:

```text
app/
├── Home.py
├── pages/
│   ├── 1_Match_Analyzer.py
│   ├── 2_Prop_Finder.py
│   ├── 3_Edge_Finder.py
│   ├── 4_PrizePicks.py
│   ├── 5_Results.py
│   └── 6_Model_Health.py
├── components/
│   ├── board.py
│   ├── prop_card.py
│   ├── quality_gate.py
│   ├── sensitivity.py
│   ├── market_table.py
│   └── charts.py
└── state.py
```

Initial dependencies:

```toml
dependencies = [
    "streamlit>=1.37",
    "pandas>=2.0",
    "plotly>=5.0",
]
```

---

# 4. Dashboard

Navigation:

```text
PARIS

Dashboard
Match Analyzer
Prop Finder
Edge Finder
PrizePicks
Results
Model Health
Settings
```

Top filters:

```text
Sport
League
Date
Verified only
Minimum grade
Minimum edge
```

Summary metrics:

```text
Props analyzed
Value candidates
WAIT candidates
NO BET
Average model edge
Market movers
```

Example:

```text
2,438 Props
17 Value Candidates
9 Market Movers
6 WAIT
21 NO BET
```

---

# 5. Match Analyzer

This should be the first fully functional page.

## Event Inputs

```text
Sport
Competition
Home Team
Away Team
Date
Kickoff
Venue
```

These fields should map directly to the existing `Event` contract.

Primary action:

```text
ANALYZE MATCH
```

---

# 6. Prop Builder

The user should not need to manually write JSON.

For every prop:

```text
Player / Subject
Market
Side
Line
Distribution
Book
Over Odds
Under Odds
Timestamp
```

Model inputs:

```text
Base Rate Per 90
Per Game Rate
Variance Hint
Matchup Multiplier
Matchup Note
```

Opportunity:

```text
Opportunity Metric
Expected Opportunity
Low
High
Certainty A/B/C/D
Starter Probability
Notes
```

Verification:

```text
Verified
Sources
Reasons For
Reasons Against
Invalidation Condition
```

Button:

```text
+ ADD PROP
```

---

# 7. Recent Form Builder

Allow structured input for:

- L5
- L10
- L20
- Season

Recommended table:

| Window | Mean | Median | SD | Min | Max | Historical Hit Rate |
|---|---:|---:|---:|---:|---:|---:|
| L5 | | | | | | |
| L10 | | | | | | |
| L20 | | | | | | |
| Season | | | | | | |

Important UI rule:

> Historical Hit Rate and Model Probability must always be displayed separately.

Never present a 5/5 or 10/10 historical streak as predictive probability.

---

# 8. Match Board Output

After:

```python
board = analyze_match(request)
```

render:

| Rank | Player | Market | Line | Side | Model P | Edge | EV | Grade | Decision |
|---:|---|---|---:|---|---:|---:|---:|---|---|

Group outputs into:

```text
BEST BETS
SECONDARY VALUE
LEANS
WAIT
AVOID
NO BET
```

The UI should use the existing `MatchBoard` categories instead of creating a second ranking system.

---

# 9. Prop Detail View

Each prop should have a detailed card.

## Projection

```text
Projection
Interval Low
Interval High
Distribution
P(Over)
P(Under)
P(Push)
```

## Market

```text
Market Fair Probability
Model Probability
Edge
Fair Odds
Offered Odds
EV
Book
Timestamp
```

## Quality

```text
Verified
Data Sufficient
Line Present
Model Completed
Opportunity Certainty
Uncertainty Estimated
```

---

# 10. Quality Gate Visualization

Example PASS:

```text
QUALITY GATE

✓ Entity Verified
✓ Data Sufficient
✓ Market Line Present
✓ Model Completed
✓ Opportunity Certainty: A
✓ Uncertainty Estimated

STATUS: PASS
```

Example WAIT:

```text
✓ Entity Verified
✓ Data Sufficient
✓ Market Line Present
✓ Model Completed
✗ Opportunity Certainty: C
✓ Uncertainty Estimated

STATUS: WAIT
Reason: official lineup / role confirmation required
```

Example NO BET:

```text
✗ Critical Data Verified
✗ Base Rate Available
✓ Market Line Present

STATUS: NO BET
```

`WAIT` and `NO BET` must remain first-class product outcomes.

---

# 11. Sensitivity Analysis

Visualize the current minutes/opportunity sensitivity.

Example:

| Expected Minutes | P(MORE) |
|---:|---:|
| 70 | 51% |
| 75 | 55% |
| 80 | 59% |
| 85 | 63% |
| 90 | 66% |

Show a chart.

Also show a threshold:

```text
MODEL STOPS BEING VALUE BELOW:
74 expected minutes
```

The same pattern can later be adapted to:

- NBA minutes;
- MLB innings;
- MLB plate appearances;
- NFL routes/snaps;
- NHL TOI.

---

# 12. Adversarial Check

Every recommended candidate should show:

## Why the Model Likes It

- opportunity;
- role;
- matchup;
- pricing;
- projection drivers.

## Why It Can Fail

- substitution risk;
- lineup change;
- matchup suppression;
- market movement;
- variance;
- game script.

## Invalidation Condition

Example:

```text
Invalidate if:
- player does not start;
- expected minutes fall below 74;
- line moves from 3.5 to 4.5.
```

---

# 13. Prop Finder

Purpose:

discover possible candidates before deep analysis.

Columns:

```text
Player
Market
Line
L5
L10
L20
Season
Expected Opportunity
Projection
P(MORE)
P(LESS)
Grade
Decision
```

Filters:

```text
Sport
League
Game
Player
Market
MORE / LESS
Minimum Probability
Minimum Grade
Opportunity Certainty
Verified Only
```

---

# 14. 100% Club

Create a screener inspired by Bobby’s Bets.

Example:

```text
🔥 100% CLUB

Player A
Shots MORE 2.5

L5        5/5    100%
L10       8/10    80%
L20      13/20    65%
Season             59%

Projection: 3.26
P(MORE): 61.8%
Grade: B+
```

Critical rule:

```text
100% L5 HIT RATE
≠
100% MODEL PROBABILITY
```

The 100% Club is a candidate generator only.

---

# 15. Edge Finder

This should become one of the most important pages.

Filters:

```text
Sport
League
Event
Player
Market
Side
Minimum Model Probability
Minimum Edge
Minimum EV
Minimum Grade
Verified Only
Opportunity Certainty
Book
```

Table:

| Rank | Player | Prop | Line | Model P | Market P | Edge | EV | Grade | Decision |
|---:|---|---|---:|---:|---:|---:|---:|---|---|

Recommended sorting hierarchy:

```text
1. Quality Gate PASS
2. Data Quality
3. Opportunity Certainty
4. Edge
5. EV
6. Grade
```

Do not rank only by EV.

---

# 16. PrizePicks Analyzer

The repository already has a PrizePicks / pick’em engine.

Initial page:

```text
PRIZEPICKS ANALYZER

[ Add Prop Manually ]
[ Import JSON ]
```

Future:

```text
[ Upload Screenshot ]
```

Results:

| Player | Market | Line | Projection | P(MORE) | P(LESS) | Grade | Decision |
|---|---|---:|---:|---:|---:|---|---|

Group:

```text
BEST MORE
BEST LESS
WAIT
PASS
```

---

# 17. PrizePicks Card Builder

Future feature:

```text
Select 2-Leg
Select 3-Leg
Select 4-Leg
```

The system should:

- detect correlation;
- avoid naive multiplication of dependent probabilities;
- compare with verified payout rules;
- estimate break-even probability;
- remove low-quality legs;
- prefer shorter higher-quality combinations.

Do not optimize for payout multiplier alone.

---

# 18. Results Persistence

Add an internal persistence layer.

Start with:

```text
SQLite
```

Recommended modules:

```text
paris/storage/
├── __init__.py
├── sqlite.py
└── schema.sql
```

Save pre-match fields:

```text
analysis_id
created_at
sport
event
subject
market
line
side
projection
interval
model_probability
market_probability
edge
fair_odds
offered_odds
ev
grade
decision
model_version
opportunity_expected
opportunity_certainty
verified
sources
```

Post-event fields:

```text
actual_stat
actual_opportunity
result
closing_line
closing_price
clv
projection_error
error_category
```

---

# 19. Results Page

Display:

| Date | Player | Prop | Model P | Grade | Decision | Result | CLV |
|---|---|---|---:|---|---|---|---:|

Summary:

```text
30-Day ROI
Average CLV
Hit Rate
Brier Score
Log Loss
Calibration Error
```

---

# 20. Model Health Page

Calibration table:

| Model Probability | Actual Hit Rate |
|---|---:|
| 50–55% | |
| 55–60% | |
| 60–65% | |
| 65–70% | |
| 70%+ | |

A 70% model bucket winning 58% is evidence of overconfidence.

Track:

```text
Brier Score
Log Loss
ROI
CLV
Calibration Error
Performance by Sport
Performance by Market
Performance by Grade
Performance by Opportunity Certainty
```

---

# 21. Live Data Providers

The current file-provider boundary is the correct architecture.

Expand later into:

```text
paris/providers/
├── base.py
├── file_provider.py
├── official_stats_provider.py
├── odds_provider.py
├── lineup_provider.py
├── injury_provider.py
├── weather_provider.py
└── news_provider.py
```

Providers should return structured data with:

```text
value
source
timestamp
verification_status
```

Quantitative engines should not directly scrape arbitrary websites.

---

# 22. Independent Verification Layer

Add:

```text
paris/verification/
├── correctness.py
├── freshness.py
├── entity.py
├── consistency.py
└── verifier.py
```

Verification questions:

```text
Is this the correct player?
Is this the correct event?
Is the market line current?
Is the source current?
Does a second reliable source contradict it?
```

Critical failures should immediately reject the finding.

---

# 23. Agent Graph

After live providers exist:

```text
REQUEST
  ↓
EVENT RESOLVER
  ↓
 ┌─────────────────────────────────────┐
 ↓              ↓          ↓           ↓
PLAYER DATA   TEAM DATA   MARKET     CONTEXT
 ↓              ↓          ↓           ↓
 └──────────────┴──────────┴───────────┘
                  ↓
             VERIFICATION
                  ↓
            OPPORTUNITY
                  ↓
              MODEL
                  ↓
             MARKET MATH
                  ↓
             SENSITIVITY
                  ↓
             QUALITY GATE
                  ↓
              DECISION
```

Parallelize only genuinely independent jobs.

---

# 24. Loops

## Data Quality Loop

```text
FETCH
→ VERIFY
→ FAIL?
→ TRY ALTERNATIVE SOURCE
→ MAX RETRIES
```

## Market Loop

```text
FETCH MARKET
→ STORE SNAPSHOT
→ COMPARE
→ MATERIAL CHANGE?
→ RECOMPUTE
```

## Lineup Loop

```text
PROBABLE LINEUP
→ INITIAL MODEL
→ OFFICIAL LINEUP
→ MATERIAL CHANGE?
→ RECOMPUTE
```

## Injury Loop

```text
QUESTIONABLE
→ NEW REPORT
→ STATUS CHANGE
→ UPDATE OPPORTUNITY
→ RECOMPUTE
```

Every loop requires:

- measurable check;
- maximum attempts;
- explicit stop condition.

---

# 25. Football-Specific UI

Football should be the first deep sport implementation.

Add fields:

```text
Lineup Status
Formation
Nominal Position
Actual Position
In-Possession Role
Out-of-Possession Role
Side / Zone
Direct Opponent
Set-Piece Role
Penalty Role
Expected Minutes
P(75+)
P(80+)
P(90)
Substitution Risk
```

---

# 26. Football — Passes Panel

For passes:

```text
Projected Team Possession
Opponent Possession
Team Passing Volume
Player Passing Share
Build-Up Structure
Passing Hierarchy
Opponent PPDA
Expected Game Script
```

---

# 27. Football — Shots / SOT Panel

Show:

```text
Expected Shots
Shots in Box
Shots Outside Box
Touches in Box
xG per Shot
Headers
Set Pieces
Penalties
Shot-on-Target Conversion
```

---

# 28. Football — Clearances Panel

Show:

```text
Expected Opponent Crosses
Targeted Side
Expected Box Entries
Long-Ball Volume
Block Height
Defensive Role
Clearance Share
Game Script
```

---

# 29. Production Architecture

After Streamlit is stable:

```text
                         USER
                           │
                           ▼
                  ┌─────────────────┐
                  │     NEXT.JS     │
                  │   TypeScript    │
                  └────────┬────────┘
                           │
                         REST
                           │
                           ▼
                  ┌─────────────────┐
                  │     FASTAPI     │
                  │      Python     │
                  └────────┬────────┘
                           │
                       paris/
                           │
           ┌───────────────┼──────────────┐
           ▼               ▼              ▼
      Quant Engine     Agent Graph    Market Engine
           │               │              │
           └───────────────┼──────────────┘
                           ▼
                      PostgreSQL
                           │
                         Redis
```

---

# 30. FastAPI Endpoints

Future endpoints:

```text
POST /api/v1/analyze/prop
POST /api/v1/analyze/match
GET  /api/v1/analyses/{id}
GET  /api/v1/events
GET  /api/v1/props
GET  /api/v1/edge-finder
GET  /api/v1/results
GET  /api/v1/model-health
```

Analysis progress:

```text
GET /api/v1/analyses/{id}/events
```

using Server-Sent Events.

---

# 31. Normalized Analysis Response

Example:

```json
{
  "analysis_id": "analysis_123",
  "decision": "VALUE",
  "grade": "A",
  "projection": 4.18,
  "interval": [2.1, 6.8],
  "probabilities": {
    "over": 0.628,
    "under": 0.372,
    "push": 0.0
  },
  "market": {
    "fair_probability": 0.541,
    "fair_odds": -169,
    "offered_odds": -115,
    "edge_points": 0.087,
    "ev_per_unit": 0.174
  },
  "quality_gate": {
    "status": "PASS",
    "checks": {
      "entity_verified": true,
      "data_sufficient": true,
      "opportunity_certain": true,
      "uncertainty_estimated": true
    }
  },
  "invalidation": [
    "player does not start",
    "expected minutes below 74",
    "market line moves to 4.5"
  ]
}
```

---

# 32. Production Frontend Pages

Recommended:

```text
frontend/
├── app/
│   ├── dashboard/
│   ├── games/
│   ├── props/
│   ├── edge-finder/
│   ├── market-pulse/
│   ├── analyzer/
│   ├── prizepicks/
│   ├── players/
│   ├── results/
│   ├── model-health/
│   └── settings/
├── components/
│   ├── dashboard/
│   ├── props/
│   ├── analysis/
│   ├── charts/
│   └── ui/
└── lib/
```

Recommended production stack:

| Layer | Technology |
|---|---|
| Frontend | Next.js |
| Language | TypeScript |
| UI | Tailwind CSS |
| Components | shadcn/ui |
| Data Fetching | TanStack Query |
| Charts | Recharts |
| Backend | FastAPI |
| Validation | Pydantic |
| ORM | SQLAlchemy |
| Database | PostgreSQL |
| Cache | Redis |
| Deployment | Docker |

---

# 33. Testing Requirements

Keep the deterministic unit tests.

Add tests for:

```text
UI input → Prop
UI input → MatchRequest
Analysis → correct Quality Gate
Analysis → correct MatchBoard bucket
Sportsbook → correct no-vig edge
Pick’em → correct probability
Opportunity C/D → WAIT
Unverified data → NO BET
```

Later integration tests:

```text
Provider → Verifier → Pipeline
API → Pipeline
Database → Audit
```

---

# 34. Market Freshness

Every market line should include a timestamp.

UI:

```text
Market updated: 8 minutes ago
```

Future configurable freshness thresholds:

```text
Soccer: 15 minutes
NBA: 10 minutes
MLB: 10 minutes
```

If stale:

```text
MARKET DATA STALE
→ WAIT / REFRESH REQUIRED
```

---

# 35. Data Quality Score

Future optional score:

```text
Entity Verification      20
Source Quality            20
Freshness                 15
Opportunity Certainty     20
Sample Quality            15
Market Quality            10
-----------------------------
Total                    100
```

Never confuse this with predictive probability.

---

# 36. Development Roadmap

## V0.1 — Streamlit Skeleton

Build:

```text
Home
Match Analyzer
Prop Form
Analyze Button
Ranked Board
```

Success criterion:

> A user can analyze a match without JSON or CLI usage.

## V0.2 — Prop Detail

Add:

```text
Projection
Probability
Market Math
Quality Gate
Sensitivity
Adversarial Risks
```

Success criterion:

> The user understands why a candidate is VALUE, WAIT, or NO BET.

## V0.3 — PrizePicks

Add:

```text
Manual Card Builder
MORE / LESS Ranking
Correlation Warnings
```

## V0.4 — Persistence

Add:

```text
SQLite
Saved Analyses
Results
Post-Match Audit
```

## V0.5 — Edge Finder

Add:

```text
Filters
Sorting
Saved Candidate Aggregation
```

## V0.6 — Model Health

Add:

```text
Calibration
Brier Score
Log Loss
ROI
CLV
```

## V0.7 — Live Providers

Add:

```text
Stats
Odds
Lineups
Injuries
Weather
```

## V0.8 — Verification Graph

Add:

```text
Correctness
Freshness
Entity Validation
Contradiction Detection
```

## V0.9 — Agent Graph

Add:

```text
Event Resolver
Research Worker
Market Worker
Context Worker
Opportunity Worker
Verifier
Synthesizer
```

## V1.0 — Production Web App

Add:

```text
FastAPI
Next.js
PostgreSQL
Redis
Background Jobs
Authentication if needed
```

---

# 37. Immediate Implementation Tasks

Recommended first tasks:

```text
1. Add Streamlit dependencies
2. Create app/Home.py
3. Create Match Analyzer page
4. Build Event form
5. Build Prop form
6. Build recent-form table editor
7. Convert UI state to MatchRequest
8. Call analyze_match()
9. Render MatchBoard
10. Add Prop Detail
11. Add Quality Gate visualization
12. Add Sensitivity chart
13. Add PrizePicks page
14. Add SQLite persistence
15. Add Results page
```

---

# 38. Final Product Experience

Target workflow:

```text
1. Open PARIS
2. Select Sport
3. Select Match
4. View Props
5. Filter Candidates
6. Click ANALYZE
7. Gather Verified Data
8. Estimate Opportunity
9. Build Projection
10. Generate Distribution
11. Estimate Probability
12. Compare with Market
13. Calculate Edge / EV
14. Run Sensitivity
15. Run Verification
16. Apply Quality Gate
17. Return:
    - Decision
    - Projection
    - Model Probability
    - Market Probability
    - Edge
    - EV
    - Grade
    - Data Quality
    - Risks
    - Invalidation
18. User Makes Final Decision
19. Save Analysis
20. Audit After Event
```

---

# 39. Core Design Rule

The application must never become:

```text
LLM
→ Opinion
→ Pick
```

It must remain:

```text
VERIFIED DATA
→ QUANTITATIVE MODEL
→ PROBABILITY
→ MARKET
→ EDGE
→ QUALITY GATE
→ DECISION
```

Agents may:

- research;
- orchestrate;
- verify;
- explain.

Quantitative engines remain responsible for the numbers.

---

# 40. Final Recommendation

Do not rebuild the repository.

Do not replace the existing Python core.

Do not begin with a complex production frontend.

The correct next step is:

```text
Existing paris Engine
        +
Streamlit Analyst Workstation
```

Then evolve through:

```text
Persistence
→ Live Data
→ Verification
→ Agents
→ FastAPI
→ Next.js
```

This is the shortest and safest path from the current quantitative engine to a professional sports-betting analytics application.

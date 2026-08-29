-- PARIS production database — target PostgreSQL schema (directive 9, 28).
--
-- This is the target normalized schema for the live-data system. The current
-- code persists analyses via the SQLite AnalysisStore (dev); migrating these
-- domains to PostgreSQL (with an ORM) is a tracked production step. Historical
-- provider responses are normalized into these tables so the app does not
-- refetch the same history repeatedly.
--
-- Every externally-sourced row carries provenance columns (directive 28):
--   provider, source_external_id, retrieved_at, source_timestamp,
--   verification_status.

CREATE TABLE IF NOT EXISTS sports (
    id           SERIAL PRIMARY KEY,
    name         TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS leagues (
    id                 SERIAL PRIMARY KEY,
    sport_id           INTEGER REFERENCES sports(id),
    name               TEXT NOT NULL,
    provider           TEXT,
    source_external_id TEXT,
    UNIQUE (provider, source_external_id)
);

CREATE TABLE IF NOT EXISTS teams (
    id                 SERIAL PRIMARY KEY,
    league_id          INTEGER REFERENCES leagues(id),
    name               TEXT NOT NULL,
    provider           TEXT,
    source_external_id TEXT,
    UNIQUE (provider, source_external_id)
);

CREATE TABLE IF NOT EXISTS players (
    id                 SERIAL PRIMARY KEY,
    team_id            INTEGER REFERENCES teams(id),
    name               TEXT NOT NULL,
    position           TEXT,
    provider           TEXT,
    source_external_id TEXT,
    UNIQUE (provider, source_external_id)
);

CREATE TABLE IF NOT EXISTS events (
    id                 SERIAL PRIMARY KEY,
    league_id          INTEGER REFERENCES leagues(id),
    home_team_id       INTEGER REFERENCES teams(id),
    away_team_id       INTEGER REFERENCES teams(id),
    kickoff            TIMESTAMPTZ,
    venue              TEXT,
    status             TEXT,
    provider           TEXT,
    source_external_id TEXT,
    retrieved_at       TIMESTAMPTZ,
    UNIQUE (provider, source_external_id)
);

CREATE TABLE IF NOT EXISTS player_game_logs (
    id                 SERIAL PRIMARY KEY,
    player_id          INTEGER REFERENCES players(id),
    event_id           INTEGER REFERENCES events(id),
    played_on          DATE,
    opponent_team_id   INTEGER REFERENCES teams(id),
    is_home            BOOLEAN,
    started            BOOLEAN,
    minutes            REAL,
    stats              JSONB,            -- {"shots": 3, "sot": 1, "passes": 41, ...}
    provider           TEXT,
    source_external_id TEXT,
    retrieved_at       TIMESTAMPTZ,
    source_timestamp   TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS team_game_logs (
    id                 SERIAL PRIMARY KEY,
    team_id            INTEGER REFERENCES teams(id),
    event_id           INTEGER REFERENCES events(id),
    stats              JSONB,
    allowed            JSONB,            -- per-stat allowed, for matchup features
    provider           TEXT,
    retrieved_at       TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS lineups (
    id                 SERIAL PRIMARY KEY,
    event_id           INTEGER REFERENCES events(id),
    team_id            INTEGER REFERENCES teams(id),
    player_id          INTEGER REFERENCES players(id),
    is_starter         BOOLEAN,
    position           TEXT,
    formation          TEXT,
    is_official        BOOLEAN,
    provider           TEXT,
    retrieved_at       TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS injuries (
    id                 SERIAL PRIMARY KEY,
    player_id          INTEGER REFERENCES players(id),
    event_id           INTEGER REFERENCES events(id),
    status             TEXT,             -- out / doubtful / questionable / available
    reason             TEXT,
    provider           TEXT,
    retrieved_at       TIMESTAMPTZ,
    source_timestamp   TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS player_roles (
    id                 SERIAL PRIMARY KEY,
    player_id          INTEGER REFERENCES players(id),
    event_id           INTEGER REFERENCES events(id),
    nominal_position   TEXT,
    actual_position    TEXT,
    set_piece_role     TEXT,
    penalty_role       TEXT
);

CREATE TABLE IF NOT EXISTS books (
    id                 SERIAL PRIMARY KEY,
    name               TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS props (
    id                 SERIAL PRIMARY KEY,
    event_id           INTEGER REFERENCES events(id),
    player_id          INTEGER REFERENCES players(id),
    market             TEXT NOT NULL,
    provider           TEXT,
    source_external_id TEXT
);

CREATE TABLE IF NOT EXISTS market_lines (
    id                 SERIAL PRIMARY KEY,
    prop_id            INTEGER REFERENCES props(id),
    book_id            INTEGER REFERENCES books(id),
    line               REAL,
    over_price         REAL,
    under_price        REAL,
    is_current         BOOLEAN DEFAULT TRUE,
    provider           TEXT,
    source_timestamp   TIMESTAMPTZ,
    retrieved_at       TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS market_snapshots (
    id                 SERIAL PRIMARY KEY,
    prop_id            INTEGER REFERENCES props(id),
    book_id            INTEGER REFERENCES books(id),
    line               REAL,
    over_price         REAL,
    under_price        REAL,
    captured_at        TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id                 TEXT PRIMARY KEY,      -- analysis_id
    event_id           INTEGER REFERENCES events(id),
    prop_id            INTEGER REFERENCES props(id),
    created_at         TIMESTAMPTZ,
    model_version      TEXT,
    decision           TEXT,
    grade              TEXT
);

CREATE TABLE IF NOT EXISTS analysis_inputs (
    id                 SERIAL PRIMARY KEY,
    analysis_id        TEXT REFERENCES analysis_runs(id),
    key                TEXT,
    value              JSONB,
    provider           TEXT,
    source_timestamp   TIMESTAMPTZ,
    verification_status TEXT
);

CREATE TABLE IF NOT EXISTS model_predictions (
    id                 SERIAL PRIMARY KEY,
    analysis_id        TEXT REFERENCES analysis_runs(id),
    projection         REAL,
    interval_low       REAL,
    interval_high      REAL,
    distribution       TEXT,
    model_probability  REAL,
    market_probability REAL,
    edge               REAL,
    ev                 REAL
);

CREATE TABLE IF NOT EXISTS quality_gate_results (
    id                 SERIAL PRIMARY KEY,
    analysis_id        TEXT REFERENCES analysis_runs(id),
    status             TEXT,
    checks             JSONB,
    reasons            JSONB
);

CREATE TABLE IF NOT EXISTS verifications (
    id                 SERIAL PRIMARY KEY,
    analysis_id        TEXT REFERENCES analysis_runs(id),
    field              TEXT,
    status             TEXT,             -- VERIFIED / CONFLICT / UNVERIFIED
    detail             TEXT
);

CREATE TABLE IF NOT EXISTS results (
    id                 SERIAL PRIMARY KEY,
    analysis_id        TEXT REFERENCES analysis_runs(id),
    actual_stat        REAL,
    actual_opportunity REAL,
    result             TEXT,             -- HIT / MISS / PUSH
    projection_error   REAL,
    error_category     TEXT,
    resolved_at        TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS closing_lines (
    id                 SERIAL PRIMARY KEY,
    analysis_id        TEXT REFERENCES analysis_runs(id),
    closing_line       REAL,
    closing_price      REAL,
    clv                REAL
);

CREATE TABLE IF NOT EXISTS calibration_stats (
    id                 SERIAL PRIMARY KEY,
    bucket             TEXT,
    n                  INTEGER,
    predicted          REAL,
    actual             REAL,
    computed_at        TIMESTAMPTZ
);

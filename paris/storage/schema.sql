-- paris persistence schema (plan section 18).
-- Pre-match fields are written when an analysis is saved; post-event fields are
-- filled later by the audit loop (plan section 19 / spec 58).

CREATE TABLE IF NOT EXISTS analyses (
    analysis_id            TEXT PRIMARY KEY,
    created_at             TEXT NOT NULL,
    model_version          TEXT,
    -- entity
    sport                  TEXT,
    event                  TEXT,
    subject                TEXT,
    market                 TEXT,
    line                   REAL,
    side                   TEXT,
    -- projection / probability
    projection             REAL,
    interval_low           REAL,
    interval_high          REAL,
    distribution           TEXT,
    model_probability      REAL,
    -- market math
    market_probability     REAL,
    edge                   REAL,
    fair_odds              REAL,
    offered_odds           REAL,
    ev                     REAL,
    -- decision
    grade                  TEXT,
    decision               TEXT,
    -- opportunity / verification
    opportunity_expected   REAL,
    opportunity_certainty  TEXT,
    verified               INTEGER,
    sources                TEXT,          -- JSON array
    -- full normalized record for anything not columnized
    payload                TEXT,          -- JSON

    -- post-event audit fields (nullable until the match resolves)
    actual_stat            REAL,
    actual_opportunity     REAL,
    result                 TEXT,          -- HIT / MISS / PUSH
    closing_line           REAL,
    closing_price          REAL,
    clv                    REAL,
    projection_error       REAL,
    error_category         TEXT,
    resolved_at            TEXT
);

CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at);
CREATE INDEX IF NOT EXISTS idx_analyses_decision ON analyses(decision);
CREATE INDEX IF NOT EXISTS idx_analyses_event ON analyses(event);
CREATE INDEX IF NOT EXISTS idx_analyses_result ON analyses(result);

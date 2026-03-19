CREATE TABLE IF NOT EXISTS run_events (

    id BIGSERIAL PRIMARY KEY,

    run_id UUID NOT NULL,

    sequence INTEGER NOT NULL,

    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    type TEXT NOT NULL,

    agent_id TEXT NOT NULL,

    payload JSONB NOT NULL,

    UNIQUE(run_id, sequence)

);

CREATE INDEX idx_run_events_run_id
ON run_events(run_id);

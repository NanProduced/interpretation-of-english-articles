-- Guest/anonymous user quota tracking
-- Limits trial usage for users who haven't logged in

CREATE TABLE anonymous_quotas (
    anonymous_id TEXT PRIMARY KEY,  -- device identifier or client-generated UUID
    trial_count INTEGER NOT NULL DEFAULT 0,
    last_trial_at DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_anonymous_quotas_set_updated_at
BEFORE UPDATE ON anonymous_quotas
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

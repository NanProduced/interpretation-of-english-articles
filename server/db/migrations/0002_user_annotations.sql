CREATE TABLE IF NOT EXISTS user_annotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    analysis_record_id UUID REFERENCES analysis_records(id) ON DELETE SET NULL,
    annotation_type TEXT NOT NULL DEFAULT 'highlight'
        CHECK (annotation_type IN ('highlight', 'note')),
    anchor_type TEXT NOT NULL DEFAULT 'sentence'
        CHECK (anchor_type IN ('sentence', 'paragraph', 'text_range')),
    target_key TEXT NOT NULL,
    paragraph_id TEXT,
    sentence_id TEXT,
    selected_text TEXT NOT NULL,
    start_offset INTEGER,
    end_offset INTEGER,
    text_hash TEXT,
    color TEXT NOT NULL DEFAULT 'warm_yellow'
        CHECK (color IN ('warm_yellow', 'soft_blue', 'sage_green')),
    note TEXT,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_annotations_target UNIQUE (user_id, target_key)
);

CREATE INDEX IF NOT EXISTS idx_user_annotations_record_created
    ON user_annotations(user_id, analysis_record_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_user_annotations_sentence
    ON user_annotations(user_id, analysis_record_id, sentence_id)
    WHERE sentence_id IS NOT NULL AND deleted_at IS NULL;

DROP TRIGGER IF EXISTS trg_user_annotations_set_updated_at ON user_annotations;
CREATE TRIGGER trg_user_annotations_set_updated_at
BEFORE UPDATE ON user_annotations
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

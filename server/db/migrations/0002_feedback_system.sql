-- ============================================================
-- 0002_feedback_system.sql
-- Feedback system: feedback table + credit ledger entry_type extension
-- ============================================================

-- 1. feedback table
CREATE TABLE feedback (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    feedback_scope  TEXT NOT NULL CHECK (feedback_scope IN (
                        'analysis_result',
                        'annotation',
                        'dictionary',
                        'app'
                    )),

    target_id       TEXT NOT NULL,

    analysis_record_id UUID REFERENCES analysis_records(id) ON DELETE CASCADE,

    sentiment       TEXT NOT NULL CHECK (sentiment IN ('positive', 'negative', 'neutral')),

    feedback_type   TEXT NOT NULL,

    annotation_type TEXT,

    content         TEXT,

    context_json    JSONB NOT NULL DEFAULT '{}'::jsonb,

    app_version     TEXT,
    client_platform TEXT NOT NULL DEFAULT 'wechat_miniprogram',

    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
                        'pending', 'adopted', 'resolved', 'dismissed'
                    )),

    reward_points   INTEGER NOT NULL DEFAULT 0,
    reward_granted_at TIMESTAMPTZ,

    admin_note      TEXT,
    reviewed_at     TIMESTAMPTZ,
    reviewed_by     UUID REFERENCES users(id) ON DELETE SET NULL,

    rag_harvested   BOOLEAN NOT NULL DEFAULT FALSE,
    rag_harvested_at TIMESTAMPTZ,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_feedback_user_target_type UNIQUE (user_id, target_id, feedback_type)
);

CREATE INDEX idx_feedback_user_created ON feedback(user_id, created_at DESC);
CREATE INDEX idx_feedback_scope_type ON feedback(feedback_scope, feedback_type);
CREATE INDEX idx_feedback_record ON feedback(analysis_record_id)
    WHERE analysis_record_id IS NOT NULL;
CREATE INDEX idx_feedback_annotation_type ON feedback(annotation_type)
    WHERE annotation_type IS NOT NULL;
CREATE INDEX idx_feedback_sentiment ON feedback(sentiment, feedback_scope);
CREATE INDEX idx_feedback_status ON feedback(status)
    WHERE status = 'pending';
CREATE INDEX idx_feedback_rag_harvested ON feedback(rag_harvested)
    WHERE rag_harvested = FALSE AND feedback_scope IN ('annotation', 'dictionary');
CREATE INDEX idx_feedback_context ON feedback USING GIN(context_json);

CREATE TRIGGER trg_feedback_set_updated_at
BEFORE UPDATE ON feedback
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE feedback IS '用户反馈表，统一存储结果页整体反馈、批注级反馈、词典反馈和应用功能反馈。';
COMMENT ON COLUMN feedback.feedback_scope IS '反馈作用域：analysis_result（结果页整体）、annotation（批注级）、dictionary（词典）、app（应用功能）。';
COMMENT ON COLUMN feedback.target_id IS '反馈目标标识：analysis_result 为 record_id，annotation 为 mark.id/sentence_entry.id，dictionary 为 dict_entry_id 或 word，app 为功能区域标识。';
COMMENT ON COLUMN feedback.sentiment IS '情感倾向：positive（正面）、negative（负面）、neutral（中性）。dictionary 作用域仅允许 negative。';
COMMENT ON COLUMN feedback.feedback_type IS '结构化反馈分类，含义随 feedback_scope 变化。';
COMMENT ON COLUMN feedback.annotation_type IS '标注类型，仅 annotation 作用域有值。';
COMMENT ON COLUMN feedback.context_json IS '反馈时的上下文快照 JSON，用于 RAG 训练数据提取。';
COMMENT ON COLUMN feedback.status IS '处理状态：pending（待处理）、adopted（已采纳，触发奖励）、resolved（已解决）、dismissed（已关闭）。';
COMMENT ON COLUMN feedback.reward_points IS '因反馈被采纳而发放的奖励积分数，0 表示未发放。';
COMMENT ON COLUMN feedback.rag_harvested IS '是否已被用于 RAG 训练数据提取。';

-- 2. Extend user_credit_ledger entry_type
ALTER TABLE user_credit_ledger DROP CONSTRAINT user_credit_ledger_entry_type_check;
ALTER TABLE user_credit_ledger ADD CONSTRAINT user_credit_ledger_entry_type_check
  CHECK (entry_type IN (
    'daily_grant', 'bonus_grant', 'analysis_deduct',
    'manual_adjust', 'refund', 'feedback_reward'
  ));

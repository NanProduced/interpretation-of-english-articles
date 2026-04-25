CREATE TABLE user_reading_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    reading_goals_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    reading_variants_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    total_word_count BIGINT NOT NULL DEFAULT 0,
    total_annotation_count BIGINT NOT NULL DEFAULT 0,
    schema_versions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    academic_count INTEGER NOT NULL DEFAULT 0,
    non_academic_count INTEGER NOT NULL DEFAULT 0,
    recent_signals_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    portrait_text TEXT,
    portrait_generated_at TIMESTAMPTZ,
    portrait_signal_count_since_last INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_reading_profiles_user_id ON user_reading_profiles(user_id);

COMMENT ON TABLE user_reading_profiles IS '用户阅读画像表，保存阅读行为统计和生成的画像文本。';

COMMENT ON COLUMN user_reading_profiles.user_id IS '关联的用户 ID。';
COMMENT ON COLUMN user_reading_profiles.reading_goals_json IS '阅读目标统计 JSON，如 {"daily_reading": 10, "exam": 5, "academic": 3}。';
COMMENT ON COLUMN user_reading_profiles.reading_variants_json IS '阅读变体统计 JSON，如 {"intermediate_reading": 8, "cet": 3}。';
COMMENT ON COLUMN user_reading_profiles.total_word_count IS '累计阅读词数。';
COMMENT ON COLUMN user_reading_profiles.total_annotation_count IS '累计标注数量。';
COMMENT ON COLUMN user_reading_profiles.schema_versions_json IS '使用的 schema 版本统计 JSON。';
COMMENT ON COLUMN user_reading_profiles.academic_count IS 'academic 类型文章数量。';
COMMENT ON COLUMN user_reading_profiles.non_academic_count IS '非 academic 类型文章数量。';
COMMENT ON COLUMN user_reading_profiles.recent_signals_json IS '最近的信号列表 JSON，用于生成画像，最多保存最近 10 篇。';
COMMENT ON COLUMN user_reading_profiles.portrait_text IS '生成的用户可读画像文本。';
COMMENT ON COLUMN user_reading_profiles.portrait_generated_at IS '上次画像生成时间。';
COMMENT ON COLUMN user_reading_profiles.portrait_signal_count_since_last IS '上次画像生成后累计的信号数量。';
COMMENT ON COLUMN user_reading_profiles.created_at IS '记录创建时间。';
COMMENT ON COLUMN user_reading_profiles.updated_at IS '记录最后更新时间。';

CREATE TRIGGER trg_user_reading_profiles_set_updated_at
BEFORE UPDATE ON user_reading_profiles
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

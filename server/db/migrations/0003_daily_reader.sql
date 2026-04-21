-- ============================================================
-- 0003_daily_reader.sql
-- Daily Reader module: daily_readers table for pre-generated article payloads
-- ============================================================

CREATE TABLE daily_readers (
    id                  TEXT PRIMARY KEY,
    title               TEXT NOT NULL,
    subtitle            TEXT,
    source              TEXT NOT NULL,
    source_url          TEXT NOT NULL,
    publish_date        DATE NOT NULL,

    difficulty          TEXT NOT NULL CHECK (difficulty IN ('A2', 'B1', 'B2', 'C1')),
    read_time_minutes   INTEGER NOT NULL,
    tags                JSONB NOT NULL DEFAULT '[]'::jsonb,

    cover_image_url     TEXT,
    cover_theme         TEXT NOT NULL DEFAULT 'editorial_warm',

    body_json           JSONB NOT NULL,
    highlights_json     JSONB NOT NULL DEFAULT '[]'::jsonb,
    footer_analysis_json JSONB NOT NULL,

    status              TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    score               REAL,

    content_sec_check   JSONB NOT NULL DEFAULT '{}'::jsonb,
    original_text_hash  TEXT,
    pipeline_source     TEXT,
    pipeline_meta       JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at        TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_daily_readers_status_date ON daily_readers(status, publish_date DESC);
CREATE INDEX idx_daily_readers_published ON daily_readers(publish_date DESC)
    WHERE status = 'published';
CREATE INDEX idx_daily_readers_source_url ON daily_readers(original_text_hash)
    WHERE original_text_hash IS NOT NULL;

CREATE TRIGGER trg_daily_readers_set_updated_at
BEFORE UPDATE ON daily_readers
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE daily_readers IS '每日精读文章表，存储预生成的精读内容 payload。每天最多 3 篇已发布文章，由应用层保证，数据库不做 UNIQUE 约束。';
COMMENT ON COLUMN daily_readers.id IS '文章 ID，格式 daily_{YYYY}_{MM}_{DD}_{NNN}。';
COMMENT ON COLUMN daily_readers.title IS '文章标题。';
COMMENT ON COLUMN daily_readers.subtitle IS '副标题/摘要。';
COMMENT ON COLUMN daily_readers.source IS '来源媒体名称，如 The Guardian、BBC News。';
COMMENT ON COLUMN daily_readers.source_url IS '原文链接，用于版权标注和引导用户访问。';
COMMENT ON COLUMN daily_readers.publish_date IS '发布日期（UTC+8），用于按天查询今日精读。';
COMMENT ON COLUMN daily_readers.difficulty IS 'CEFR 难度等级。';
COMMENT ON COLUMN daily_readers.read_time_minutes IS '预估阅读时长（分钟）。';
COMMENT ON COLUMN daily_readers.tags IS '文章主题标签数组。';
COMMENT ON COLUMN daily_readers.cover_image_url IS '封面图 URL，优先使用文章自带图。';
COMMENT ON COLUMN daily_readers.cover_theme IS '封面氛围主题，用于无封面图时的渐变色渲染。';
COMMENT ON COLUMN daily_readers.body_json IS '正文段落数据，包含段落文本和高亮锚点。';
COMMENT ON COLUMN daily_readers.highlights_json IS '正文高亮标注数据，vocab_highlight/phrase_gloss/context_gloss。';
COMMENT ON COLUMN daily_readers.footer_analysis_json IS '文末解析数据，summary/structure/key_expressions/full_analysis/discussion_questions。';
COMMENT ON COLUMN daily_readers.status IS '文章状态：draft（草稿）、published（已发布）、archived（已归档）。';
COMMENT ON COLUMN daily_readers.score IS 'AI 评分（4 维综合，满分 10）。';
COMMENT ON COLUMN daily_readers.content_sec_check IS '微信内容安全检测结果，含 trace_id、suggest、label 等。';
COMMENT ON COLUMN daily_readers.original_text_hash IS '原文 SHA256，用于去重校验。';
COMMENT ON COLUMN daily_readers.pipeline_source IS '拉取来源标识，如 guardian_api、bbc_rss。';
COMMENT ON COLUMN daily_readers.pipeline_meta IS 'Pipeline 运行元数据，含评分详情、提取日志、workflow 审核记录等。';

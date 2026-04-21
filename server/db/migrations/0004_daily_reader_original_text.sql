-- ============================================================
-- 0004_daily_reader_original_text.sql
-- Add original_text column for retry workflow support
-- ============================================================

ALTER TABLE daily_readers ADD COLUMN IF NOT EXISTS original_text TEXT;

COMMENT ON COLUMN daily_readers.original_text IS '原文全文，用于 retry workflow 重新生成解析内容。仅在 pipeline 存储时写入，历史数据为 NULL。';

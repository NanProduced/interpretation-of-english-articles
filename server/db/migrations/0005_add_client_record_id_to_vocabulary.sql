-- Add client_record_id column to vocabulary_book table
-- This allows us to track the original client-side record ID for vocabulary entries,
-- enabling proper linking back to the original analysis record in the frontend.

ALTER TABLE vocabulary_book
  ADD COLUMN client_record_id TEXT;

CREATE INDEX idx_vocabulary_book_client_record_id ON vocabulary_book(client_record_id)
  WHERE client_record_id IS NOT NULL;

COMMENT ON COLUMN vocabulary_book.client_record_id IS '客户端侧生成的记录 ID，用于关联回原始分析记录。';

-- Backfill: Try to populate client_record_id from analysis_records for existing entries
UPDATE vocabulary_book vb
SET client_record_id = ar.client_record_id
FROM analysis_records ar
WHERE vb.analysis_record_id = ar.id
  AND vb.client_record_id IS NULL;

-- Migration: Add paragraph_notes_json and takeaways_json columns to daily_readers
-- Retains footer_analysis_json for backward compatibility (old data not deleted)

ALTER TABLE daily_readers
  ADD COLUMN IF NOT EXISTS paragraph_notes_json JSONB NOT NULL DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS takeaways_json JSONB NOT NULL DEFAULT '{}';

COMMENT ON COLUMN daily_readers.paragraph_notes_json IS '段落透读与译文：article_summary, reading_focus, notes[{paragraph_id, focus_question, micro_summary, translation}]';
COMMENT ON COLUMN daily_readers.takeaways_json IS '精读收束：article_takeaway, key_expressions, sentence_notes, writing_moves, discussion_questions';

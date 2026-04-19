-- Migration: 0002_vocabulary_book_overhaul
-- Rebuild vocabulary_book table with dict_entry_id and remove analysis_record_id.
-- Source record association is now managed via payload_json.source_refs.

DROP TABLE IF EXISTS vocabulary_book CASCADE;

CREATE TABLE vocabulary_book (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  lemma TEXT NOT NULL,
  display_word TEXT NOT NULL,
  phonetic TEXT,
  part_of_speech TEXT,
  short_meaning TEXT NOT NULL,
  meanings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  exchange TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  source_provider TEXT NOT NULL DEFAULT 'tecd3',
  dict_entry_id BIGINT REFERENCES dict_entries(id) ON DELETE SET NULL,
  source_sentence TEXT,
  source_context TEXT,
  mastery_status TEXT NOT NULL DEFAULT 'new' CHECK (mastery_status IN ('new', 'learning', 'review', 'mastered', 'archived')),
  review_count INTEGER NOT NULL DEFAULT 0,
  last_reviewed_at TIMESTAMPTZ,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_vocabulary_book_user_lemma_lower ON vocabulary_book(user_id, LOWER(lemma));
CREATE INDEX idx_vocabulary_book_user_created_at ON vocabulary_book(user_id, created_at DESC);
CREATE INDEX idx_vocabulary_book_user_mastery_status ON vocabulary_book(user_id, mastery_status);
CREATE INDEX idx_vocabulary_book_dict_entry_id ON vocabulary_book(dict_entry_id) WHERE dict_entry_id IS NOT NULL;

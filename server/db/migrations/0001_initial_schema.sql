CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled', 'deleted')),
  display_name TEXT,
  avatar_url TEXT,
  locale TEXT NOT NULL DEFAULT 'zh-CN',
  timezone TEXT NOT NULL DEFAULT 'Asia/Shanghai',
  settings_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE user_identities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  provider_user_id TEXT NOT NULL,
  unionid TEXT,
  app_id TEXT,
  auth_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_user_identities_provider_user UNIQUE (provider, provider_user_id)
);

CREATE INDEX idx_user_identities_user_id ON user_identities(user_id);
CREATE INDEX idx_user_identities_unionid ON user_identities(unionid) WHERE unionid IS NOT NULL;

CREATE TABLE user_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  session_token_hash TEXT NOT NULL UNIQUE,
  refresh_token_hash TEXT UNIQUE,
  client_platform TEXT NOT NULL DEFAULT 'wechat_miniprogram',
  device_id TEXT,
  device_name TEXT,
  app_version TEXT,
  ip_address INET,
  user_agent TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked', 'expired')),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  refresh_expires_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_sessions_user_id_status ON user_sessions(user_id, status);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);

CREATE TABLE analysis_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  client_record_id TEXT,
  source_type TEXT NOT NULL DEFAULT 'user_input' CHECK (source_type IN ('user_input', 'daily_article', 'imported')),
  title TEXT,
  source_text TEXT NOT NULL,
  source_text_hash TEXT NOT NULL,
  request_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  render_scene_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  page_state_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  reading_goal TEXT,
  reading_variant TEXT,
  user_facing_state TEXT,
  workflow_version TEXT,
  schema_version TEXT,
  analysis_status TEXT NOT NULL DEFAULT 'ready' CHECK (analysis_status IN ('ready', 'partial', 'failed', 'deleted')),
  last_opened_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_analysis_records_client_record UNIQUE (user_id, client_record_id)
);

CREATE INDEX idx_analysis_records_user_created_at ON analysis_records(user_id, created_at DESC);
CREATE INDEX idx_analysis_records_user_updated_at ON analysis_records(user_id, updated_at DESC);
CREATE INDEX idx_analysis_records_source_hash ON analysis_records(source_text_hash);
CREATE INDEX idx_analysis_records_render_scene_gin ON analysis_records USING GIN (render_scene_json);

CREATE TABLE favorite_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  target_type TEXT NOT NULL CHECK (target_type IN ('analysis_record', 'sentence', 'phrase', 'vocab')),
  target_key TEXT NOT NULL,
  analysis_record_id UUID REFERENCES analysis_records(id) ON DELETE CASCADE,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_favorite_records_target UNIQUE (user_id, target_type, target_key)
);

CREATE INDEX idx_favorite_records_user_created_at ON favorite_records(user_id, created_at DESC);
CREATE INDEX idx_favorite_records_analysis_record_id ON favorite_records(analysis_record_id) WHERE analysis_record_id IS NOT NULL;

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
  source_provider TEXT NOT NULL DEFAULT 'ecdict',
  analysis_record_id UUID REFERENCES analysis_records(id) ON DELETE SET NULL,
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

CREATE TABLE ecdict_entries (
  id BIGSERIAL PRIMARY KEY,
  word TEXT NOT NULL,
  phonetic TEXT,
  definition TEXT,
  translation TEXT,
  part_of_speech TEXT,
  exchange TEXT,
  tag TEXT,
  bnc INTEGER,
  frq INTEGER,
  oxford INTEGER,
  collins INTEGER,
  detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_ecdict_entries_word_lower ON ecdict_entries(LOWER(word));
CREATE INDEX idx_ecdict_entries_tag ON ecdict_entries(tag);

CREATE TABLE ecdict_lemmas (
  id BIGSERIAL PRIMARY KEY,
  inflected_form TEXT NOT NULL,
  lemma TEXT NOT NULL,
  rule TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_ecdict_lemmas_inflected_form_lower ON ecdict_lemmas(LOWER(inflected_form));
CREATE INDEX idx_ecdict_lemmas_lemma_lower ON ecdict_lemmas(LOWER(lemma));

CREATE TABLE ecdict_aliases (
  id BIGSERIAL PRIMARY KEY,
  alias TEXT NOT NULL,
  normalized TEXT NOT NULL,
  alias_type TEXT NOT NULL DEFAULT 'abbreviation',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_ecdict_aliases_alias_lower ON ecdict_aliases(LOWER(alias));
CREATE INDEX idx_ecdict_aliases_normalized_lower ON ecdict_aliases(LOWER(normalized));

CREATE TRIGGER trg_users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_user_identities_set_updated_at
BEFORE UPDATE ON user_identities
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_user_sessions_set_updated_at
BEFORE UPDATE ON user_sessions
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_analysis_records_set_updated_at
BEFORE UPDATE ON analysis_records
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_favorite_records_set_updated_at
BEFORE UPDATE ON favorite_records
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_vocabulary_book_set_updated_at
BEFORE UPDATE ON vocabulary_book
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_ecdict_entries_set_updated_at
BEFORE UPDATE ON ecdict_entries
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

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
  source_provider TEXT NOT NULL DEFAULT 'tecd3',
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

CREATE TABLE dict_entries (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL DEFAULT 'tecd3',
  source_entry_key TEXT NOT NULL,
  entry_kind TEXT NOT NULL CHECK (entry_kind IN ('entry', 'fragment')),
  display_headword TEXT NOT NULL,
  base_headword TEXT,
  homograph_no INTEGER,
  phonetic TEXT,
  primary_pos TEXT,
  meanings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  examples_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  phrases_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  sections_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  raw_html TEXT,
  parse_version TEXT NOT NULL DEFAULT 'tecd3_v2',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_dict_entries_source_entry_key ON dict_entries(source, source_entry_key);
CREATE INDEX idx_dict_entries_display_headword_lower ON dict_entries(LOWER(display_headword));
CREATE INDEX idx_dict_entries_base_headword_lower ON dict_entries(LOWER(base_headword));

CREATE TABLE dict_lookup_targets (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL DEFAULT 'tecd3',
  normalized_form TEXT NOT NULL,
  lookup_label TEXT NOT NULL,
  entry_id BIGINT NOT NULL REFERENCES dict_entries(id) ON DELETE CASCADE,
  target_label TEXT NOT NULL,
  target_pos TEXT,
  preview_text TEXT,
  rank INTEGER NOT NULL DEFAULT 0,
  match_kind TEXT NOT NULL CHECK (match_kind IN ('headword', 'alias', 'disamb', 'redirect')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_dict_lookup_targets UNIQUE (source, normalized_form, entry_id, match_kind)
);

CREATE INDEX idx_dict_lookup_targets_form_rank ON dict_lookup_targets(source, normalized_form, rank);
CREATE INDEX idx_dict_lookup_targets_entry_id ON dict_lookup_targets(entry_id);

CREATE TABLE dict_redirects (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL DEFAULT 'tecd3',
  redirect_key TEXT NOT NULL,
  target_entry_key TEXT NOT NULL,
  redirect_kind TEXT NOT NULL CHECK (redirect_kind IN ('mdx_link', 'normalized_alias')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_dict_redirects UNIQUE (source, redirect_key, target_entry_key, redirect_kind)
);

CREATE INDEX idx_dict_redirects_key ON dict_redirects(source, redirect_key);
CREATE INDEX idx_dict_redirects_target ON dict_redirects(source, target_entry_key);

COMMENT ON TABLE users IS '用户主表，保存应用内部用户档案与基础偏好设置。';
COMMENT ON COLUMN users.id IS '用户主键，使用 UUID。';
COMMENT ON COLUMN users.status IS '用户状态，支持 active、disabled、deleted。';
COMMENT ON COLUMN users.display_name IS '用户展示名称。';
COMMENT ON COLUMN users.avatar_url IS '用户头像地址。';
COMMENT ON COLUMN users.locale IS '用户语言区域设置，例如 zh-CN。';
COMMENT ON COLUMN users.timezone IS '用户时区标识，例如 Asia/Shanghai。';
COMMENT ON COLUMN users.settings_json IS '用户设置的结构化 JSON 数据。';
COMMENT ON COLUMN users.metadata_json IS '用户附加元数据 JSON。';
COMMENT ON COLUMN users.last_login_at IS '最近一次登录时间。';
COMMENT ON COLUMN users.created_at IS '记录创建时间。';
COMMENT ON COLUMN users.updated_at IS '记录最后更新时间。';

COMMENT ON TABLE user_identities IS '用户身份绑定表，保存第三方登录提供方与应用用户之间的映射。';
COMMENT ON COLUMN user_identities.id IS '身份记录主键，使用 UUID。';
COMMENT ON COLUMN user_identities.user_id IS '关联的应用用户 ID。';
COMMENT ON COLUMN user_identities.provider IS '身份提供方标识，例如 wechat。';
COMMENT ON COLUMN user_identities.provider_user_id IS '第三方平台中的用户唯一标识。';
COMMENT ON COLUMN user_identities.unionid IS '微信等平台的 unionid，用于跨应用归并用户。';
COMMENT ON COLUMN user_identities.app_id IS '第三方应用 ID。';
COMMENT ON COLUMN user_identities.auth_payload_json IS '认证返回的原始或扩展载荷 JSON。';
COMMENT ON COLUMN user_identities.created_at IS '记录创建时间。';
COMMENT ON COLUMN user_identities.updated_at IS '记录最后更新时间。';

COMMENT ON TABLE user_sessions IS '用户会话表，保存登录态、刷新令牌与设备信息。';
COMMENT ON COLUMN user_sessions.id IS '会话主键，使用 UUID。';
COMMENT ON COLUMN user_sessions.user_id IS '关联的应用用户 ID。';
COMMENT ON COLUMN user_sessions.session_token_hash IS '访问令牌哈希值。';
COMMENT ON COLUMN user_sessions.refresh_token_hash IS '刷新令牌哈希值。';
COMMENT ON COLUMN user_sessions.client_platform IS '客户端平台标识，例如 wechat_miniprogram。';
COMMENT ON COLUMN user_sessions.device_id IS '客户端设备 ID。';
COMMENT ON COLUMN user_sessions.device_name IS '设备名称或机型描述。';
COMMENT ON COLUMN user_sessions.app_version IS '客户端应用版本号。';
COMMENT ON COLUMN user_sessions.ip_address IS '最近访问的 IP 地址。';
COMMENT ON COLUMN user_sessions.user_agent IS '客户端 User-Agent 信息。';
COMMENT ON COLUMN user_sessions.status IS '会话状态，支持 active、revoked、expired。';
COMMENT ON COLUMN user_sessions.last_seen_at IS '最近活跃时间。';
COMMENT ON COLUMN user_sessions.expires_at IS '访问令牌过期时间。';
COMMENT ON COLUMN user_sessions.refresh_expires_at IS '刷新令牌过期时间。';
COMMENT ON COLUMN user_sessions.revoked_at IS '会话被撤销的时间。';
COMMENT ON COLUMN user_sessions.metadata_json IS '会话附加元数据 JSON。';
COMMENT ON COLUMN user_sessions.created_at IS '记录创建时间。';
COMMENT ON COLUMN user_sessions.updated_at IS '记录最后更新时间。';

COMMENT ON TABLE analysis_records IS '文章分析记录表，保存用户输入文本、分析请求参数与渲染结果快照。';
COMMENT ON COLUMN analysis_records.id IS '分析记录主键，使用 UUID。';
COMMENT ON COLUMN analysis_records.user_id IS '所属用户 ID。';
COMMENT ON COLUMN analysis_records.client_record_id IS '客户端侧生成的记录 ID，用于回放或去重。';
COMMENT ON COLUMN analysis_records.source_type IS '文本来源类型，例如 user_input、daily_article、imported。';
COMMENT ON COLUMN analysis_records.title IS '文章标题。';
COMMENT ON COLUMN analysis_records.source_text IS '原始输入文本。';
COMMENT ON COLUMN analysis_records.source_text_hash IS '原始文本的哈希值，用于去重与检索。';
COMMENT ON COLUMN analysis_records.request_payload_json IS '分析请求参数 JSON。';
COMMENT ON COLUMN analysis_records.render_scene_json IS '前端渲染场景 JSON 快照。';
COMMENT ON COLUMN analysis_records.page_state_json IS '页面状态与过程信息 JSON。';
COMMENT ON COLUMN analysis_records.reading_goal IS '阅读目标，例如 exam、daily_reading、academic。';
COMMENT ON COLUMN analysis_records.reading_variant IS '阅读变体，例如 cet、ielts_toefl。';
COMMENT ON COLUMN analysis_records.user_facing_state IS '面向用户的结果状态，例如 normal、degraded_light。';
COMMENT ON COLUMN analysis_records.workflow_version IS '分析工作流版本号。';
COMMENT ON COLUMN analysis_records.schema_version IS '渲染结果 schema 版本号。';
COMMENT ON COLUMN analysis_records.analysis_status IS '分析记录状态，支持 ready、partial、failed、deleted。';
COMMENT ON COLUMN analysis_records.last_opened_at IS '最近一次打开该记录的时间。';
COMMENT ON COLUMN analysis_records.created_at IS '记录创建时间。';
COMMENT ON COLUMN analysis_records.updated_at IS '记录最后更新时间。';

COMMENT ON TABLE favorite_records IS '收藏记录表，保存用户对文章、句子、短语或词汇的收藏。';
COMMENT ON COLUMN favorite_records.id IS '收藏记录主键，使用 UUID。';
COMMENT ON COLUMN favorite_records.user_id IS '所属用户 ID。';
COMMENT ON COLUMN favorite_records.target_type IS '收藏目标类型，例如 analysis_record、sentence、phrase、vocab。';
COMMENT ON COLUMN favorite_records.target_key IS '收藏目标的逻辑键，用于唯一定位收藏对象。';
COMMENT ON COLUMN favorite_records.analysis_record_id IS '关联的分析记录 ID，可为空。';
COMMENT ON COLUMN favorite_records.payload_json IS '收藏附加信息 JSON。';
COMMENT ON COLUMN favorite_records.note IS '用户自定义备注。';
COMMENT ON COLUMN favorite_records.created_at IS '记录创建时间。';
COMMENT ON COLUMN favorite_records.updated_at IS '记录最后更新时间。';

COMMENT ON TABLE vocabulary_book IS '用户生词本表，保存词汇快照、掌握状态与复习信息。';
COMMENT ON COLUMN vocabulary_book.id IS '生词记录主键，使用 UUID。';
COMMENT ON COLUMN vocabulary_book.user_id IS '所属用户 ID。';
COMMENT ON COLUMN vocabulary_book.lemma IS '词元或归一化词形，用于唯一去重。';
COMMENT ON COLUMN vocabulary_book.display_word IS '向用户展示的单词原形或表面形。';
COMMENT ON COLUMN vocabulary_book.phonetic IS '音标。';
COMMENT ON COLUMN vocabulary_book.part_of_speech IS '词性。';
COMMENT ON COLUMN vocabulary_book.short_meaning IS '生词快照中的简短释义文本。';
COMMENT ON COLUMN vocabulary_book.meanings_json IS '完整释义结构 JSON。';
COMMENT ON COLUMN vocabulary_book.tags IS '词汇标签数组。';
COMMENT ON COLUMN vocabulary_book.exchange IS '词形变化数组。';
COMMENT ON COLUMN vocabulary_book.source_provider IS '词汇来源提供方，例如 tecd3。';
COMMENT ON COLUMN vocabulary_book.analysis_record_id IS '来源分析记录 ID，可为空。';
COMMENT ON COLUMN vocabulary_book.source_sentence IS '来源句子文本。';
COMMENT ON COLUMN vocabulary_book.source_context IS '来源上下文文本。';
COMMENT ON COLUMN vocabulary_book.mastery_status IS '掌握状态，支持 new、learning、review、mastered、archived。';
COMMENT ON COLUMN vocabulary_book.review_count IS '累计复习次数。';
COMMENT ON COLUMN vocabulary_book.last_reviewed_at IS '最近一次复习时间。';
COMMENT ON COLUMN vocabulary_book.payload_json IS '生词附加元数据 JSON。';
COMMENT ON COLUMN vocabulary_book.created_at IS '记录创建时间。';
COMMENT ON COLUMN vocabulary_book.updated_at IS '记录最后更新时间。';

COMMENT ON TABLE dict_entries IS '词典词条详情表，保存 TECD3 的正式词条或可保留的 fragment 详情。';
COMMENT ON COLUMN dict_entries.id IS '词条主键，自增 bigint。';
COMMENT ON COLUMN dict_entries.source IS '词典来源标识，当前为 tecd3。';
COMMENT ON COLUMN dict_entries.source_entry_key IS '词典原生词条键，用于唯一标识一个入口。';
COMMENT ON COLUMN dict_entries.entry_kind IS '词条类型，entry 表示正式词条，fragment 表示片段词条。';
COMMENT ON COLUMN dict_entries.display_headword IS '展示给用户的词头，保留同形编号。';
COMMENT ON COLUMN dict_entries.base_headword IS '去掉同形编号后的基础词头。';
COMMENT ON COLUMN dict_entries.homograph_no IS '同形词编号，例如 1、2。';
COMMENT ON COLUMN dict_entries.phonetic IS '主音标。';
COMMENT ON COLUMN dict_entries.primary_pos IS '主词性。';
COMMENT ON COLUMN dict_entries.meanings_json IS '完整义项结构 JSON。';
COMMENT ON COLUMN dict_entries.examples_json IS '例句结构 JSON。';
COMMENT ON COLUMN dict_entries.phrases_json IS '短语结构 JSON。';
COMMENT ON COLUMN dict_entries.sections_json IS '词条分段摘要 JSON，用于调试或扩展展示。';
COMMENT ON COLUMN dict_entries.raw_html IS '词条原始 HTML 内容。';
COMMENT ON COLUMN dict_entries.parse_version IS '导入解析器版本号。';
COMMENT ON COLUMN dict_entries.created_at IS '记录创建时间。';
COMMENT ON COLUMN dict_entries.updated_at IS '记录最后更新时间。';

COMMENT ON TABLE dict_lookup_targets IS '词典查询映射表，保存归一化查询词到一个或多个候选词条的关系。';
COMMENT ON COLUMN dict_lookup_targets.id IS '查询映射主键，自增 bigint。';
COMMENT ON COLUMN dict_lookup_targets.source IS '词典来源标识，当前为 tecd3。';
COMMENT ON COLUMN dict_lookup_targets.normalized_form IS '归一化后的查询词。';
COMMENT ON COLUMN dict_lookup_targets.lookup_label IS '查询结果页显示的查找标签。';
COMMENT ON COLUMN dict_lookup_targets.entry_id IS '关联的词条详情 ID。';
COMMENT ON COLUMN dict_lookup_targets.target_label IS '候选词条展示标签。';
COMMENT ON COLUMN dict_lookup_targets.target_pos IS '候选词条词性。';
COMMENT ON COLUMN dict_lookup_targets.preview_text IS '候选词条预览释义。';
COMMENT ON COLUMN dict_lookup_targets.rank IS '候选排序值，越小越靠前。';
COMMENT ON COLUMN dict_lookup_targets.match_kind IS '匹配来源类型，例如 headword、disamb、redirect。';
COMMENT ON COLUMN dict_lookup_targets.created_at IS '记录创建时间。';

COMMENT ON TABLE dict_redirects IS '词典重定向关系表，保存 MDX 链接跳转与归一化别名到词条键的映射。';
COMMENT ON COLUMN dict_redirects.id IS '重定向记录主键，自增 bigint。';
COMMENT ON COLUMN dict_redirects.source IS '词典来源标识，当前为 tecd3。';
COMMENT ON COLUMN dict_redirects.redirect_key IS '重定向查找键。';
COMMENT ON COLUMN dict_redirects.target_entry_key IS '重定向目标词条键。';
COMMENT ON COLUMN dict_redirects.redirect_kind IS '重定向类型，例如 mdx_link、normalized_alias。';
COMMENT ON COLUMN dict_redirects.created_at IS '记录创建时间。';

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

CREATE TRIGGER trg_dict_entries_set_updated_at
BEFORE UPDATE ON dict_entries
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

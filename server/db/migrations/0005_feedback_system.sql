-- ---------------------------------------------------------------------------
-- 反馈系统表结构
-- 用于收集用户反馈，为后续 RAG 的 few-shot 注入做准备
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- 反馈主表
-- ---------------------------------------------------------------------------
CREATE TABLE feedbacks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- 反馈类型：标识是从哪个功能模块提交的
  feedback_type TEXT NOT NULL CHECK (feedback_type IN (
    'result_overall',    -- 结果页整体反馈
    'grammar_note',      -- 语法标注反馈
    'sentence_analysis', -- 句式分析反馈
    'vocab_entry',       -- 词汇卡片反馈
    'general'            -- 通用反馈（从个人中心提交）
  )),
  
  -- 满意度：是否满意（null 表示未评价或不适用）
  satisfaction BOOLEAN,
  
  -- 反馈分类（不满意时选择的类型）
  category TEXT CHECK (category IN (
    'data_error',           -- 数据错误
    'poor_quality',         -- 质量差
    'translation_wrong',    -- 翻译错误
    'incomplete',           -- 信息不完整
    'irrelevant',           -- 不相关
    'unclear',              -- 表达不清楚
    'performance',          -- 性能问题（慢）
    'ui_ux',                -- UI/UX 问题
    'other',                -- 其他
    -- 针对不同场景的差异化分类
    'too_slow',             -- 响应太慢（结果页专用）
    'layout_mess',          -- 排版混乱（结果页专用）
    'inaccurate_annotation',-- 标注不准确（语法/词汇专用）
    'split_wrong',          -- 拆分不准确（句式解析专用）
    'wrong_in_context',     -- 不符合语境（词汇专用）
    'feature_suggestion',   -- 功能建议（通用反馈专用）
    'app_crash',            -- 程序错误（通用反馈专用）
    'experience_issue'      -- 体验问题（通用反馈专用）
  )),
  
  -- 用户输入的详细理由
  detail_text TEXT,
  
  -- 关联的分析记录 ID（可选，某些场景下有）
  analysis_record_id UUID REFERENCES analysis_records(id) ON DELETE SET NULL,
  
  -- 上下文数据 JSON：根据不同 feedback_type 存储不同的上下文
  -- 
  -- 【重要设计原则】
  -- 所有能通过 analysis_record_id 关联查询到的数据（如原文、长度、解析结果）都不存储
  -- 只存储：关键 ID 引用、反馈特有元数据、无法通过关联查询的数据
  --
  -- 可通过 analysis_record_id 查询的数据（不存储）：
  -- - source_text（原文）→ 可计算 preview、length
  -- - reading_goal, reading_variant, extended, user_facing_state（来自 analysis_records 表）
  -- - render_scene_json（完整解析结果：句子、词汇、标注等）
  --
  -- result_overall：
  -- {
  --   "processing_ms": 25000   -- 反馈触发时的处理耗时（可能在 analysis_records 中未保存）
  -- }
  --
  -- grammar_note / sentence_analysis：
  -- {
  --   "sentence_id": "s_xxx",
  --   "annotation_id": "ann_xxx",
  --   "annotation_type": "grammar_note"
  -- }
  --
  -- vocab_entry：
  -- {
  --   "mark_id": "m_xxx",
  --   "vocab_preview": "running",
  --   "vocab_source": "vocab_highlight",
  --   "is_ai_annotated": true
  -- }
  --
  -- general：
  -- {
  --   "page": "profile",
  --   "app_version": "1.0.0",
  --   "platform": "wechat_miniprogram"
  -- }
  context_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  
  -- 客户端元数据
  client_metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  
  -- 处理状态（预留字段，用于后续处理反馈）
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
    'pending',      -- 待处理
    'reviewed',     -- 已审核
    'used_for_rag', -- 已用于 RAG 训练
    'dismissed'     -- 已忽略
  )),
  
  -- 审核备注（预留字段）
  admin_note TEXT,
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_feedbacks_user_id ON feedbacks(user_id);
CREATE INDEX idx_feedbacks_feedback_type ON feedbacks(feedback_type);
CREATE INDEX idx_feedbacks_satisfaction ON feedbacks(satisfaction);
CREATE INDEX idx_feedbacks_category ON feedbacks(category);
CREATE INDEX idx_feedbacks_analysis_record_id ON feedbacks(analysis_record_id);
CREATE INDEX idx_feedbacks_created_at ON feedbacks(created_at DESC);
CREATE INDEX idx_feedbacks_status ON feedbacks(status);

-- JSONB 索引：用于快速查询特定上下文字段
CREATE INDEX idx_feedbacks_context_gin ON feedbacks USING GIN (context_json);

-- ---------------------------------------------------------------------------
-- 触发器：自动更新 updated_at
-- ---------------------------------------------------------------------------
CREATE TRIGGER trg_feedbacks_set_updated_at
BEFORE UPDATE ON feedbacks
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- 表注释
-- ---------------------------------------------------------------------------
COMMENT ON TABLE feedbacks IS '用户反馈表，收集上线初期用户反馈，用于 RAG few-shot 注入准备。';
COMMENT ON COLUMN feedbacks.id IS '反馈记录主键，UUID。';
COMMENT ON COLUMN feedbacks.user_id IS '提交反馈的用户 ID。';
COMMENT ON COLUMN feedbacks.feedback_type IS '反馈类型：result_overall（结果页整体）、grammar_note（语法标注）、sentence_analysis（句式分析）、vocab_entry（词汇卡片）、general（通用反馈）。';
COMMENT ON COLUMN feedbacks.satisfaction IS '满意度：true=满意，false=不满意，null=未评价或不适用。';
COMMENT ON COLUMN feedbacks.category IS '反馈分类：数据错误、质量差、翻译错误、信息不完整、不相关、表达不清楚、性能问题、UI/UX问题、其他。';
COMMENT ON COLUMN feedbacks.detail_text IS '用户输入的详细反馈理由。';
COMMENT ON COLUMN feedbacks.analysis_record_id IS '关联的分析记录 ID（可选）。';
COMMENT ON COLUMN feedbacks.context_json IS '上下文数据 JSON，根据 feedback_type 存储不同的上下文信息，用于后续 RAG 分析。';
COMMENT ON COLUMN feedbacks.client_metadata_json IS '客户端元数据 JSON，如版本号、平台、设备信息等。';
COMMENT ON COLUMN feedbacks.status IS '处理状态：pending（待处理）、reviewed（已审核）、used_for_rag（已用于 RAG）、dismissed（已忽略）。';
COMMENT ON COLUMN feedbacks.admin_note IS '管理员备注（预留）。';

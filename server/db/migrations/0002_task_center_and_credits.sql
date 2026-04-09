-- Migration: 0002_task_center_and_credits
-- Description: Add analysis task center (幂等/单任务/生命周期) and credit system (积分账本)
-- Depends on: 0001_initial_schema

-- ============================================================
-- 1. Extend analysis_records.analysis_status CHECK constraint
-- ============================================================

ALTER TABLE analysis_records
  DROP CONSTRAINT IF EXISTS analysis_records_analysis_status_check;

ALTER TABLE analysis_records
  ADD CONSTRAINT analysis_records_analysis_status_check
  CHECK (analysis_status IN (
    'queued', 'running', 'finalizing',
    'ready', 'partial', 'failed',
    'deleted', 'cancelled', 'expired'
  ));

-- ============================================================
-- 2. analysis_tasks — 执行控制平面
-- ============================================================

CREATE TABLE analysis_tasks (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  analysis_record_id UUID NOT NULL REFERENCES analysis_records(id) ON DELETE CASCADE,
  idempotency_key    TEXT NOT NULL,
  request_fingerprint TEXT,

  status        TEXT NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued', 'running', 'finalizing', 'succeeded', 'failed', 'cancelled', 'expired')),

  worker_token  TEXT,
  queue_name    TEXT NOT NULL DEFAULT 'default',
  attempt_no    INTEGER NOT NULL DEFAULT 1,

  failure_code    TEXT,
  failure_message TEXT,

  usage_summary_json  JSONB NOT NULL DEFAULT '{}'::jsonb,
  quota_cost_points   INTEGER NOT NULL DEFAULT 0,

  queued_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at    TIMESTAMPTZ,
  finished_at   TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 幂等: 同一用户 + 同一幂等键唯一
CREATE UNIQUE INDEX uq_analysis_tasks_idempotency
  ON analysis_tasks (user_id, idempotency_key);

-- 单用户单活跃任务: 同一用户同时只能有一个 queued/running/finalizing 任务
CREATE UNIQUE INDEX uq_analysis_tasks_user_active
  ON analysis_tasks (user_id)
  WHERE status IN ('queued', 'running', 'finalizing');

-- 一个任务只服务一条结果记录
CREATE UNIQUE INDEX uq_analysis_tasks_record
  ON analysis_tasks (analysis_record_id);

-- 查询索引
CREATE INDEX idx_analysis_tasks_user_status
  ON analysis_tasks (user_id, status);

CREATE INDEX idx_analysis_tasks_status_queued_at
  ON analysis_tasks (status, queued_at);

-- ============================================================
-- 3. analysis_task_events — 过程审计日志 (append-only)
-- ============================================================

CREATE TABLE analysis_task_events (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id         UUID NOT NULL REFERENCES analysis_tasks(id) ON DELETE CASCADE,
  event_type      TEXT NOT NULL,
  event_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_task_events_task_created
  ON analysis_task_events (task_id, created_at);

-- ============================================================
-- 4. user_credit_accounts — 用户积分快照 (每用户一行)
-- ============================================================

CREATE TABLE user_credit_accounts (
  user_id           UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  daily_free_points INTEGER NOT NULL DEFAULT 1000,
  daily_used_points INTEGER NOT NULL DEFAULT 0,
  bonus_points      INTEGER NOT NULL DEFAULT 0,
  last_reset_on     DATE NOT NULL DEFAULT CURRENT_DATE,
  policy_version    TEXT NOT NULL DEFAULT 'v1',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 5. user_credit_ledger — 积分流水账本 (append-only)
-- ============================================================

CREATE TABLE user_credit_ledger (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  task_id       UUID REFERENCES analysis_tasks(id) ON DELETE SET NULL,
  entry_type    TEXT NOT NULL
                CHECK (entry_type IN ('daily_grant', 'bonus_grant', 'analysis_deduct', 'manual_adjust', 'refund')),
  points        INTEGER NOT NULL,
  bucket_type   TEXT NOT NULL DEFAULT 'daily_free'
                CHECK (bucket_type IN ('daily_free', 'bonus')),
  balance_after INTEGER NOT NULL,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_credit_ledger_user_created
  ON user_credit_ledger (user_id, created_at DESC);

CREATE INDEX idx_credit_ledger_task
  ON user_credit_ledger (task_id)
  WHERE task_id IS NOT NULL;

-- ============================================================
-- 6. Triggers for updated_at
-- ============================================================

CREATE TRIGGER trg_analysis_tasks_set_updated_at
  BEFORE UPDATE ON analysis_tasks
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_user_credit_accounts_set_updated_at
  BEFORE UPDATE ON user_credit_accounts
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 7. Comments
-- ============================================================

COMMENT ON TABLE analysis_tasks IS '分析任务执行控制表，负责排队、幂等、并发控制、失败重试与额度结算。';
COMMENT ON COLUMN analysis_tasks.id IS '任务主键，UUID。';
COMMENT ON COLUMN analysis_tasks.user_id IS '所属用户 ID。';
COMMENT ON COLUMN analysis_tasks.analysis_record_id IS '关联的分析记录 ID，1:1 关系。';
COMMENT ON COLUMN analysis_tasks.idempotency_key IS '幂等键，由前端生成，同一用户内唯一。';
COMMENT ON COLUMN analysis_tasks.request_fingerprint IS '请求内容指纹，用于二次校验与风控分析。';
COMMENT ON COLUMN analysis_tasks.status IS '任务状态：queued, running, finalizing, succeeded, failed, cancelled, expired。';
COMMENT ON COLUMN analysis_tasks.worker_token IS '执行器标识，用于多实例场景下的任务认领。';
COMMENT ON COLUMN analysis_tasks.queue_name IS '队列名称，默认 default。';
COMMENT ON COLUMN analysis_tasks.attempt_no IS '当前执行尝试次数。';
COMMENT ON COLUMN analysis_tasks.failure_code IS '失败错误码。';
COMMENT ON COLUMN analysis_tasks.failure_message IS '失败错误信息。';
COMMENT ON COLUMN analysis_tasks.usage_summary_json IS '聚合 token 使用量与模型信息 JSON。';
COMMENT ON COLUMN analysis_tasks.quota_cost_points IS '本次任务实际扣减的积分数。';
COMMENT ON COLUMN analysis_tasks.queued_at IS '入队时间。';
COMMENT ON COLUMN analysis_tasks.started_at IS '开始执行时间。';
COMMENT ON COLUMN analysis_tasks.finished_at IS '执行完成时间。';

COMMENT ON TABLE analysis_task_events IS '分析任务过程审计日志，append-only。';
COMMENT ON COLUMN analysis_task_events.task_id IS '关联的任务 ID。';
COMMENT ON COLUMN analysis_task_events.event_type IS '事件类型，如 task_submitted, task_started, task_succeeded 等。';
COMMENT ON COLUMN analysis_task_events.event_payload_json IS '事件载荷 JSON。';

COMMENT ON TABLE user_credit_accounts IS '用户积分账户快照，每用户一行。';
COMMENT ON COLUMN user_credit_accounts.daily_free_points IS 'Daily free points quota (default 1000, where 1pt = 1000 weighted tokens).';
COMMENT ON COLUMN user_credit_accounts.daily_used_points IS '今日已使用积分。';
COMMENT ON COLUMN user_credit_accounts.bonus_points IS '活动赠送/人工补偿/邀请码奖励等长期积分。';
COMMENT ON COLUMN user_credit_accounts.last_reset_on IS '最近一次每日积分重置日期。';
COMMENT ON COLUMN user_credit_accounts.policy_version IS '积分策略版本号。';

COMMENT ON TABLE user_credit_ledger IS '积分流水账本，append-only，所有积分变动均记录。';
COMMENT ON COLUMN user_credit_ledger.entry_type IS '流水类型：daily_grant, bonus_grant, analysis_deduct, manual_adjust, refund。';
COMMENT ON COLUMN user_credit_ledger.points IS '变动积分数（正为增加，负为扣减）。';
COMMENT ON COLUMN user_credit_ledger.bucket_type IS '积分桶类型：daily_free 或 bonus。';
COMMENT ON COLUMN user_credit_ledger.balance_after IS '变动后余额。';
COMMENT ON COLUMN user_credit_ledger.metadata_json IS '扩展元数据 JSON，如 { input_tokens, output_tokens, multiplier_input, multiplier_output }。';

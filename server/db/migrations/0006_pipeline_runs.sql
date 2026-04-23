CREATE TABLE IF NOT EXISTS pipeline_runs (
    id          TEXT PRIMARY KEY,
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    stage       TEXT NOT NULL DEFAULT 'init'
                CHECK (stage IN (
                    'init',
                    'discovery',
                    'extraction',
                    'scoring',
                    'selection',
                    'workflow',
                    'cover_download',
                    'storing',
                    'done'
                )),
    stage_detail    JSONB NOT NULL DEFAULT '{}'::jsonb,
    candidates_found    INT NOT NULL DEFAULT 0,
    candidates_extracted INT NOT NULL DEFAULT 0,
    candidates_scored   INT NOT NULL DEFAULT 0,
    articles_generated  INT NOT NULL DEFAULT 0,
    errors          JSONB NOT NULL DEFAULT '[]'::jsonb,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE pipeline_runs IS '每日精读 pipeline 执行记录，用于追踪异步任务进度';
COMMENT ON COLUMN pipeline_runs.stage IS '当前执行阶段';
COMMENT ON COLUMN pipeline_runs.stage_detail IS '阶段详情，如发现的来源、评分分布等';
COMMENT ON COLUMN pipeline_runs.errors IS '错误列表，每项含 stage + message';

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs (status);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_created ON pipeline_runs (created_at DESC);

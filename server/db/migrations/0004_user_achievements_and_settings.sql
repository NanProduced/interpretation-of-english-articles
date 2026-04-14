-- Add achievement and activity tracking to users table
ALTER TABLE users 
  ADD COLUMN cumulative_article_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN last_active_at TIMESTAMPTZ;

COMMENT ON COLUMN users.cumulative_article_count IS '用户自注册以来累计成功解析的文章总数，删除历史记录不减少。';
COMMENT ON COLUMN users.last_active_at IS '用户最近一次活跃（如发起解析）的时间。';

-- Initial backfill for existing users
UPDATE users u
SET cumulative_article_count = (
    SELECT COUNT(*) FROM analysis_records r 
    WHERE r.user_id = u.id AND r.analysis_status = 'ready'
);

-- ============================================================
-- 0003_ebbinghaus_review.sql
-- 艾宾浩斯遗忘曲线复习系统：添加复习调度字段与索引
-- ============================================================

-- 1. 添加艾宾浩斯复习相关字段到 vocabulary_book 表
ALTER TABLE vocabulary_book 
ADD COLUMN IF NOT EXISTS next_review_at TIMESTAMPTZ;

ALTER TABLE vocabulary_book 
ADD COLUMN IF NOT EXISTS ease_factor DECIMAL(5,3) NOT NULL DEFAULT 2.500;

ALTER TABLE vocabulary_book 
ADD COLUMN IF NOT EXISTS repetitions INTEGER NOT NULL DEFAULT 0;

ALTER TABLE vocabulary_book 
ADD COLUMN IF NOT EXISTS review_interval INTEGER NOT NULL DEFAULT 1;

-- 2. 更新现有数据的 next_review_at 为 created_at + 1天
-- 对于已存在的生词，默认设置为"明天复习"（或者根据 last_reviewed_at 推算）
UPDATE vocabulary_book
SET next_review_at = CASE 
    WHEN last_reviewed_at IS NOT NULL THEN last_reviewed_at + INTERVAL '1 day'
    ELSE created_at + INTERVAL '1 day'
END
WHERE next_review_at IS NULL;

-- 3. 调整已掌握单词的状态
-- 对于 mastery_status = 'mastered' 的单词，设置为已完成复习
UPDATE vocabulary_book
SET 
    repetitions = 5,
    review_interval = 30,
    next_review_at = created_at + INTERVAL '30 days'
WHERE mastery_status = 'mastered' AND repetitions = 0;

-- 4. 创建索引以支持复习查询
-- 用于获取今日/逾期待复习单词
CREATE INDEX IF NOT EXISTS idx_vocabulary_book_user_next_review 
ON vocabulary_book(user_id, next_review_at) 
WHERE mastery_status IN ('new', 'learning', 'review');

-- 用于快速统计待复习数量
CREATE INDEX IF NOT EXISTS idx_vocabulary_book_user_mastery_next_review 
ON vocabulary_book(user_id, mastery_status, next_review_at);

-- 5. 添加注释
COMMENT ON COLUMN vocabulary_book.next_review_at IS '下一次复习时间，基于艾宾浩斯遗忘曲线计算';
COMMENT ON COLUMN vocabulary_book.ease_factor IS '易度因子 (Ease Factor)，SM-2算法核心参数，默认2.5，最低1.3';
COMMENT ON COLUMN vocabulary_book.repetitions IS '连续成功复习次数，用于计算下一次复习间隔';
COMMENT ON COLUMN vocabulary_book.review_interval IS '当前复习间隔（天），上一次成功复习后的间隔';

COMMENT ON INDEX idx_vocabulary_book_user_next_review IS '用户+下次复习时间索引，用于快速获取待复习单词';
COMMENT ON INDEX idx_vocabulary_book_user_mastery_next_review IS '用户+掌握状态+下次复习时间复合索引，用于统计和筛选';

-- ---------------------------------------------------------------------------
-- 扩展反馈分类选项
-- 添加差异化的反馈分类，用于不同场景
-- ---------------------------------------------------------------------------

-- 先删除旧的 CHECK 约束（如果存在）
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'feedbacks_category_check'
    ) THEN
        ALTER TABLE feedbacks DROP CONSTRAINT feedbacks_category_check;
    END IF;
END $$;

-- 添加新的 CHECK 约束，包含所有差异化分类
ALTER TABLE feedbacks
ADD CONSTRAINT feedbacks_category_check
CHECK (category IN (
    'data_error',           -- 数据错误
    'poor_quality',         -- 质量差
    'translation_wrong',    -- 翻译错误
    'incomplete',           -- 信息不完整
    'irrelevant',           -- 不相关
    'unclear',              -- 表达不清楚
    'performance',          -- 性能问题（慢）
    'ui_ux',                -- UI/UX 问题
    'other',                -- 其他
    'too_slow',             -- 响应太慢（结果页专用）
    'layout_mess',          -- 排版混乱（结果页专用）
    'inaccurate_annotation',-- 标注不准确（语法/词汇专用）
    'split_wrong',          -- 拆分不准确（句式解析专用）
    'wrong_in_context',     -- 不符合语境（词汇专用）
    'feature_suggestion',   -- 功能建议（通用反馈专用）
    'app_crash',            -- 程序错误（通用反馈专用）
    'experience_issue'      -- 体验问题（通用反馈专用）
));

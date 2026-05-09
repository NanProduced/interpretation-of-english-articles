ALTER TABLE user_annotations
    DROP CONSTRAINT IF EXISTS user_annotations_color_check;

ALTER TABLE user_annotations
    ALTER COLUMN color SET DEFAULT 'soft_green';

ALTER TABLE user_annotations
    ADD CONSTRAINT user_annotations_color_check
    CHECK (color IN ('soft_green', 'soft_blue', 'soft_purple', 'warm_yellow', 'sage_green'));

ALTER TABLE feedback
    DROP CONSTRAINT IF EXISTS feedback_feedback_scope_check;

ALTER TABLE feedback
    ADD CONSTRAINT feedback_feedback_scope_check
    CHECK (feedback_scope IN ('analysis_result', 'annotation', 'sentence', 'dictionary', 'app'));

COMMENT ON COLUMN feedback.feedback_scope IS '反馈作用域：analysis_result（结果页整体）、annotation（批注级）、sentence（句子级）、dictionary（词典）、app（应用功能）。';

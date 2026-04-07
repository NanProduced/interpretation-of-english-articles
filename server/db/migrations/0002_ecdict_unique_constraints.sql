-- 0002: 为 ECDICT 表添加 unique 约束，支持 INSERT ... ON CONFLICT DO NOTHING
-- 迁移后 ecdict_entries.word 和 ecdict_lemmas.inflected_form 唯一约束才存在，
-- import_ecdict.py 的 ON CONFLICT (col) 子句才能正常工作。

-- ecdict_entries: 原 unique index 在 LOWER(word)，无法被 ON CONFLICT 引用
-- 新增对 word 列本身的唯一约束
ALTER TABLE ecdict_entries
ADD CONSTRAINT uq_ecdict_entries_word UNIQUE (word);

-- ecdict_lemmas: 同理
ALTER TABLE ecdict_lemmas
ADD CONSTRAINT uq_ecdict_lemmas_inflected_form UNIQUE (inflected_form);

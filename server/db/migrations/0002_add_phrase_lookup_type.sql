-- 1. 增加 lookup_type 字段区分 word 和 phrase
ALTER TABLE dict_lookup_targets 
ADD COLUMN lookup_type TEXT NOT NULL DEFAULT 'word';

ALTER TABLE dict_lookup_targets 
ADD CONSTRAINT dict_lookup_targets_lookup_type_chk 
CHECK (lookup_type IN ('word', 'phrase'));

-- 2. 修改 match_kind 的检查约束，增加 'phrase' 和 'phrase_template'
ALTER TABLE dict_lookup_targets 
DROP CONSTRAINT IF EXISTS dict_lookup_targets_match_kind_check;

ALTER TABLE dict_lookup_targets 
ADD CONSTRAINT dict_lookup_targets_match_kind_check 
CHECK (match_kind IN ('headword', 'alias', 'disamb', 'redirect', 'nlp', 'phrase', 'phrase_template'));

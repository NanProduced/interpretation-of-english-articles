# Vocab Display Overhaul

建议 agent 按以下顺序阅读并执行：

1. [requirements.md](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/specs/vocab-display-overhaul/requirements.md)
2. [review.md](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/specs/vocab-display-overhaul/review.md)
3. [design.md](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/specs/vocab-display-overhaul/design.md)
4. [tasks.md](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/specs/vocab-display-overhaul/tasks.md)

执行原则：

- 先做 Phase A：完整词条、lemma 合并、语境卡片、条件跳转、发音、归并反馈
- 再做 Phase B：结果页 overlay 和搜索筛选
- 不要把 vocabulary overlay 合并进 `/analyze`
- 不修改 dict_entries / dict_lookup_targets / dict_redirects 三张词典表
- 第一版不开发复习系统

约束条件：

- 项目尚在开发阶段，不需要数据迁移，可直接重建 vocabulary_book 表
- 词典表只做只读引用，通过 dict_entry_id 关联
- 已有 GET /dict/entry?id={dict_entry_id} 接口可直接复用

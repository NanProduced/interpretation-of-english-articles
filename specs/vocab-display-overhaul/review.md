# Code Review Notes

## Findings

### 1. 生词本详情信息弱于查词弹层

严重程度：高

当前结果页 `WordPopup` 能展示：

- 完整词典释义
- 短语
- 例句
- AI 语境解析

但生词本详情 `VocabDetailView` 只消费本地保存的 `detailMeanings` 和简化字段，信息密度明显下降。

涉及文件：

- [client/src/components/WordPopup/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/WordPopup/index.tsx)
- [client/src/components/VocabDetailView/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/VocabDetailView/index.tsx)
- [client/src/pages/result/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/pages/result/index.tsx)

结论：

- 这是当前生词本体验最核心的问题
- 根因不是 UI，而是保存模型没有稳定引用完整词条
- 解决方案：保存 `dict_entry_id`，详情页通过 `GET /dict/entry` 按需加载完整词条

### 2. 本地与云端去重语义冲突

严重程度：高

本地 `saveVocabEntry()` 按 `lemma + recordId` 去重，云端 `vocabulary_book` 按 `user_id + lemma` 全局唯一。

涉及文件：

- [client/src/services/storage/index.ts](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/services/storage/index.ts)
- [server/db/migrations/0001_initial_schema.sql](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/db/migrations/0001_initial_schema.sql)
- [server/app/services/user_assets/vocabulary.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/user_assets/vocabulary.py)

风险：

- 登录前后行为不一致
- 多篇文章中同 lemma 会在本地重复、在云端折叠
- 来源句和状态很容易被覆盖

解决方案：

- 本地也改为以 `lemma` 为唯一键去重（与云端一致）
- 合并时追加 `source_refs` 而非覆盖
- 云端 upsert 改为追加 `source_refs` + `collected_forms`，而非覆盖来源字段

### 3. "查看原文"链路过于粗糙

严重程度：高

当前生词本直接基于 `recordId` 跳结果页 replay，没有 sentence 级定位，也没有删除态判断。

涉及文件：

- [client/src/pages/vocab/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/pages/vocab/index.tsx)
- [client/src/components/VocabDetailView/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/VocabDetailView/index.tsx)
- [client/src/stores/article.ts](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/stores/article.ts)

风险：

- 用户找不到收藏当时的语境
- record 被删除后仍可能尝试跳转
- 即使跳转成功，也没有定位语句

解决方案：

- 跳转时携带 `sentenceId` 参数
- 结果页 replay mode 下滚动到目标句子
- 跳转前判断记录是否可用（本地 tombstone + 云端 404）

### 4. 离线同步状态设计已经复杂，但未形成真实收益

严重程度：中

`pendingOp / tombstone / syncState` 等状态在生词本逻辑中只被部分消费，没有真正形成完整冲突处理机制。

涉及文件：

- [client/src/pages/vocab/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/pages/vocab/index.tsx)
- [client/src/services/cloudSync.service.ts](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/services/cloudSync.service.ts)

建议：

- 第一版不继续加复杂状态
- 先统一 lemma 语义和 source refs 模型
- 同步逻辑随数据模型一起简化

### 5. 结果页与生词本之间缺少后置联动层

严重程度：中

现在结果页只知道"当前记录里是否已经手动保存过这个词"，不知道"这个词是否在用户整个生词本里"。

涉及文件：

- [client/src/pages/result/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/pages/result/index.tsx)
- [client/src/components/ParagraphBlock/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/ParagraphBlock/index.tsx)

建议：

- 用单独的 vocabulary highlights 接口做 overlay
- 不改 `/analyze`

### 6. 结果页 vocabList 只匹配 surface form，不覆盖词形变化

严重程度：中

`vocabList` 只存储 surface form（如 "running"），不包含 lemma（如 "run"），ParagraphBlock 中 `isSaved` 判断只匹配 surface form。同一词的不同形态（run/running/ran）无法统一标记。

涉及文件：

- [client/src/pages/result/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/pages/result/index.tsx)（第 136-143 行）
- [client/src/components/ParagraphBlock/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/ParagraphBlock/index.tsx)（第 57-81 行）

解决方案：

- Phase B 的 `/vocabulary/highlights` 接口会返回 lemma 级别的匹配结果
- 前端消费 overlay 数据时不再依赖 `vocabList` 的 surface form 匹配

### 7. 云端分页限制

严重程度：低

生词本页面只取第一页 100 条，超过部分不可见。`lite=true` 模式省略了 `meanings_json`、`source_sentence`、`source_context`。

涉及文件：

- [client/src/services/api/vocabulary.client.ts](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/services/api/vocabulary.client.ts)

解决方案：

- 移除 `lite=true`，默认返回完整数据
- 或新增 `lite=enhanced` 模式返回 `source_sentence` 但省略 `meanings_json`

### 8. Schema 新旧字段并存

严重程度：低

`analysis_record_id` / `client_record_id` 已标记 deprecated，但仍在使用。`source_cloud_record_id` / `source_client_record_id` 在 schema 中定义但数据库 migration 中不存在。

解决方案：

- 重建 `vocabulary_book` 表时移除 `analysis_record_id`，统一用 `payload_json.source_refs` 管理来源记录关联
- 不需要向后兼容旧字段

## Architectural Direction

### Good current foundations

- 后端已有 `lemma.py`，可以复用词形归并能力
- vocabulary 表已有 `payload_json`，适合承载扩展 metadata
- 结果页和生词本已经分开，适合走后置 overlay 方案
- 已有 `GET /dict/entry?id={dict_entry_id}` 接口，可直接复用获取完整词条

### Current architectural mismatch

- 数据层在做"全局词条"
- 前端展示层在做"按文章收藏"
- 详情层又退化成"局部快照"

需要统一成：

- 核心词条全局唯一（本地和云端都以 lemma 为唯一键）
- 来源语境多条保留（source_refs 数组）
- 详情按完整词条展示（通过 dict_entry_id 按需加载）
- 结果页通过 overlay 查询联动

## Competitive Analysis Summary

### 竞品核心差异化对比

| 维度 | 竞品最佳实践 | Claread 差异化机会 |
|------|-------------|-------------------|
| 词条展示 | 不背单词的真实语境 + 墨墨的助记法 | AI 增强的语境分析 + 阅读来源追踪 |
| 来源追踪 | 欧路的文章级追踪 | **句子级追踪 + 锚点定位**（独家） |
| 词形归一 | 有道的 lemma 主键 | lemma 主键 + 多形态展示 + 归并通知 |
| 阅读联动 | 欧路的已收藏词标注 | 独立视觉层的 saved-vocab overlay |
| 搜索筛选 | 欧路的强大搜索 | 前缀匹配 + lemma 搜索（够用即可） |
| 视觉设计 | 不背单词的沉浸式美感 | 语境优先的卡片设计 + 批注感 overlay |

### 关键发现

1. **句子级来源追踪是独家能力** — 目前所有主流竞品（扇贝、百词斩、墨墨、不背、欧路、有道、沪江）都没有做到"句子级 + 锚点文本"级别的来源追踪，Claread 的 `source_refs` 设计是明显的差异化优势
2. **语境优先是正确方向** — 不背单词的核心差异化就是"真实语境例句"，Claread 可以更进一步：用户自己的阅读语境比系统提供的语料例句更有记忆价值
3. **归并通知是必要体验** — 墨墨采用"半透明归并"策略，用户能看到归并过程；静默合并会让用户困惑"为什么我收藏的词不见了"
4. **发音是基础能力** — 所有主流竞品都有发音功能，Claread 当前缺失

### 竞品视觉设计模式参考

- **列表页**：建议采用"语境卡片"模式（不背单词风格），而非紧凑列表（扇贝风格），因为 Claread 的核心场景是"阅读后回看"，语境是最高价值信息
- **详情页**：建议采用"分层信息架构"模式（不背单词/墨墨风格），语境区优先于释义区
- **结果页 overlay**：参考欧路词典的"阅读中已收藏词标注"，使用独立视觉层

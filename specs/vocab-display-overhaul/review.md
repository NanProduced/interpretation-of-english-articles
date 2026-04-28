# Code Review Notes

> **审查更新：2026-04-27**
> 原始审查的核心发现"生词本详情弱于查词弹层"、"本地与云端去重语义冲突"、"查看原文链路粗糙"等已大部分解决。当前生词本改造 Phase A 已完成 ~80%，Phase B（搜索/筛选）未开始。本文件已更新为当前状态。

## Findings

### 1. 生词本详情信息已补全

严重程度：信息（原为"高"，已解决）

VocabDetailView 已通过 `dict_entry_id` 调用 `GET /dict/entry` 按需加载完整词条：

- ✅ Hero 区：单词 + 音标 + lemma + 收藏形态标签 + 发音按钮
- ✅ 语境区：横向滑动卡片 + 计数器 + "查看原文"按钮
- ✅ 词典区：释义 / 短语 / 例句 tabs，通过 dictEntryId 加载完整词条
- ✅ Fallback 到本地 `detailMeanings`

涉及文件：

- [client/src/components/VocabDetailView/index.tsx](../../client/src/components/VocabDetailView/index.tsx)

### 2. 本地与云端去重已统一为 lemma 语义

严重程度：信息（原为"高"，已解决）

- ✅ 本地存储已改为以 `lemma` 为唯一键去重（与云端一致）
- ✅ 合并时追加 `source_refs`（去重按 `client_record_id + source_sentence_id`，上限 20 条）
- ✅ 追加 `collected_forms`（去重）
- ✅ 保留 `audio_url`
- ✅ 云端 upsert 改为追加 `source_refs` + `collected_forms`，而非覆盖

涉及文件：

- [client/src/services/storage/index.ts](../../client/src/services/storage/index.ts)
- [server/app/services/user_assets/vocabulary.py](../../server/app/services/user_assets/vocabulary.py) — `_merge_payload_on_conflict()`

### 3. "查看原文"链路已改善

严重程度：信息（原为"高"，已部分解决）

- ✅ 跳转时携带 `sentenceId` 参数
- ✅ 跳转前检查本地 record 是否存在且未 tombstone，不可用时显示"原文记录已删除或不可用"
- ⚠️ 结果页 replay mode 下滚动到目标句子的功能需验证

涉及文件：

- [client/src/components/VocabDetailView/index.tsx](../../client/src/components/VocabDetailView/index.tsx)

### 4. 结果页与生词本后置联动已实现

严重程度：信息（原为"中"，已解决）

- ✅ `POST /vocabulary/highlights` 接口已实现（lemma candidates 匹配 + collected_forms 匹配）
- ✅ 结果页 `useResultState` 中 `vocabHighlights` 状态已接入
- ✅ ParagraphBlock 使用 `vocabSavedMap` 判断 savedStatus

涉及文件：

- [server/app/api/routes/vocabulary.py](../../server/app/api/routes/vocabulary.py)
- [client/src/pages/result/hooks/useResultState.ts](../../client/src/pages/result/hooks/useResultState.ts)
- [client/src/components/ParagraphBlock/index.tsx](../../client/src/components/ParagraphBlock/index.tsx)

### 5. 发音功能已实现

严重程度：信息（原为缺失，已解决）

- ✅ VocabDetailView 使用 Free Dictionary API 获取音频 URL
- ✅ 点击播放 MP3
- ✅ API 不可用时隐藏按钮
- ⚠️ audio_url 仅存在组件 state 中，未见回写 `payload_json.audio_url` 的逻辑（spec 要求缓存避免重复请求）

### 6. vocabulary_book 表结构已改造

严重程度：信息（原为待重建，已完成）

- ✅ 初始 schema 已包含改造后结构：`dict_entry_id`、`payload_json`（含 source_refs / collected_forms）
- ✅ `analysis_record_id` 已移除
- ✅ 唯一索引 `uq_vocabulary_book_user_lemma_lower`
- ✅ 索引 `idx_vocabulary_book_dict_entry_id`

### 7. 待完成项

严重程度：中

| 项目 | 状态 | 说明 |
|------|------|------|
| saved-vocab 独立视觉层 | 未确认 | Spec 要求"批注感"设计（浅色圆角背景+左侧小竖线+淡蓝灰色），需验证 ParagraphBlock CSS 是否符合 |
| 列表页来源数量徽标 | 未确认 | Spec 要求"N 篇"来源数量徽标 + 最近收藏语境句 + "还有 N 个语境" |
| 收藏归并 toast 反馈 | 未确认 | Spec 要求合并时 toast 提示"adopted 已添加到 adopt（第 2 个语境）" |
| audio_url 缓存回写 | 未实现 | audioUrl 仅存在组件 state，未回写 payload_json |
| Phase B 搜索/筛选 | 未实现 | 列表搜索/筛选/字母索引侧边栏完全未开始 |

## Architectural Direction

### Current foundations (updated)

- ✅ 核心词条全局唯一（本地和云端都以 lemma 为唯一键）
- ✅ 来源语境多条保留（source_refs 数组）
- ✅ 详情按完整词条展示（通过 dict_entry_id 按需加载）
- ✅ 结果页通过 overlay 查询联动（/vocabulary/highlights）
- ✅ 后端 `lemma.py` 词形归并能力已复用
- ✅ `GET /dict/entry?id={dict_entry_id}` 接口已复用

### Remaining work

- 验证 saved-vocab 视觉层是否符合 spec 的"批注感"设计
- 实现 audio_url 缓存回写 payload_json
- Phase B：列表搜索/筛选/字母索引侧边栏
- 验证结果页 replay mode 下滚动到目标句子功能

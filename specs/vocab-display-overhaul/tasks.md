# Implementation Plan

## Phase A — 生词本核心体验

### A1. 重建 vocabulary_book 表与后端 API 改造

- [ ] A1.1 新建 migration：重建 `vocabulary_book` 表
  - 新增 `dict_entry_id BIGINT REFERENCES dict_entries(id) ON DELETE SET NULL`
  - 移除 `analysis_record_id UUID`（来源关联统一到 `payload_json.source_refs`）
  - 新增 `idx_vocabulary_book_dict_entry_id` 索引
  - _Requirement: 1, 5_

- [ ] A1.2 扩展 vocabulary schema
  - `VocabularyCreateRequest`：新增 `dict_entry_id`，移除 `analysis_record_id` / `client_id`
  - `VocabularyResponse`：新增 `dict_entry_id`、`source_refs`、`collected_forms`，移除 deprecated 字段
  - _Requirement: 1, 3, 5_

- [ ] A1.3 改造 vocabulary service upsert 逻辑
  - 冲突时追加 `payload_json.source_refs`（而非覆盖来源字段）
  - 追加 `payload_json.collected_forms`（去重）
  - 更新 `meanings_json` 等词条信息（取最新）
  - 更新顶层 `source_sentence` 为最近一次来源
  - `source_refs` 上限 20 条，超出时保留最近 20 条
  - _Requirement: 1, 3_

- [ ] A1.4 更新 vocabulary routes
  - POST `/vocabulary`：接收并传递 `dict_entry_id`、`payload_json`
  - GET `/vocabulary`：返回完整数据（移除 `lite=true` 或改为 `lite=enhanced`）
  - PATCH `/vocabulary/{id}`：保持不变
  - DELETE `/vocabulary/{id}`：保持不变
  - _Requirement: 1, 5_

### A2. 前端存储与同步改造

- [ ] A2.1 扩展 VocabEntry VM 类型
  - 新增 `dictEntryId?: number`
  - 新增 `sourceRefs?: SourceRef[]`
  - 新增 `collectedForms?: string[]`
  - 移除 `cloudRecordId`（移入 `sourceRefs` 内）
  - _Requirement: 1, 3_

- [ ] A2.2 改造本地存储 saveVocabEntry
  - 去重键从 `lemma + recordId` 改为 `lemma`（与云端一致）
  - 合并时追加 `sourceRefs` 而非创建新条目
  - 追加 `collectedForms`（去重）
  - 保存 `dictEntryId`
  - 返回合并结果（用于 toast 反馈）
  - _Requirement: 3_

- [ ] A2.3 更新 vocabulary API client
  - `addVocabToCloud`：传递 `dict_entry_id`、`payload_json`
  - `dtoToVm`：映射 `dict_entry_id`、`source_refs`、`collected_forms`
  - `fetchCloudVocabulary`：移除 `lite=true` 或改为 `lite=enhanced`
  - _Requirement: 1, 3_

- [ ] A2.4 更新云同步逻辑
  - `syncVocab`：传递 `dict_entry_id`、`payload_json`
  - `resolveCurrentVocabId`：按 lemma 查找（本地已只有一条）
  - 简化合并逻辑（本地 lemma 唯一后不再有多条冲突）
  - _Requirement: 3, 5_

### A3. 生词本页面与详情视图升级

- [ ] A3.1 升级 VocabDetailView
  - Hero 区：单词 + 音标 + lemma + 收藏形态标签 + 发音按钮
  - 语境区：来源句子卡片（横向滑动）+ "已收藏于 N 个语境" + "查看原文"按钮
  - 词典区：通过 `dictEntryId` 调 `GET /dict/entry` 加载完整词条，展示释义/短语/例句 tabs
  - 词典不可用时 fallback 到本地 `detailMeanings`
  - 操作区：标记掌握、删除
  - _Requirement: 1, 2, 6_

- [ ] A3.2 实现语境卡片横向滑动
  - 每个卡片：来源句子 + 来源文章标题 + 收藏时间 + "查看原文"按钮
  - 计数器 "1/N"
  - 单条语境时不需要滑动
  - _Requirement: 2_

- [ ] A3.3 实现条件跳转
  - 跳转时携带 `sentenceId` 参数
  - 结果页 replay mode 下滚动到目标句子
  - 跳转前判断记录是否可用（本地 tombstone + 云端 404）
  - 不可用时显示"原文记录已删除或不可用"
  - _Requirement: 2_

- [ ] A3.4 实现发音播放
  - 使用 Free Dictionary API (`GET https://api.dictionaryapi.dev/api/v2/entries/en/{word}`) 获取音频
  - 从 `phonetics[].audio` 筛选第一个有音频 URL 的条目（优先美音）
  - 缓存音频 URL 到 `payload_json.audio_url`，避免重复请求
  - 点击发音按钮播放 MP3
  - API 不可用或无音频时隐藏发音按钮
  - 仅在生词本详情页引入，结果页查词卡片暂不加
  - _Requirement: 6_

- [ ] A3.5 升级生词本列表页
  - 列表卡片：第一行增加来源数量徽标（"N 篇"）
  - 第三行：最近收藏语境句 + "还有 N 个语境"
  - 更新 mergeVocabCloudWithLocal 适配新数据结构
  - _Requirement: 7_

### A4. 收藏流程改造

- [ ] A4.1 改造结果页收藏逻辑
  - 保存时携带 `dictEntryId`（从词典结果获取 `entry.id`）
  - 保存时构造 `sourceRef`（含 `sentenceId`、`anchorText`、`occurrence`）
  - 调用改造后的 `saveVocabEntry`
  - 合并时显示 toast："adopted 已添加到 adopt（第 2 个语境）"
  - 新建时显示 toast："adopted 已记入生词本"
  - _Requirement: 1, 3_

### A5. 验证与收尾

- [ ] A5.1 编译检查
  - Python: 后端 schema / route / service 编译通过
  - TypeScript: `tsc --noEmit` 通过
  - _Requirement: 1, 2, 3, 5_

- [ ] A5.2 手工验证链路
  - 收藏单词 → 生词本详情展示完整词条
  - 同 lemma 再次收藏 → 合并 source_refs + toast 提示
  - 删除原文记录 → 生词详情不跳转 + 提示不可用
  - 详情页发音播放正常
  - 列表页来源数量徽标正确显示
  - _Requirement: 1, 2, 3, 6, 7_

---

## Phase B — 结果页联动与搜索

### B1. 结果页 saved-vocab overlay

- [ ] B1.1 新增 `/vocabulary/highlights` 接口
  - 接收句子列表，返回匹配的 saved-vocab marks
  - 对单词使用 `lemma.py` lemma candidates 匹配
  - 对短语做 exact phrase match
  - 匿名用户使用本地生词数据
  - _Requirement: 4, 5_

- [ ] B1.2 结果页集成 overlay
  - 页面渲染完成后请求 vocabulary highlights（debounce 500ms）
  - 将 overlay 数据传入 ParagraphBlock
  - _Requirement: 4_

- [ ] B1.3 实现 saved-vocab 视觉
  - "批注感"设计：浅色圆角背景 + 左侧小竖线
  - 淡蓝灰色，与现有 `visualTone` 暖色系区分
  - hover/点击态：圆角背景加深 + 小书签图标
  - 不使用下划线
  - _Requirement: 4_

### B2. 列表搜索/筛选

- [ ] B2.1 实现搜索
  - 前缀匹配 + 模糊匹配
  - 搜索支持 lemma 匹配（搜 "adopted" 也能找到 "adopt"）
  - 300ms 防抖
  - _Requirement: 7_

- [ ] B2.2 实现筛选
  - 按掌握状态筛选
  - 按添加时间排序
  - _Requirement: 7_

- [ ] B2.3 字母索引侧边栏（可选）
  - 右侧 A-Z 索引条
  - 快速跳转
  - _Requirement: 7_

### B3. 验证与收尾

- [ ] B3.1 编译检查
- [ ] B3.2 手工验证链路
  - 结果页加载后出现 saved-vocab overlay
  - overlay 视觉与教学注释不冲突
  - 搜索/筛选功能正常
  - 匿名用户 overlay 使用本地数据

---

## 后续预留功能（不在本次范围）

以下功能在本次改造中不做开发，但架构上预留扩展点：

| 功能 | 预留方式 | 预计优先级 |
|------|---------|-----------|
| 复习日程与间隔重复 | `mastery_status` 5 态 + `review_count` + `last_reviewed_at` 字段已存在 | P1 |
| 掌握状态细粒度化 | 当前只用 mastered 布尔值，后续可引入 new → learning → mastered 三态 | P1 |
| AI 助记 | `payload_json` 可扩展 `ai_mnemonic` 字段 | P2 |
| 学习成就与 AI 学习路径分析 | `payload_json` 可扩展学习画像字段 | P2 |
| 独立背词模式 | 架构上与生词本共享数据，不冲突 | P3 |
| 笔记/自定义释义编辑 | `payload_json` 可扩展 `user_notes` 字段 | P2 |
| 批量操作 | 列表页架构支持多选，后续加 UI | P2 |
| 短语学习能力 | `source_refs` 已支持短语来源，`/vocabulary/highlights` 预留 phrase 匹配扩展点 | P2 |
| 本地存储性能优化 | 按 lemma 建立索引 Map，避免全量扫描 | P2 |
| 云端缓存层 | `/vocabulary/highlights` 接口预留缓存策略 | P3 |

# 词典功能问题修复进度 (TEMP)

> 本文档为临时跟踪文件，所有问题修复完成后删除。
> 来源：2026-05-05 词典功能深度评估

---

## P0 — 严重问题

### P0-1：Fragment 派生词查询返回空释义 ✅ 已修复

- **文件**: `server/scripts/import_tecd3.py` / `server/app/services/dictionary/providers/tecd3.py` / `server/app/services/dictionary/db_pg.py`
- **原因**: 导入脚本 `_extract_redirect_target_entry_key()` 只处理 `xrg a.xr`，不处理 `.mdict-parent-link`，导致 `chronically → chronic` 关系丢失；Provider 不过滤空 fragment 候选
- **修复**:
  1. `import_tecd3.py`: 新增 `_extract_parent_link_target()`，空 fragment 走 redirect 通道
  2. `db_pg.py`: `CandidateRow` 增加 `has_meanings` 字段
  3. `tecd3.py`: 候选过滤空 fragment + `word` 字段保留查询词
  4. `backfill_fragment_redirects.py`: 增量修复 33,412 个空 fragment
- **联动修改**: `client/src/components/WordPopup/index.tsx` fragment 兜底文案

### P0-2：生词本保存状态反馈完全失效 ⏳ 待修复

- **文件**: `client/src/pages/result/index.tsx:233-247`
- **原因**: 渲染 `WordPopup` 时未传递 `isSaved` prop，按钮始终显示"记入生词本"
- **修复方向**: 从 vocabList/vocabSavedMap 计算 `isSaved` 并传递

### P0-3：`getLookupSaveState` 缺参数，3 种状态永远不触发 ⏳ 待修复

- **文件**: `client/src/components/WordPopup/index.tsx:153`
- **原因**: 调用 `getLookupSaveState(lookupText, isSaved)` 只传 2 个参数，`currentSentenceId` 和 `savedSourceRefs` 缺失
- **修复方向**: 传入 `currentSentenceId` 和 `savedSourceRefs`，使 `same_lemma_new_context`/`multiple_contexts`/`mastered` 状态可触发

### P0-4：adapter 对未知 result_type 无防御 ⏳ 待修复

- **文件**: `client/src/services/api/adapters/dict.adapter.ts:63-68`
- **原因**: `result_type` 非 `entry` 时走 `mapDisambiguationResult`，但 `dto.candidates` 可能不存在导致崩溃
- **修复方向**: 增加 `else` 分支抛出错误或返回安全默认值；`mapEntryResult`/`mapDisambiguationResult` 增加 null 防御

### P0-5：L1 缓存无淘汰策略，内存无限增长 ⏳ 待修复

- **文件**: `server/app/services/dictionary/cache.py:37-42`
- **原因**: 缓存满且无过期条目时不淘汰，内存持续增长
- **修复方向**: 实现满容量时强制淘汰最旧条目（LRU 或 FIFO）

### P0-6：502 错误暴露内部异常信息 ⏳ 待修复

- **文件**: `server/app/api/routes/dict.py:47`
- **原因**: `detail=f"Dictionary service error: {exc}"` 将原始异常暴露给客户端
- **修复方向**: 返回通用错误信息，详细异常记录到日志

### P0-7：生词本删除操作云端同步静默失败 ⏳ 待修复

- **文件**: `client/src/packageA/vocab/index.tsx:212-214` / `client/src/services/cloudSync.service.ts:291-296`
- **原因**: 先 `removeVocabEntry(entry.id)` 物理删除本地记录，后入队 `DELETE_VOCAB`，执行时 `resolveCurrentVocabId` 在本地找不到词条，返回 null，云端删除被跳过
- **修复方向**: 改为 tombstone 标记而非物理删除，或在同步队列 payload 中保存云端 ID

---

## P1 — 高优先级

### P1-1：`occurrence=0` 被 falsy 判断跳过 ⏳ 待修复

- **文件**: `client/src/services/api/client.ts:376`
- **原因**: `if (occurrence)` 当 `occurrence=0` 时为 falsy，不拼接参数
- **修复方向**: 改为 `if (occurrence !== undefined && occurrence !== null)`

### P1-2：正则 split 未转义特殊字符 ⏳ 待修复

- **文件**: `client/src/components/WordPopup/index.tsx:141`
- **原因**: `new RegExp(`(${lookupText})`, 'gi')` 未转义，查询词含 `.` `?` `*` 时崩溃
- **修复方向**: 添加 `escapeRegExp` 转义函数

### P1-3：请求无竞态保护 ⏳ 待修复

- **文件**: `client/src/components/WordPopup/index.tsx:160-163`
- **原因**: 快速切换单词时旧响应可能覆盖新结果
- **修复方向**: 使用请求版本号或 AbortController

### P1-4：InnerAudioContext 未销毁导致内存泄漏 ⏳ 待修复

- **文件**: `client/src/components/VocabDetailView/index.tsx:98-102`
- **原因**: 每次播放创建新 `InnerAudioContext` 但从不调用 `destroy()`
- **修复方向**: 在 `onEnded`/`onError` 回调中调用 `innerAudio.destroy()`

### P1-5：WordPopup 无发音播放按钮 ⏳ 需设计

- **文件**: `client/src/components/WordPopup/index.tsx`
- **原因**: mini/full 模式都无发音按钮，VocabDetailView 有实现但依赖海外 API
- **状态**: 需设计发音方案（TTS API / 本地音频资源）

### P1-6：NER 禁用导致 phrase_templates 的 sb/sth 分类失效 ⏳ 待修复

- **文件**: `server/app/services/dictionary/nlp.py:39` / `server/app/services/dictionary/phrase_templates.py:29`
- **原因**: nlp.py 禁用了 NER（`disable=["ner"]`），但 phrase_templates.py 依赖 `root.ent_type_ == "PERSON"` 判断 sb 槽位
- **修复方向**: 在词典专用 pipeline 中启用 NER，或改用依存关系/词表判断 sb

### P1-7：phrase_candidates 多匹配时丢失依存分析候选 ⏳ 待修复

- **文件**: `server/app/services/dictionary/phrase_candidates.py:59-64`
- **原因**: `occurrence is None` 且同一词出现多次时，直接返回空列表
- **修复方向**: 多匹配时为每个匹配分别生成候选，或选择第一个匹配

### P1-8：子树 span 包含不连续 token 间无关词 ⏳ 待修复

- **文件**: `server/app/services/dictionary/phrase_candidates.py:80-84`
- **原因**: `doc[start:end]` 包含 start 到 end 之间所有 token，不仅是 subtree 中的
- **修复方向**: 只使用 subtree 中的 token 拼接，跳过中间无关词

### P1-9：spaCy 可用性只检查一次无法恢复 ⏳ 待修复

- **文件**: `server/app/services/dictionary/nlp.py:15-31`
- **原因**: `_dict_spacy_checked = True` 后永不重新检查，启动时模型不可用则整个生命周期 NLP 禁用
- **修复方向**: 添加重试机制或定期重新检查选项

### P1-10：数据库不可用时返回 404 而非 503 ⏳ 待修复

- **文件**: `server/app/services/dictionary/db_pg.py:105-106`
- **原因**: `DB_POOL is None` 时 `fetch_entry` 返回 None，调用方视为"词不存在"
- **修复方向**: 抛出特定异常，API 层返回 503

---

## P2 — 中优先级

### P2-1：缓存穿透——不存在的词不缓存 ⏳ 待修复

- **文件**: `server/app/services/dictionary/providers/tecd3.py`
- **原因**: 查不到词时抛 ValueError 不缓存，重复查询走完整流程
- **修复方向**: 缓存"未找到"标记（短 TTL）

### P2-2：`LookupError` 与 Python 内置同名 ⏳ 待修复

- **文件**: `server/app/services/dictionary/service.py:12`
- **修复方向**: 改名为 `DictLookupError` 或 `WordNotFoundError`

### P2-3：`handleFavorite`/`onFavorite` 死代码 ⏳ 待清理

- **文件**: `client/src/components/WordPopup/index.tsx:118-121`
- **修复方向**: 删除未使用的 `handleFavorite` 函数和 `onFavorite` prop

### P2-4：关闭弹窗不清空 dictResult ⏳ 待修复

- **文件**: `client/src/components/WordPopup/index.tsx:206`
- **修复方向**: `visible` 变为 false 时清空 `dictResult` 状态

### P2-5：contextSentence 通过 URL 传递可能超长 ⏳ 待修复

- **文件**: `client/src/services/api/client.ts:375`
- **修复方向**: 改为 POST 请求体传递

### P2-6：多设备 mastered 状态覆盖 ⏳ 需设计

- **文件**: `client/src/packageA/vocab/index.tsx:73`
- **原因**: 合并时本地优先，可能覆盖其他设备的更新状态
- **状态**: 需设计冲突解决策略

### P2-7：vocabList 使用数组 includes 性能差 ⏳ 待修复

- **文件**: `client/src/pages/result/hooks/useResultState.ts:26`
- **修复方向**: 改用 Set 数据结构

### P2-8：快照 vs 实时数据混合无区分 ⏳ 需设计

- **文件**: `client/src/components/VocabDetailView/index.tsx:120-126`
- **原因**: 详情页优先用实时词典数据，与收藏时快照可能不同
- **状态**: 需设计区分提示或统一策略

---

## P3 — 低优先级

### P3-1：`_l1_get` 中删除过期条目无锁保护 ⏳ 待修复

- **文件**: `server/app/services/dictionary/cache.py:28-29`

### P3-2：`SELECT *` 查询脆弱 ⏳ 待修复

- **文件**: `server/app/services/dictionary/db_pg.py:109-112`

### P3-3：`_build_entry_result` 中 base_word 赋值逻辑疑似无效操作 ⏳ 待验证

- **文件**: `server/app/services/dictionary/providers/tecd3.py:223-226`

### P3-4：消歧列表点击后闪烁无平滑过渡 ⏳ 待优化

- **文件**: `client/src/components/WordPopup/index.tsx:386-397`

### P3-5：列表使用 index 作为 key ⏳ 待修复

- **文件**: `client/src/components/WordPopup/index.tsx:402,424,434`

### P3-6：弹窗缺少 ARIA 属性和焦点管理 ⏳ 待修复

- **文件**: `client/src/components/WordPopup/index.tsx:235`

### P3-7：`fetchDictEntry` 返回类型过窄 ⏳ 待修复

- **文件**: `client/src/services/api/client.ts:383-386`

### P3-8：phrase_templates canonicalize 正则替换顺序问题 ⏳ 待修复

- **文件**: `server/app/services/dictionary/phrase_templates.py:13-15`

### P3-9：单 token span 返回 text 而非 lemma ⏳ 待修复

- **文件**: `server/app/services/dictionary/phrase_templates.py:51-52`

### P3-10：N-gram fallback 只生成 lemma 形式 ⏳ 待修复

- **文件**: `server/app/services/dictionary/phrase_candidates.py:205`

---

## 修复日志

| 日期 | 问题 | 操作 |
|------|------|------|
| 2026-05-05 | P0-1 | import_tecd3.py: 新增 `_extract_parent_link_target()`，空 fragment 走 redirect 通道 |
| 2026-05-05 | P0-1 | db_pg.py: `CandidateRow` 增加 `has_meanings` 字段 |
| 2026-05-05 | P0-1 | tecd3.py: 候选过滤空 fragment + `word` 字段保留查询词 + cache_version v3→v4 |
| 2026-05-05 | P0-1 | WordPopup: fragment 兜底文案"派生词，查看主词条" |
| 2026-05-05 | P0-1 | backfill_fragment_redirects.py: 增量修复 33,412 个空 fragment redirect 记录 |

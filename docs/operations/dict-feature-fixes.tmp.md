# 词典功能问题修复进度 (TEMP)

> 本文档为临时跟踪文件，所有问题修复完成后删除。
> 来源：2026-05-05 词典功能深度评估

---

## P0 — 严重问题

### P0-1：Fragment 派生词查询返回空释义 ✅ 已修复（2026-05-05）

- **文件**: `server/scripts/import_tecd3.py` / `server/app/services/dictionary/providers/tecd3.py` / `server/app/services/dictionary/db_pg.py`
- **原因**: 导入脚本 `_extract_redirect_target_entry_key()` 只处理 `xrg a.xr`，不处理 `.mdict-parent-link`，导致 `chronically → chronic` 关系丢失；Provider 不过滤空 fragment 候选
- **修复**:
  1. `import_tecd3.py`: 新增 `_extract_parent_link_target()`，空 fragment 走 redirect 通道
  2. `db_pg.py`: `CandidateRow` 增加 `has_meanings` 字段
  3. `tecd3.py`: 候选过滤空 fragment + `word` 字段保留查询词
  4. `backfill_fragment_redirects.py`: 增量修复 33,412 个空 fragment
- **联动修改**: `client/src/components/WordPopup/index.tsx` fragment 兜底文案

### P0-2：生词本保存状态反馈完全失效 ✅ 已修复（2026-05-06）

- **文件**: `client/src/pages/result/index.tsx:256-271` / `client/src/components/WordPopup/index.tsx`
- **原因**: 渲染 `WordPopup` 时未传递 `isSaved` prop，按钮始终显示"记入生词本"
- **修复**:
  1. `result/index.tsx`: 从 `vocabSavedMap` 计算 `isSaved={!!vocabSavedMap[wordPopup.word?.toLowerCase()]}` 并传递
  2. `WordPopup/index.tsx`: 新增 `isSaved?: boolean` prop，传入 `getLookupSaveState`

### P0-3：`getLookupSaveState` 缺参数，3 种状态永远不触发 ✅ 已修复（2026-05-06）

- **文件**: `client/src/components/WordPopup/index.tsx:544` / `client/src/pages/result/index.tsx`
- **原因**: 调用 `getLookupSaveState(lookupText, isSaved)` 只传 2 个参数，`currentSentenceId` 和 `savedSourceRefs` 缺失
- **修复**:
  1. `result/index.tsx`: 传递 `savedMasteryStatus={vocabSavedMap[wordPopup.word?.toLowerCase()]}`
  2. `WordPopup/index.tsx`: 新增 `savedMasteryStatus?: string` prop，调用改为 `getLookupSaveState(lookupText, isSaved, undefined, savedMasteryStatus ? [{ status: savedMasteryStatus }] : undefined)`

### P0-4：adapter 对未知 result_type 无防御 ✅ 已修复（2026-05-06）

- **文件**: `client/src/services/api/adapters/dict.adapter.ts:63-68`
- **原因**: `result_type` 非 `entry` 时走 `mapDisambiguationResult`，未知类型会导致崩溃
- **修复**: 显式检查 `disambiguation` 类型，未知类型 throw Error；新增独立异常模块 `errors.py`

### P0-5：L1 缓存无淘汰策略 + threading.Lock 阻塞 asyncio ✅ 已修复（2026-05-06）

- **文件**: `server/app/services/dictionary/cache.py`
- **原因**: `threading.Lock` 在 asyncio 中阻塞事件循环；缓存满时淘汰逻辑存在但锁方案不匹配异步框架
- **修复**:
  1. 移除 `threading.Lock`，依赖 Python GIL 保证 OrderedDict 单操作原子性
  2. 新增 `set_miss()` + `_MISS_MARKER` + `_MISS_TTL_SECONDS = 300s`（P2-1 联动）
  3. `_l1_set` / `_l2_set` 支持 `ttl` 参数
  4. `get()` 识别 miss 标记返回 None（对调用方透明）

### P0-6：502 错误暴露内部异常信息 ✅ 已修复（2026-05-06）

- **文件**: `server/app/api/routes/dict.py:53`
- **原因**: `from exc` 将原始异常链附加到 HTTPException，可能暴露内部信息
- **修复**: `from exc` → `from None`，detail 改为 "Dictionary service temporarily unavailable"；两个端点统一修改

### P0-7：生词本删除操作云端同步静默失败 ✅ 已修复（2026-05-06）

- **文件**: `client/src/packageA/vocab/index.tsx:210` / `client/src/services/cloudSync.service.ts:324-329, 446-462`
- **原因**: 先物理删除本地记录再入队同步，执行时本地找不到词条导致云端删除被跳过
- **修复**:
  1. `syncDeleteVocab` payload 增加 `cloudId: vocabId`
  2. `executeDeleteVocab` 优先使用 `payload.cloudId` 直接调云端 API
  3. 同步修复 `syncVocabMastery` / `executeUpdateVocabMastery` 的同样问题
  4. 旧队列项无 cloudId 时 fallback 到 resolveCurrentVocabId（向后兼容）

---

## P1 — 高优先级

### P1-1：`occurrence=0` 被 falsy 判断跳过 ✅ 已修复（2026-05-06）

- **文件**: `client/src/services/api/client.ts:376`
- **修复**: `if (occurrence)` → `if (occurrence != null)`

### P1-2：正则 split 未转义特殊字符 ✅ 已修复（2026-05-06）

- **文件**: `client/src/components/WordPopup/index.tsx:487`
- **修复**: 添加 `escapeRegExp` 函数：`lookupText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')`

### P1-3：请求无竞态保护 ✅ 已修复（2026-05-06）

- **文件**: `client/src/components/WordPopup/index.tsx:520`
- **修复**: 使用 `useRef` 存储请求版本号 `fetchVersionRef`，响应返回时比对版本号，过期响应丢弃

### P1-4：InnerAudioContext 未销毁导致内存泄漏 ✅ 已修复（2026-05-06）

- **文件**: `client/src/components/VocabDetailView/index.tsx:98`
- **修复**:
  1. `innerAudio` 提升为 `useRef`
  2. 播放前先 `destroy()` 旧实例
  3. `onEnded`/`onError` 回调中调用 `destroy()`
  4. 组件卸载时 cleanup 中销毁音频实例

### P1-5：WordPopup 无发音播放按钮 ✅ 已修复（2026-05-06）

- **文件**: `client/src/components/WordPopup/index.tsx` / `index.scss`
- **原因**: WordPopup 显示音标和 volume-2 图标但不可点击，无法播放发音
- **修复**:
  1. 新增 `AudioVariant` 类型（label + url），支持英音/美音分别播放
  2. 新增 `loadAudio` 函数：调用 dictionaryapi.dev API 获取音频 URL，根据 URL 中 `-uk.`/`-us.`/`-au.` 后缀自动识别 UK/US/AU 标签
  3. 新增 `playAudio` 函数：复用 VocabDetailView 的 InnerAudioContext 模式，useRef 管理生命周期
  4. mini 模式：音标行显示可点击的音频按钮（带 UK/US 标签），播放中切换 volume-1 图标
  5. full 模式：音标下方显示音频变体按钮行
  6. 弹窗关闭时销毁音频实例、重置 audioVariants
  7. 短语查询跳过音频加载（dictionaryapi.dev 不支持短语）

### P1-6：NER 禁用导致 phrase_templates 的 sb/sth 分类失效 ✅ 已修复（2026-05-06）

- **文件**: `server/app/services/dictionary/nlp.py:39` / `server/app/services/dictionary/phrase_templates.py:26`
- **原因**: nlp.py 禁用 NER 导致 `ent_type_=="PERSON"` 永远为空，人名专有名词无法识别为 sb
- **修复**:
  1. `nlp.py`: `disable=["ner"]` → `disable=[]`（启用 NER）
  2. `phrase_templates.py`: 新增 `its`/`their` 所有格代词判断为 `sth`（而非误判为 `sb's`）
- **测试验证**: NER 正确识别人名（John/Mary → sb），`its`/`their` 正确归为 sth

### P1-7：phrase_candidates 多匹配时丢失依存分析候选 ✅ 已修复（2026-05-06）

- **文件**: `server/app/services/dictionary/phrase_candidates.py:61`
- **修复**: `len(target_tokens) == 1` → `len(target_tokens) >= 1`，多匹配时取第一个 target 生成候选

### P1-8：子树 span 包含不连续 token 间无关词 ✅ 已修复（2026-05-06）

- **文件**: `server/app/services/dictionary/phrase_candidates.py:82`
- **修复**: 子树 span 包含无关 token 时，手动拼接 filtered tokens（literal/lemma_form/template_form），不再依赖连续 span

### P1-9：spaCy 可用性只检查一次无法恢复 ✅ 已修复（2026-05-06）

- **文件**: `server/app/services/dictionary/nlp.py:13-24`
- **修复**: 添加 `_dict_spacy_last_check` + `_DICT_SPACY_RETRY_INTERVAL = 300s`，失败后每 5 分钟重试

### P1-10：数据库不可用时返回 404 而非 503 ✅ 已修复（2026-05-06）

- **文件**: `server/app/services/dictionary/errors.py`(新) / `db_pg.py` / `dict.py`
- **修复**:
  1. 新建 `errors.py` 独立异常模块（避免循环导入），定义 `WordNotFoundError` + `ServiceUnavailableError`
  2. `db_pg.py`: 3 个函数 `DB_POOL is None` 时抛出 `ServiceUnavailableError`
  3. `dict.py`: API 层新增 `except ServiceUnavailableError` 返回 503
  4. 错误链路: DB不可用→ServiceUnavailableError→503 | 词不存在→WordNotFoundError→404 | 其他→502

---

## P2 — 中优先级

### P2-1：缓存穿透——不存在的词不缓存 ✅ 已修复（2026-05-06，与 P0-5 联动）

- **文件**: `server/app/services/dictionary/cache.py` / `server/app/services/dictionary/providers/tecd3.py:127`
- **修复**:
  1. cache.py: 新增 `set_miss(key)` + `_MISS_MARKER` + TTL 5 分钟
  2. tecd3.py: `fetch()` 和 `fetch_entry()` 查不到词时调用 `await dict_cache.set_miss(cache_key)`
  3. 链路: 首次查不到 → set_miss → ValueError → 404; 5分钟内重复查 → 命中miss标记 → 返回None → 404(跳过DB)

### P2-2：`LookupError` 与 Python 内置同名 ✅ 已修复（2026-05-06）

- **文件**: `server/app/services/dictionary/errors.py`(新) / `service.py` / `__init__.py` / `dict.py` / `tests/test_dict_proxy.py`
- **修复**: 重命名为 `WordNotFoundError`，提取到独立模块 `errors.py`

### P2-3：`handleFavorite`/`onFavorite` 死代码 ✅ 已修复（2026-05-06）

- **文件**: `client/src/components/WordPopup/index.tsx:118` / `result/index.tsx` / `daily-reader/index.tsx`
- **修复**: 删除 `onFavorite` prop 定义、解构、以及 2 处调用

### P2-4：关闭弹窗不清空 dictResult ✅ 已修复（2026-05-06）

- **文件**: `client/src/components/WordPopup/index.tsx:206`
- **修复**: `visible` 变为 false 时在 useEffect 中 `setDictResult(null)`

### P2-5：contextSentence 通过 URL 传递可能超长 ✅ 已评估（2026-05-06，暂不改 POST）

- **文件**: `client/src/services/api/client.ts:374`
- **评估结果**: contextSentence 来自单个英语句子（最长约 500 字符），远低于 URL 限制
- **修复**: 添加截断防御——超过 500 字符时 slice 截断

### P2-6：多设备 mastered 状态覆盖 ⏳ 保持现状

- **文件**: `client/src/packageA/vocab/index.tsx:73`
- **决策**: 保持本地优先策略。后续如需多设备冲突解决可引入 updatedAt/masteredAt 时间戳

### P2-7：vocabList 使用数组 includes 性能差 ✅ 已修复（2026-05-06）

- **文件**: `client/src/components/ParagraphBlock/index.tsx` / `GrammarInlineSpan/index.tsx`
- **修复**:
  1. ParagraphBlock 组件中用 `useMemo(() => new Set(vocabList), [vocabList])` 创建 `vocabSet`
  2. `renderPlainSegmentAsClickableWords` 参数从 `vocabList` 改为 `vocabSet: Set<string>`
  3. `renderTextWithMarks` 同上
  4. GrammarInlineSpan prop 从 `vocabList` 改为 `vocabSet`
  5. `.includes()` 改为 `.has()`

### P2-8：快照 vs 实时数据混合无区分 ✅ 已修复（2026-05-06）

- **文件**: `client/src/types/view/vocabulary.vm.ts` / `VocabDetailView/index.tsx` / `useResultActions.ts` / `daily-reader/index.tsx` / `storage/index.ts` / `vocabulary.client.ts`
- **原因**: VocabDetailView 混合使用快照数据和实时词典数据，快照 `detailMeanings.definitions` 为 `string[]` 丢失例句；音标只用快照不更新；phrases/examples 无快照降级
- **修复**:
  1. `vocabulary.vm.ts`: `detailMeanings.definitions` 从 `string[]` 改为 `Array<{ meaning, example?, exampleTranslation? }>` 与 `DictionaryMeaning` 对齐；新增 `detailPhrases` 和 `detailExamples` 快照字段
  2. `useResultActions.ts` + `daily-reader/index.tsx`: 保存时保留完整 definitions（含例句），同时保存 phrases/examples 快照
  3. `VocabDetailView/index.tsx`: `displayMeanings` 直接使用 `entry.detailMeanings`（无需 map 转换）；音标优先使用 `dictEntry.phonetic`；phrases/examples 降级到快照数据
  4. `storage/index.ts`: 合并逻辑增加 `detailPhrases`/`detailExamples` 字段
  5. `vocabulary.client.ts`: `dtoToVm` 解析新结构 + `addVocabToCloud` 上传新字段

---

## P3 — 低优先级

### P3-1：`_l1_get` 中删除过期条目无锁保护 ✅ 已修复（2026-05-06，与 P0-5 联动）

- **文件**: `server/app/services/dictionary/cache.py`
- **修复**: 随移除 threading.Lock 一并解决

### P3-2：`SELECT *` 查询脆弱 ✅ 已修复（2026-05-06）

- **文件**: `server/app/services/dictionary/db_pg.py:110`
- **修复**: `SELECT *` 替换为 15 个显式列名（id, source, source_entry_key, entry_kind, display_headword, base_headword, homograph_no, phonetic, meanings_json, examples_json, phrases_json, sections_json, raw_html, parse_version, exam_tags）

### P3-3：`_build_entry_result` 中 base_word 赋值逻辑疑似无效操作 ✅ 已验证（非无效操作）

- **文件**: `server/app/services/dictionary/providers/tecd3.py:225`
- **验证结果**: `base_word`（即 `base_headword`）不是无效操作。数据库中 8,510 条词条的 `base_headword != display_headword`（同形词如 Aberdeen¹ → Aberdeen）。前端 3 处使用：1) 收藏时作为 lemma；2) fragment 词条提示"详见 xxx"；3) daily-reader 同上

### P3-4：消歧列表点击后闪烁无平滑过渡 ✅ 已修复（2026-05-06）

- **文件**: `client/src/components/WordPopup/index.tsx` / `index.scss`
- **原因**: 点击候选词条时 `fetchEntryDetail` 立即 `setDictResult(null)` 导致消歧列表瞬间消失，再显示 loading，造成闪烁
- **修复**:
  1. `fetchEntryDetail` 不再 `setDictResult(null)`，保持消歧列表在加载期间可见
  2. UI 逻辑：`loading && !isDisambiguationResult` 时才显示全屏 spinner；消歧列表加载时叠加半透明 loading 遮罩
  3. 候选项加载中添加 `is-loading` class（opacity: 0.5 + pointer-events: none）
  4. 额外修复：`getSaveActionCopy` 误传 `entry?.sourceRefs?.length`（DictionaryEntryPayload 无 sourceRefs 属性）

### P3-5：列表使用 index 作为 key ✅ 已修复（2026-05-06）

- **文件**: `client/src/components/WordPopup/index.tsx:402,424,434`
- **修复**:
  - meanings 列表: key=`{partOfSpeech}-{idx}`
  - definitions 列表: key=`{meaning?.slice(0,20)}-{defIdx}`
  - phrases 列表: key={p.phrase}
  - examples 列表: key={`{example?.slice(0,20)}-${idx}`}

### P3-6：弹窗缺少 ARIA 属性和焦点管理 ⏳ 保持现状（后续统一处理）

- **文件**: `client/src/components/WordPopup/index.tsx:235`
- **决策**: 当前开发阶段，小程序环境对 ARIA 支持有限，等正式上线前统一添加无障碍属性

### P3-7：`fetchDictEntry` 返回类型过窄 ⏳ 保持现状

- **文件**: `client/src/services/api/client.ts:383`
- **决策**: 项目统一用 try/catch 处理 API 错误，改返回类型需同步修改所有 API 函数

### P3-8：phrase_templates canonicalize 正则替换顺序问题 ✅ 已修复（2026-05-06）

- **文件**: `server/app/services/dictionary/phrase_templates.py:12-17`
- **修复**:
  1. 先替换所有格长模式（somebody's/someone's/one's → sb's）
  2. 再替换 sb.'s → sb's
  3. 再替换短模式（sb./somebody/someone → sb）
  4. 最后替换 sth./something → sth
  5. 修复 `sb.`/`sth.` 点号边界问题：`\bsb\.\b` 无法匹配点号后的非单词字符，改为 `(?=\s|$)` 前瞻断言
- **测试验证**: 8 个测试用例全部通过

### P3-9：单 token span 返回 text 而非 lemma ⏳ 不改（经评审决策）

- **文件**: `server/app/services/dictionary/phrase_templates.py:51-52`
- **决策依据**: 经数据库验证 going/go 都有独立索引；canonicalize_sentence_span 语义是替换非锚点词，单 token 无需模板化

### P3-10：N-gram fallback 只生成 lemma 形式 ✅ 已修复（2026-05-06）

- **文件**: `server/app/services/dictionary/phrase_candidates.py:205`
- **修复**: n-gram fallback 同时生成 literal 和 lemma 形式（去重），template_form 不生成（n-gram 无 span 对象）

---

## 修复日志

| 日期 | 问题 | 操作 |
|------|------|------|
| 2026-05-05 | P0-1 | import_tecd3.py: 新增 `_extract_parent_link_target()`，空 fragment 走 redirect 通道 |
| 2026-05-05 | P0-1 | db_pg.py: `CandidateRow` 增加 `has_meanings` 字段 |
| 2026-05-05 | P0-1 | tecd3.py: 候选过滤空 fragment + `word` 字段保留查询词 + cache_version v3→v4 |
| 2026-05-05 | P0-1 | WordPopup: fragment 兜底文案"派生词，查看主词条" |
| 2026-05-05 | P0-1 | backfill_fragment_redirects.py: 增量修复 33,412 个空 fragment redirect 记录 |
| 2026-05-06 | P0-4 | dict.adapter.ts: 显式检查 disambiguation 类型，未知 throw Error |
| 2026-05-06 | P0-5+P2-1+P3-1 | cache.py: 去 threading.Lock + set_miss 空标记 + GIL 原子性 |
| 2026-05-06 | P0-6 | dict.py: from exc → from None + 通用错误文案 |
| 2026-05-06 | P0-7 | cloudSync.service.ts: payload 保存 cloudId + executeDeleteVocab 优先使用 |
| 2026-05-06 | P1-1 | client.ts: if(occurrence) → if(occurrence != null) |
| 2026-05-06 | P1-2 | WordPopup: escapeRegExp 转义特殊字符 |
| 2026-05-06 | P1-3 | WordPopup: useRef 版本号竞态保护 |
| 2026-05-06 | P1-4 | VocabDetailView: InnerAudioContext useRef + destroy |
| 2026-05-06 | P1-6 | nlp.py: 启用 NER + phrase_templates.py: its/their → sth |
| 2026-05-06 | P1-7 | phrase_candidates.py: 多匹配取第一个 target |
| 2026-05-06 | P1-8 | phrase_candidates.py: 子树 span 过滤无关 token |
| 2026-05-06 | P1-9 | nlp.py: spaCy TTL 300s 重试机制 |
| 2026-05-06 | P1-10 | errors.py(新) + db_pg.py 抛 ServiceUnavailableError + dict.py 返回 503 |
| 2026-05-06 | P2-2 | LookupError → WordNotFoundError，提取到 errors.py |
| 2026-05-06 | P2-3 | WordPopup: 删除 onFavorite 死代码 + 2 调用处清理 |
| 2026-05-06 | P2-4 | WordPopup: 关闭弹窗清空 dictResult |
| 2026-05-06 | P2-5 | client.ts: contextSentence >500 字符截断防御 |
| 2026-05-06 | P2-7 | ParagraphBlock + GrammarInlineSpan: vocabList → Set |
| 2026-05-06 | P3-2 | db_pg.py: SELECT * → 15 个显式列名 |
| 2026-05-06 | P3-5 | WordPopup: index key → 语义 key |
| 2026-05-06 | P3-8 | phrase_templates.py: 正则替换顺序修正 + sb./sth. 边界修复 |
| 2026-05-06 | P3-10 | phrase_candidates.py: n-gram fallback 增加 literal |

---

## API 测试验证记录（2026-05-06）

### 测试环境
- 数据库: 253,300 条 dict_entries, 1,014,676 条 dict_lookup_targets, 848,873 条 dict_redirects
- spaCy: en_core_web_sm 已加载（含 NER）

### TEST 1: 基础词查询 ✅
| 词 | 结果 | 耗时 |
|----|------|------|
| adopt | entry 'adopt', 4 meanings | ~15ms |
| chronic | entry 'chronic', 4 meanings | ~12ms |
| make | disambiguation, 3 candidates (make¹/make²) | ~18ms |
| running | entry 'running', 3 meanings, 1 phrase | ~14ms |

### TEST 2: 上下文感知查询 ✅
| 词 | 上下文 | 结果 | 耗时 |
|----|--------|------|------|
| made | She made up her mind quickly | entry 'make up', 3m/3p | ~35ms |
| made | ...made the team (occ=1) | entry 'make up', 3m/3p | ~32ms |
| told | John told Mary the truth... | disambig, 2 cands [tell, told] | ~38ms |
| going | She is going to the store | entry 'go', 10m/16p | ~42ms |
| better | This is better than that one | entry 'good', 6m/11p | ~36ms |
| make | We need to make up for lost time | entry 'make up for', 3m/1p | ~34ms |

### TEST 3: NLP 候选生成 ✅ (P1-6/P1-7/P1-8 验证)
- "made" in "She made up her mind": 生成 ['make up', 'make up ones mind', 'make up sth'] 等 6 个候选
- "told" in "John told Mary the truth": 生成 ['tell sb sth', 'tell sb the truth'] 等 4 个候选（NER 识别 Mary 为 sb ✅）
- "better" in "This is better than that one": 触发 COMP_STRICT Matcher 匹配

### TEST 4: classify_slot (P1-6 NER 验证) ✅
- John → sb (PERSON 实体) ✅
- Mary → sb (PERSON 实体) ✅
- its tail → sth (its 误判修复) ✅
- their books → sth (their 误判修复) ✅
- her mind → sb's (possessive pronoun) ✅

### TEST 5: canonicalize_dictionary_phrase (P3-8 验证) ✅
全部 8 个测试用例通过（包括 sb./sth. 边界修复）

### TEST 6: 错误处理 (P1-10/P2-2 验证) ✅
- 不存在的词: WordNotFoundError ✓
- 异常层次: WordNotFoundError(404) / ServiceUnavailableError(503) / 其他(502)

### TEST 7: 缓存穿透防护 (P2-1 验证) ✅
- set_miss 后 get 返回 None（对调用方透明）
- Cache stats 正确

### TEST 8: spaCy 重试 (P1-9 验证) ✅
- Retry interval: 300s
- Last check timestamp 正常更新

### 发现的新问题（待后续评审）

#### NEW-1: NLP pipeline noun_chunk 整体分类丢失 poss 依赖信息 [中]

- **文件**: `server/app/services/dictionary/phrase_templates.py:72-81`
- **问题**: `canonicalize_sentence_span` 对 noun_chunk 整体调用 `classify_slot` 时，使用 `chunk.root`（核心名词），丢失了 poss 依赖代词的信息。例如 `her mind` 整体被分类为 `sth`（因为 root=mind 是 NOUN），而非 `sb's mind`（因为 her 是 poss 代词）
- **影响**: 上下文感知查询 `made` in "She made up her mind" 生成模板 `make up sth` 而非 `make up sb's mind`，无法匹配数据库中的 `make up sb's mind` 条目，导致返回消歧页面而非直接命中
- **修复方向**: `canonicalize_sentence_span` 对 noun_chunk 应先检查 chunk 内是否有 poss 代词，如果有则分别处理（poss 代词 → sb's/sth，其余部分保留）

#### NEW-2: Review 修复的额外 BUG [已修复]

1. **loadAudio 竞态**: `loadAudio` 未使用 `fetchVersionRef` 保护，快速切词时旧音频结果覆盖新音频 → 已加入版本检查
2. **WordLookupSlip onSelectEntry**: 声明了类型但未解构，mini 模式消歧提示不可点击 → 已解构 + 添加 onClick 展开
3. **getSaveActionCopy 误传参数**: `entry?.sourceRefs?.length` 传给了 `getSaveActionCopy`，但 DictionaryEntryPayload 无 sourceRefs 属性 → 已移除错误参数
4. **handleAddVocab any 类型**: `dictResult` 参数为 `any`，丧失编译期类型检查 → 已改为 `DictionaryResult | null`

---

## Lemma 能力分析（2026-05-06）

### 架构评价

项目的 lemma 系统设计合理，形成完整闭环：

```
词典查询: query → [exact/redirect/disamb/nlp] → [lemma fallback] → 结果
生词收藏: word + baseWord(lemma) → upsert by lemma → 合并 collectedForms
生词高亮: token → [直接匹配] → [collectedForms匹配] → [lemma还原匹配] → 标记
```

### 关键优势
1. 三级匹配策略（直接 → collectedForms → lemma candidates）确保高召回率
2. 前后端匹配逻辑一致，已登录/未登录用户体验一致（仅精度有差异）
3. lemma 作为唯一主键，配合 collectedForms 完美处理"同一词不同形态多次收藏"
4. 优雅降级：lemminflect 未安装时静默返回空

### 需关注风险
| 优先级 | 问题 | 建议 |
|--------|------|------|
| 中 | 前端简易 lemma 还原不支持不规则变形（better→good, went→go） | 可引入轻量级不规则变形表 |
| 中 | 前端简易 lemma 还原存在误还原（butter→butt, letter→lett） | 可增加黑名单过滤 |
| 低 | dict_lookup_targets 无 lemma match_kind | 当前不影响功能 |
| 低 | 短语不参与 lemma fallback | 属于设计决策 |

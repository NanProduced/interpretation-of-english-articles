# 词典与生词功能优化进度 (TEMP)

> 本文档为临时跟踪文件，用于推进 Claread 透读小程序词典、点词查询、解析页查词交互和生词本优化。所有问题修复完成并沉淀到正式文档后删除。
>
> 创建时间：2026-05-10

---

## 范围

本轮覆盖：

- 词典 API 与点词查询逻辑：lemma、单词查询、短语查询、语境短语嗅探、候选重排
- TECD3 MDX 导入到 PostgreSQL 的词典数据链路
- 解析页 `WordPopup` mini slip、dictionary sheet、保存状态与反馈
- 生词本列表、详情、语境来源、lemma 合并、结果页 saved-vocab overlay
- 其他词典/生词相关体验、数据质量和工程风险

参考文档：

- `docs/architecture/dictionary-service-architecture.md`
- `docs/uiux/reading-annotation-system/word-lookup-and-vocabulary-ux.md`
- `specs/vocab-display-overhaul/`

---

## 当前基线

### 已具备能力

- `/dict` 支持 `q/type/context_sentence/occurrence`，后端通过 TECD3 provider 执行查词。
- 查询策略已包含语境短语候选、直接查询、lemma fallback、候选重排和 L1/L2 缓存。
- 词典运行时真源为 PostgreSQL：`dict_entries`、`dict_lookup_targets`、`dict_redirects`。
- 前端 `WordPopup` 已支持 mini slip、bottom sheet、AI glossary 优先、disambiguation、反馈和加入生词本。
- 生词本已支持 lemma 合并、`dict_entry_id`、`source_refs`、`collected_forms`、详情页按 `/dict/entry` 加载完整词条。
- 结果页已有 saved-vocab overlay：登录用户走 `/vocabulary/highlights`，匿名用户使用本地词库匹配。
- 生词本列表已有搜索、状态筛选、时间/字母排序、来源数量和最近语境展示。

### 待确认能力

- 结果页从生词详情跳回后按 `sentenceId` 滚动定位的真实小程序表现。
- saved-vocab 独立视觉层是否符合最新“批注感”规格。
- 词典导入数据中 POS 归一化、多例句块、fragment redirect、phrase template 覆盖率是否稳定。
- 云端生词掌握状态 PATCH 与音频 URL 回写是否在真实同步队列中稳定工作。

---

## P0 — 严重问题

### P0-1：初始 schema 中 `vocabulary_book` 前向引用 `dict_entries` ✅ 已修复

- **文件**: `server/db/migrations/0001_initial_schema.sql`
- **位置**: `vocabulary_book.dict_entry_id BIGINT REFERENCES dict_entries(id)` 出现在 `dict_entries` 建表之前
- **风险**: 空库直接执行初始 schema 时，PostgreSQL 通常不能引用尚未存在的表，开发环境重建可能失败
- **修复**: `vocabulary_book.dict_entry_id` 先创建为 `BIGINT`，待 `dict_entries` / `dict_lookup_targets` / `dict_redirects` 创建完成后，再用 `ALTER TABLE` 添加外键约束
- **验证**: 代码审查确认无前向引用；空库实跑仍待数据库环境验证

### P0-2：`PATCH /vocabulary/{id}` 动态 SQL 参数占位符错位 ✅ 已修复

- **文件**: `server/app/services/user_assets/vocabulary.py` → `update_vocabulary()`
- **原因**: `set_clause` 从 `$2` 开始生成，但实际 `values` 从更新字段开始传入；`WHERE id = ${len(values)} AND user_id = ${len(values) + 1}` 也会越界
- **影响**: 掌握状态更新、`payload_json.audio_url` 回写等 PATCH 操作可能运行时失败
- **修复**: 更新字段占位符从 `$1` 开始，`vocab_id` / `user_id` 参数按更新字段数量顺延
- **验证**: `python -m py_compile server/app/services/user_assets/vocabulary.py` 通过；`uv run pytest tests/test_user_assets.py tests/test_dict_proxy.py -q` 通过

### P0-3：结果页查词弹层引入外部发音 API 请求 ✅ 已评审，待修复

- **文件**: `client/src/components/WordPopup/index.tsx`
- **原因**: `WordPopup` 中直接请求 `https://api.dictionaryapi.dev/...` 并展示发音按钮
- **问题**: 与现有规格“发音仅在生词本详情页”不一致；点词高频场景额外引入外部网络延迟和不可控失败
- **评审结论**: 同意移除结果页查词弹层发音，仅保留生词本详情页发音
- **修复**: 已删除 `WordPopup` 中 Free Dictionary API 请求、音频按钮和播放状态；生词本详情页发音保留

---

## P1 — 高优先级

### P1-1：已保存状态按 surface word 查找，变形词可能取不到 source refs ✅ 已修复

- **文件**: `client/src/pages/result/index.tsx`
- **位置**: `savedSourceRefs={getVocabEntryByLemma(wordPopup.word?.toLowerCase() || '')?.sourceRefs}`
- **原因**: 生词本以 lemma 归并，但这里用点击词表面形态查询；如 `adopted` 已合并到 `adopt`，可能无法拿到 source refs
- **影响**: `WordPopup` 中“已记入 / 加入当前语境 / 已记入 · n个语境”状态不准
- **修复**: 新增 `getVocabEntryByLookupForm()`，按 lemma、展示词和 `collectedForms` 查找；结果页改用该 helper 获取 `savedSourceRefs`
- **验证**: `client/node_modules/.bin/tsc.cmd -p client/tsconfig.json --noEmit` 通过

### P1-2：saved-vocab 视觉层仍是折角标记 ❌ 已关闭

- **文件**:
  - `client/src/components/ClickableWord/index.scss`
  - `client/src/components/InlineMark/index.scss`
- **现状**: 已保存词使用右下角折角标记
- **规格方向**: 浅色圆角背景 + 左侧小竖线 / 书签信号，与 `vocab/phrase/context` annotation 独立
- **风险**: 与普通词汇高亮、短语高亮、上下文下划线混在一起时层级不够清楚
- **评审结论**: 当前右下角折角方案可接受，本轮不改

### P1-3：词典 sheet 信息层级仍偏功能堆叠 ✅ 已评审，待优化

- **文件**:
  - `client/src/components/WordPopup/index.tsx`
  - `client/src/components/WordPopup/index.scss`
- **现状**: 已包含来源语境、AI glossary、通用释义、短语/例句 tabs、反馈、保存
- **问题**: Full sheet 与设计稿相比，AI 语境块和通用词典释义的层级还可更清晰，footer 动作与阅读流的轻量感仍需打磨
- **评审结论**: AI 语境解析优先级高于 TECD3 词典释义；sheet 应围绕当前语境先解释，再提供通用词典兜底
- **待办**: 调整 full sheet 层级与视觉重点：来源语境 / AI 语境解析优先，通用释义作为次级词典区
- **已实现**: `WordPopup` full sheet 改为两级底部 sheet：默认态语境优先，详情态上滑/点击展开到 86vh，AI 语境折叠为摘要条，`释义/短语/例句` 获得主体滚动空间；disambiguation 改为“选择这句话里的含义”状态。
- **二次重构**: 已按“阅读边注”重构为 `answer / dictionary / entry_picker / not_found` 四状态；默认态不再显示 tabs 和大段例句，详情态才承载 `释义 / 短语 / 例句`，消歧态取消禁用底部按钮，反馈降级到 header，保存按钮改为轻量纸面动作。

#### P1-3 UX 评估（2026-05-10）

评估依据：`.impeccable.md`、`docs/uiux/reading-annotation-system/word-lookup-and-vocabulary-ux.md`、`component-spec.md`、当前 `WordPopup` 实现。

自动检测：本地未发现可用 `impeccable` CLI / npm script，本轮以人工 UX critique 为准。

**当前主要问题**

1. **首屏答案不够“判定式”**  
   当前 full sheet 先展示来源语境，再展示 AI 语境解析，最后进入通用释义。虽然顺序合理，但“这句话里是什么意思”没有形成足够明确的首屏答案。用户打开 full sheet 时仍需要扫三块内容才能确认含义。

2. **来源语境和 AI 解析的关系不够清楚**  
   `来源语境` 是证据，`语境解析` 是结论。现在二者是两个并列 section，容易让用户把它们当成同级信息，而不是“结论 + 证据”。

3. **通用释义区视觉权重偏高**  
   `通用释义` 标题、tabs、释义列表组成完整词典面板，在有 AI glossary 的场景下会抢走部分注意力。考虑到 TECD3 只是本地兜底词典，通用释义应更像“词典补充”，而不是 sheet 主体。

4. **Disambiguation 状态缺少语境决策语言**  
   当前 candidate list 是可点列表，但没有明确告诉用户“请选择这句话里的意思”。这会让多个义项看起来像搜索结果，而不是一次语境消歧。

5. **Footer 同时放反馈和保存，任务层级仍可更清晰**  
   对用户来说主任务是“确认含义后保存语境”。反馈是纠错路径，应可达但更低权重。当前 footer 两个按钮并排，反馈按钮仍占据较稳定的底部动作位。

**建议的信息架构**

有 AI glossary 时：

1. Header：词头 / 音标 / 可选考试标签
2. `语境答案`：AI 解析作为首块，标题用 `在本文语境中` 或 `语境含义`
3. `原句证据`：来源句作为 AI 答案下的轻量 excerpt，而不是独立强 section
4. `词典补充`：TECD3 通用释义，默认展示前 1-2 个核心义项；短语/例句作为 tabs 或折叠入口
5. Footer：主按钮为保存 / 加入当前语境；反馈降为次按钮或 header 小入口

无 AI glossary、普通点词时：

1. Header
2. `原句`（若有 context sentence）
3. `词典释义`：直接给通用释义
4. Footer

Disambiguation 时：

1. Header
2. `选择这句话里的含义`
3. 来源句轻量展示
4. 候选列表：词性 + 释义预览 + 当前候选可点状态；选择后进入对应 entry sheet

Not found 时：

1. Header
2. 若有 AI glossary，仍显示 `语境答案`
3. 词典区显示结构化空态：`本地词库未收录`，可提供反馈入口
4. 无 dict entry 时不显示“记入生词本”主按钮，避免保存一个没有词典锚点的脆弱条目（后续如做 AI 生词条目再单独设计）

**推荐 UI 处理**

- 把 `glossary-section` 改成首屏主信息块：更强标题、更少边框、更像“答案纸条”。
- `source-context-excerpt` 移入 AI 块下方，作为证据行；无 AI 时再独立显示。
- `dict-section` 改名/视觉为 `词典补充` 或 `本地词典`，降低标题权重，默认只展开 `meanings`。
- Full sheet 内避免继续增加新卡片层级，尽量用分隔线、密度和标题级别区分层级。
- Footer 保持 sticky，但反馈改为低权重图标/文字入口；保存按钮保留主动作。

**设计健康评分（P1-3 局部）**

| 维度 | 评分 | 说明 |
|---|---:|---|
| 系统状态可见 | 3/4 | loading / not_found 已有，但网络失败仍笼统 |
| 真实语境匹配 | 2/4 | 有 AI 与来源句，但“结论-证据”关系不够明确 |
| 用户控制 | 3/4 | 可关闭、展开、反馈、保存；disambiguation 选择仍可更明确 |
| 一致性 | 3/4 | 符合纸感方向，但 section 权重略平均 |
| 错误恢复 | 2/4 | 词库未命中已改善，服务失败仍需细化 |
| 识别优于记忆 | 2/4 | 多义候选需要更明确的选择语言 |
| 效率 | 3/4 | mini 快速，full 可继续减少扫读成本 |
| 审美克制 | 3/4 | 没有明显 AI 套路，但有“功能堆叠”感 |
| 帮助与反馈 | 3/4 | 反馈入口存在，但权重略高 |
| 总体 | 27/40 | 基础不错，主要问题是信息架构而非视觉质量 |

#### P1-3 二次 critique（2026-05-10）

背景：两级 bottom sheet 已实现，但当前视觉效果仍不理想。按 `/impeccable critique` 复查后，判断问题不是单点样式，而是“信息架构、空间模型、视觉语言”三者没有统一。

**核心判断**

当前 sheet 同时想做三件事：解释当前语境、承载本地词典、提供保存/反馈动作。但默认态和详情态之间的视觉差异不够明确，导致用户感知上像是一个较高的功能面板，而不是“先给答案，再展开词典资料”的阅读辅助层。

**主要问题**

1. **上下两级 sheet 的角色没有被视觉化**  
   `context` stage 和 `detail` stage 主要通过高度、tabs 和摘要条区分，但整体容器、标题、卡片、footer 的语言基本一致。用户看不出“默认态是语境答案，展开态是词典资料库”。

2. **AI 语境答案被做成普通卡片，缺少判定感**  
   `context-answer-card` 仍是白底圆角卡片，和词典补充、消歧提示、原句证据都接近。它没有形成“这句话里就是这个意思”的首屏锚点。

3. **可用高度被结构性消耗**  
   header、AI card、source excerpt、dict title/tabs、footer 都是固定占位。即使 sheet 展开到 86vh，释义/短语/例句真正可阅读空间仍被切碎，用户滑动时只能看到一小段内容。

4. **详情态仍残留默认态信息**  
   展开后 AI 摘要条保留在主滚动区域内，虽然有上下文价值，但它继续占据词典资料区顶部空间。详情态应把它变成更轻的 pinned context hint，或者收入 header 下方的单行语境栏。

5. **反馈动作仍在底部稳定动作区抢空间**  
   保存/加入语境是用户完成查词后的主动作；反馈是纠错路径。当前 footer 让反馈和保存同处底部主操作区域，既压缩空间，也削弱主动作。

6. **视觉上仍有“卡片套卡片”的倾向**  
   sheet 是一个大容器，内部又出现答案卡、证据框、词典补充区、例句块、候选块。纸感阅读系统更适合用排版、留白、细分隔线和层级密度，而不是继续增加圆角块。

**修正方向**

- 默认态：做成“语境答案 sheet”，首屏只服务一个问题：这句话里是什么意思。词典补充只露出 1-2 行和展开入口。
- 详情态：做成“词典资料 sheet”，让 `释义 / 短语 / 例句` 成为主舞台；AI 语境只保留为轻量 sticky hint。
- 去掉或弱化内部卡片感：减少圆角背景块，改用纸面排版、细线、左侧词性栏、紧凑例句组。
- footer 精简：保存作为主按钮；反馈移动到 header 小入口或词典空态/错误态附近。
- 空间策略改为内容优先：详情态 header 更紧，tabs 固定，主滚动区尽量完整；默认态不展示大段词典内容。

**二次健康评分**

| 维度 | 评分 | 说明 |
|---|---:|---|
| 系统状态可见 | 3/4 | loading/not_found 有表达，网络失败还不够细 |
| 真实语境匹配 | 3/4 | 语境优先方向正确，但首屏判定感不够 |
| 用户控制 | 3/4 | 关闭、展开、选择、保存可用；上下滑语义需更清楚 |
| 一致性 | 2/4 | 两级 sheet 的角色差异不明显 |
| 错误预防 | 2/4 | disambiguation 有选择门槛，但保存无词条时策略还需明确 |
| 识别优于记忆 | 2/4 | tabs/展开/滑动之间有认知成本 |
| 效率 | 2/4 | 展开后仍要扫过较多上下文才能读词典资料 |
| 审美克制 | 2/4 | 纸感方向在，但内部块太多，阅读面被打碎 |
| 错误恢复 | 2/4 | 业务未命中清晰，服务失败仍笼统 |
| 帮助与反馈 | 3/4 | 反馈入口可达，但位置权重不理想 |
| 总体 | 24/40 | 方向正确，但当前视觉与交互结构还需要重构一轮 |

#### P1-3 截图复评与 clarify 评估（2026-05-10）

依据用户提供的小程序截图复查真实效果后，问题等级上调：当前不是局部视觉不佳，而是 bottom sheet 的状态模型、文案、排版和操作区一起造成了明显的阅读阻断。

**截图中暴露的关键问题**

1. **消歧态像错误态，不像选择态**  
   `north` 截图中标题为 `选择这句话里的含义`，说明文案是 `根据原句选择最贴近的词条，选择后查看完整释义。`，底部按钮是 `先选择义项`。这套文案过重，且和候选项内容不匹配：候选出现两个 `North` 专名，用户会疑惑为什么点普通方位词却要选人名词条。这里需要先解决候选质量/展示过滤，其次文案要解释“本地词库找到多个近似词条”，不能让用户以为自己操作错了。

2. **普通查词态缺少“当前语境答案”**  
   `resident`、`predators` 截图实际只显示原句和词典释义，没有给出“这句话里是什么意思”的直接答案。用户点词的第一诉求是理解当前句子，不是先读完整词典。即使没有 AI glossary，也应该从词典释义中抽取或强调最可能的首义，并把原句作为证据。

3. **词典数据原样暴露，阅读负担过高**  
   `resident` 的释义是一整串中文释义堆叠，`predators` 的释义也连续成段。MDX 转换数据如果直接展示，会像数据库 dump，而不是学习产品。需要对 definitions 做分行、限量、层级化和展开策略。

4. **“词典释义”标题与 tabs 分裂**  
   左侧标题是 `词典释义`，右侧 tabs 是 `释义 / 例句`，视觉上像两个导航系统并存。用户会看到一个标题和一个 tab 同时告诉他当前区域是什么，造成重复和噪音。

5. **详情展开行为不清楚**  
   `展开词典详情` 出现在默认态，但展开后用户看到的主要变化是 sheet 变高、更多释义露出。状态转换没有明确反馈，也没有告诉用户当前在“词典详情”模式。上滑、按钮、tab 切换三种行为都可能进入详情态，交互语义过多。

6. **底部操作过重且抢空间**  
   `反馈` + `记入生词本` 占据稳定底部区域，尤其黑色主按钮视觉重量很大。查词场景里用户还没确认含义，就已经被强行动作召唤。反馈按钮也过大，像与保存同级的主任务。

7. **原文背景和 sheet 关系太浑浊**  
   overlay 把原文变成灰绿色背景，sheet 白度很高，产生重遮罩感。阅读场景应保持“轻覆盖”，否则用户感觉被拉离文章，而不是获得一个临时注释。

8. **关闭按钮、拖拽条、滚动条同时出现，控制噪音高**  
   顶部有 drag handle，右上角有关闭按钮，右侧有滚动条，底部有两个大按钮。可控性是够的，但视觉控制点过多，sheet 像一个复杂弹窗。

**clarify 方向**

- `选择这句话里的含义` 改为更贴近问题的状态标题，例如 `找到多个词条` 或 `请选择最接近本文的意思`。如果候选都是专名，应明确标识 `专名词条` 并考虑降权。
- `根据原句选择最贴近的词条，选择后查看完整释义。` 可缩短为 `本地词库找到多个结果。选一个继续查看。`
- `先选择义项` 不适合作为大按钮文案。可改成禁用提示 `选择一个词条后可保存`，或取消底部主按钮，直接让候选项成为主动作。
- `词典释义` 与 `释义/例句` 不应同时强展示。详情态使用 tabs 即可，默认态使用 `词典补充`。
- `展开词典详情` 可改成 `查看更多释义` / `查看短语和例句`，根据实际可展开内容动态变化。

**结论**

下一轮应做结构性重构，而不是继续微调当前样式。建议先拆成三个明确状态：

1. `context answer`：默认打开，只回答当前句子里的意思。
2. `dictionary detail`：用户主动展开后，专门阅读释义/短语/例句。
3. `choose entry`：多候选时，先解决“选哪个词条”，不显示保存主按钮。

截图实际体验评分下调到 **18/40**。主要扣分来自：消歧候选不可信、首屏没有当前语境答案、词典释义原始堆叠、底部动作抢占阅读空间、状态切换语义不清。

#### P1-3 impeccable 优化方案（2026-05-10）

设计目标：把查词 sheet 从“词典弹窗”改成“阅读边注”。它不是有道词典类独立词典 app，而是帮助用户在阅读中快速确认当前句义、必要时再进入词典深读。

**核心设计判断**

- 首屏默认态只回答一个问题：`这个词在这句话里怎么理解？`
- 本地 TECD3 词典是兜底资料库，不是首屏主角。
- 多义词/多词条状态首先是“候选可信度”问题，其次才是 UI 问题。
- 保存生词是理解之后的动作，不能压过释义本身。
- 纸感界面应靠排版和层级，而不是多个圆角卡片堆叠。

**新的状态模型**

1. **`answer` 默认态：语境答案**
   - 高度：约 52-60vh，内容不足时自然收缩。
   - 展示：词头、音标、本文/常用含义、原句证据、少量词典补充。
   - 不展示 tabs。
   - 不展示大段例句。
   - 主动作：轻量 `记入生词本` / `加入当前语境`。
   - 反馈入口降级到 header 小入口或更多菜单。

2. **`dictionary` 详情态：词典资料**
   - 高度：约 84-88vh。
   - 展示：紧凑词头、单行语境提示、`释义 / 短语 / 例句` tabs、完整词典内容。
   - tabs 只在详情态出现。
   - 主滚动区尽量完整留给释义、短语、例句。
   - footer 更薄，或只在需要保存时出现。

3. **`entry_picker` 消歧态：选择词条**
   - 只解决“选哪个词条”。
   - 不展示保存主按钮。
   - 不展示大段词典释义。
   - 候选项需要显示词条类型：普通词 / 短语 / 专名 / 变形。
   - 如果候选主要是专名，而用户点击的是小写普通词，应优先显示普通词直查结果或降权专名。

4. **`not_found` 未收录态**
   - 若有 AI glossary，仍显示语境答案。
   - 若没有 AI glossary，显示轻空态：本地词库未收录；可反馈，但不显示保存主按钮。
   - 区分 `not_in_dictionary` 与 network/server fail。

**答案置信度策略**

首屏的“语境答案”需要区分来源，避免过度承诺：

| 来源 | 标签 | 文案策略 |
|---|---|---|
| AI glossary | `本文含义` | 可以判定式展示 |
| 后端语境短语命中 | `短语含义` | 可以优先展示短语整体意义 |
| 单一精确词条 + 首义 | `常用释义` | 可以说“可先按这个意思理解” |
| 多候选/低置信 | `多个结果` | 不给判定答案，先进入选择词条 |
| not found | `未收录` | 不伪造答案 |

**词典内容整理策略**

MDX 转 PostgreSQL 的释义不能原样倾倒到 UI。前端至少需要一层 presentation formatting：

- 每个 POS 最多默认展示 2-3 条释义。
- 长释义按 `；`、`;`、中文顿号密集段落做弱切分，但保留原顺序。
- 默认态只展示首个 POS 的核心释义。
- 详情态按 POS 分组展示，例句与定义分离。
- 例句 tab 中英文分层：英文为主，中文译文降低权重。
- 专名词条必须显式标识，避免用户误以为是普通词义。

**视觉方向**

- sheet 背景使用温纸色，不使用强白大卡片。
- overlay 降低浑浊感：保留文章可感知，不让用户觉得被弹窗拉走。
- 默认态少用内部卡片：答案、原句、词典补充用排版和细分隔线区分。
- 词头仍可使用阅读 serif，但尺寸收敛；避免 `resident/predators` 这类长词压迫首屏。
- tabs 只出现在详情态，避免默认态左标题 + 右 tabs 的重复。
- 主保存按钮不再使用当前大黑块。默认态改为纸面按钮或行内 bookmark action；详情态可使用较薄 sticky action。
- 反馈入口改为低权重：header 小图标、空态旁、或更多菜单；不与保存同级。

**交互方向**

- 默认态进入详情态：只保留一个明确入口，如 `查看更多释义` / `查看短语和例句`。
- 上滑可作为增强手势，但不作为唯一或主要可发现路径。
- tab 点击只在详情态内切换，不再隐式触发展开。
- 消歧态候选项就是主动作，底部不放禁用大按钮。
- 下拉关闭保留，关闭按钮缩小并降低视觉权重。

**文案方向**

- `词典释义` 默认态改为 `词典补充`。
- `展开词典详情` 按内容动态改：
  - 有更多释义：`查看更多释义`
  - 有短语/例句：`查看短语和例句`
  - 只有例句：`查看例句`
- `选择这句话里的含义` 改为更中性的 `找到多个词条` 或 `选一个词条继续`。
- `先选择义项` 删除；消歧态不显示底部禁用主按钮。
- `本地词库未收录` 只作为空态标题，机器原因继续使用 `reason=not_in_dictionary`。

**实施优先级**

1. **先修查词可信度**
   - 小写普通词查询时，专名词条降权。
   - 精确小写普通词存在时，不应优先返回大写专名 disambiguation。
   - 建立 `north / resident / predators / take off / nonexistent` 最小回归样例。
   - 已补 `north` 类同拼写大写专名降噪：小写普通词存在时，过滤同拼写大写专名候选，避免无意义消歧。

2. **再重构 WordPopup 信息架构**
   - 引入明确 `SheetMode = answer | dictionary | entry_picker | not_found`。
   - 抽取 `primaryMeaning` / `answerConfidence` / `dictionarySections` presentation helpers。
   - 默认态移除 tabs 和大段例句。
   - 详情态集中展示 tabs 与完整词典内容。

3. **最后做视觉重写**
   - 减少内部圆角块。
   - 改 footer 动作层级。
   - 降低 overlay 和控制点噪音。
   - 检查长词、长中文释义、长例句、底部安全区。

**验收样例**

- `north` in `in the north of the country`：优先显示普通方位词义，不应默认出现两个 `North` 人名候选。
- `resident` in `resident big cats`：首屏能理解为“栖居/常驻于此的”，不是先读一串职业/专名式释义。
- `predators`：默认态只展示核心含义“捕食者/掠食动物”，例句进入详情态后查看。
- `take off`：点击 `off` 时优先展示 `take off` 短语整体义。
- 未收录词：返回结构化未收录状态，不刷错误，不显示保存主按钮。

### P1-4：词典查询参数未传 reading goal/variant 到后端 ✅ 已评审，待清理

- **文件**:
  - `client/src/services/api/client.ts` → `fetchDict()`
  - `server/app/api/routes/dict.py`
- **现状**: 后端 schema 已接收 `reading_goal` / `reading_variant`，但前端未传；provider 当前也未使用
- **影响**: 考试标签过滤目前主要在前端展示层完成，后端无法按阅读目标做查询策略或结果排序
- **评审结论**: `reading_goal` / `reading_variant` 不参与 `/dict` 查询，属于遗留字段，应清理
- **真正优化方向**: 强化上下文短语识别，例如点击 `take off` 中的 `off` 时，应优先显示 `take off` 而不是 `off`
- **修复**: 已清理 `/dict` route 与 `DictionaryLookupRequest` 中的无效 reading 参数
- **短语优化**: `phrase_candidates` 增加 bare phrasal fallback，覆盖 `look up`、`find out`、`look forward to` 等常见结构
- **API 验证**:
  - `off` + `The plane will take off...` → `take off` 排在 `off` 前
  - `up` + `I look up the word...` → `look up` 排在 `up` 前
  - `out` + `She found out the truth...` → `find out` 排在 `out` 前
  - `forward` + `look forward to hearing...` → `look forward to` 排在 `forward` 前

---

## P2 — 中优先级

### P2-1：disambiguation mini 状态还可以更明确 ⏳ 待优化

- **文件**: `client/src/components/WordPopup/index.tsx`
- **现状**: mini 文案为“多个义项，点击查看”
- **评审结论**: mini 保持轻量；full sheet 中优化候选列表 UI，突出词性、预览和可选择性

### P2-2：词典数据质量需要建立抽样回归集 ⏳ 待补充

- **文件**:
  - `server/tests/test_tecd3_import.py`
  - `server/tests/test_dict_query_optimization.py`
  - `server/tests/test_dict_lemma_fallback.py`
- **已有覆盖**: POS canonicalization、多例句、fragment redirect、hidden nlp forms、lemma fallback、phrase template
- **建议新增样例**:
  - 常见短语：`take place`、`be there for sb`、`look forward to`
  - 变形词：三单、过去式、比较级、不规则复数
  - 多义词：`lead`、`object`、`content`
  - 专名/缩略词：`U.S.`、`AAR`
  - fragment-only 与 weak entry

### P2-3：`dict_redirects` 运行时使用路径需复查 ⏳ 待确认

- **文件**:
  - `server/app/services/dictionary/db_pg.py`
  - `server/app/services/dictionary/providers/tecd3.py`
- **现状**: 运行时主要查 `dict_lookup_targets`；`dict_redirects` 是否仅作为导入/补齐辅助需进一步确认
- **建议**: 明确 `dict_redirects` 的运行时职责。若不直接查询，应在架构文档中说明 redirect 已物化到 lookup targets

### P2-4：结果页回原文定位需要真机/开发者工具验证 ⏳ 待验证

- **文件**: `client/src/pages/result/index.tsx`
- **现状**: replay mode 支持 `sentenceId`，并设置 `scrollIntoView` 和 `scrollTop`
- **风险**: 小程序 `ScrollView` 与页面滚动混合时可能表现不一致
- **验证**: 从生词详情页点击“查看原文”，确认目标句高亮且滚动位置稳定

### P2-5：生词掌握状态与复习功能未完成 ⏳ 后续专题

- **文件**:
  - `client/src/types/view/vocabulary.vm.ts`
  - `client/src/packageA/vocab/index.tsx`
  - `server/db/migrations/0001_initial_schema.sql`
- **现状**: 后端支持 `new/learning/review/mastered/archived`，前端 VM 主要是 `mastered: boolean`
- **评审结论**: 单词本目前是粗糙版本，后续需要完整复习功能
- **后续方向**: 研究并引入“艾宾浩斯遗忘曲线”相关复习调度能力，作为单词本二期/专题设计

---

## P3 — 低优先级

### P3-1：前端词典缓存 key 使用原文 text，未统一 normalize ⏳ 待评估

- **文件**: `client/src/services/dictCache.ts`
- **现状**: 缓存 key 为 `text:type:context:occurrence`
- **影响**: `World’s` / `world's` 等规范化等价输入会产生不同前端缓存 key；后端可正常归一化
- **建议**: 可接受，除非高频重复查询下发现缓存收益不足

### P3-2：生词列表 `N 篇` 实际统计为 source refs 数 ✅ 已修复

- **文件**: `client/src/packageA/vocab/index.tsx`
- **现状**: `sourceCount = entry.sourceRefs?.length`
- **问题**: 多个语境可能来自同一篇文章，显示为 `N 篇` 不一定准确
- **修复**: 新增 distinct source article 统计，`N 篇` 仅按不同 `cloudRecordId/clientRecordId` 计算；“还有 N 个语境”继续按 source refs 计算
- **验证**: `client/node_modules/.bin/tsc.cmd -p client/tsconfig.json --noEmit` 通过

### P3-3：词典 not found / network fail 的 mini 与 sheet 状态可更细 ⏳ 部分修复

- **文件**: `client/src/components/WordPopup/index.tsx`
- **现状**: 异常后 `dictResult=null`，文案偏笼统
- **建议**: 区分 404、网络失败、服务不可用；mini 给轻提示，full sheet 提供反馈入口
- **已修复**: `/dict` 查询未命中改为正常 200 响应，返回 `result_type=not_found` 与 `reason=not_in_dictionary` 机器可读状态；前端 adapter/VM 已支持 `not_found`，并在本地映射空态提示文案。
- **仍待优化**: 网络失败、词典服务不可用等非业务 miss 状态仍需单独 UI

---

## 推进计划

### Phase 1 — 基础风险修复

- [x] 修复初始 schema 中 `dict_entries` 与 `vocabulary_book` 的外键顺序
- [x] 修复 `update_vocabulary()` 动态 SQL 参数占位符
- [x] 明确并调整 `WordPopup` 发音能力边界
- [x] 修复 saved source refs 按 surface word 查找的问题
- [ ] 补最小测试：schema 执行、vocabulary PATCH、saved state helper

### Phase 2 — 查词 UI/UX 状态矩阵

- [ ] 梳理 `WordPopup` mini/full 的 required states
- [ ] 优化 disambiguation mini 和 full sheet 展示
- [ ] 优化 AI glossary、来源语境、通用释义的层级
- [x] 统一 saved-vocab 视觉层（评审决定保留当前右下角折角）
- [ ] 验证文字溢出、遮挡、底部安全区、长词/短语状态

### Phase 3 — 生词本体验增强

- [x] 区分“篇数”和“语境数”
- [ ] 评估是否引入 `masteryStatus` 前端 VM
- [ ] 验证生词详情页发音 URL 回写与云同步
- [ ] 验证从生词详情回原文定位

### Phase 4 — 数据质量与回归

- [ ] 建立词典查询黄金样例集
- [ ] 补 phrase template / fragment redirect / POS / examples 抽样回归
- [ ] 明确 `dict_redirects` 运行时职责并更新架构文档
- [ ] 跑完整后端词典与生词本相关测试

---

## 修复日志

| 日期 | 问题 | 操作 |
|------|------|------|
| 2026-05-10 | 初始化 | 创建词典与生词功能优化临时 tracker，记录第一轮走查发现 |
| 2026-05-10 | P0-1 | 初始 schema 中 `vocabulary_book.dict_entry_id` 改为后置 `ALTER TABLE` 外键，避免前向引用 `dict_entries` |
| 2026-05-10 | P0-2 | 修复 `update_vocabulary()` 动态 SQL 参数占位符错位 |
| 2026-05-10 | P1-1 | 新增 `getVocabEntryByLookupForm()`，结果页保存状态可按 collected form 命中源语境 |
| 2026-05-10 | P3-2 | 生词列表 `N 篇` 改为 distinct 文章数，语境数单独计算 |
| 2026-05-10 | P0-3/P1-2/P1-3/P1-4/P2-1/P2-5 | 记录评审结论：结果页发音移除、saved-vocab 折角保留、AI 语境解析优先、清理 reading 参数、优化 disambiguation full sheet、复习功能后续专题 |
| 2026-05-10 | P0-3 | 移除 `WordPopup` 结果页查词发音请求与播放 UI，仅保留生词本详情页发音 |
| 2026-05-10 | P1-4 | 清理 `/dict` reading 参数；新增 bare phrasal fallback，修复 `look up` / `find out` / `look forward to` 语境短语优先 |
| 2026-05-10 | P3-3 | `/dict` 查询未命中改为 200 `not_found` 正常结果，并使用 `reason=not_in_dictionary` 结构化原因避免异常流刷屏 |
| 2026-05-10 | P1-3 | 复刻两级底部词典 sheet：默认态语境答案优先，详情态扩高展示释义/短语/例句，并优化 disambiguation 与 footer 状态 |
| 2026-05-10 | P1-3 | 按“阅读边注”二次重构 `WordPopup`：新增 `answer/dictionary/entry_picker/not_found` 状态模型，整理 MDX 释义展示，弱化 footer 与反馈，补小写普通词过滤同拼写大写专名候选 |

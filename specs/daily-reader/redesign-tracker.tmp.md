# 每日精读重构进度 (TEMP)

> 本文档为临时跟踪文件，用于跟踪“每日精读做到精品级”的产品、workflow、schema、前端与验证进度。功能稳定后删除或沉淀到正式 specs。
>
> 创建日期：2026-05-10

---

## 目标

每日精读不是主线“解析页”的复制，也不是文章底部的分析报告。目标是做成首页核心内容产品：

- **正文是沉浸英文阅读器**：阅读节奏轻、纸感强、词汇高亮克制但全篇覆盖。
- **透读是轻量带读**：每段只给一点导读/问题/小结，帮助用户带着目标读，不打断正文。
- **译文是理解工具**：按段隐藏展开，默认不抢走英文阅读主导权。
- **文末是克制讲义**：提炼表达、长难句、写作手法和少量讨论题，不再堆 2000+ 字全文分析。
- **workflow 是英语精读教案生成器**：从“文章意义分析”转向“提升英语阅读能力”。

---

## 当前判断

### 已确认的问题

1. **当前 workflow 偏全文解读**
   - 主要输出 `summary / thesis_and_intent / structure / full_article_analysis`。
   - 内容更像“文章讲了什么”，不够像“如何读懂英文、学会表达”。

2. **文末内容过量**
   - `full_article_analysis` 500-1000 字，再叠加结构、表达、误读点、讨论题，移动端负担过重。
   - 当前 UI 即使改成编辑笔记，也仍然是在文末承载过多学习内容。

3. **正文不应插入重解析**
   - 每日精读要区别于主线解析页。
   - 正文中允许高亮词和每段轻量“透读”，不应插入长难句、语法、写法等重内容。

4. **高亮覆盖有严重生成问题**
   - 当前观测到词汇高亮集中在文章前半部分，后半部分缺少标注。
   - 根因大概率是一次性把全篇 paragraphs 交给 LLM，模型优先处理前半部分，且 projection 缺少 coverage guard。

5. **旧数据兼容不是当前优先级**
   - 当前仍是本地调试和探索阶段。
   - 可以删除旧 daily reader 数据，重跑 pipeline，不需要为旧 schema 做复杂兼容。

### 需要保留的方向

- 文章拉取发现层可以基本保留：Guardian/BBC/NPR、提取、评分、来源多样化逻辑不需要大改。
- 正文词汇/短语/语境高亮方向合理，但生成方式和覆盖检查需要改。
- 词典弹层复用 `WordPopup` 合理。
- 纸感、杂志感、低干扰设计方向保留。

---

## 目标体验草案

### 页面结构

```text
Header / Cover
→ 读前导读
   - 这篇大致写什么
   - 带着 1-2 个问题读
→ Body
   - 英文原文
   - 全篇均匀的词汇/短语/语境高亮
   - 每段轻量“透读”
   - 每段译文默认隐藏，可展开
→ 文末收束
   - 这篇带走什么
   - 值得学的表达 3-5 个
   - 长难句透视 1-2 个
   - 写作手法 / 高级语法 1-2 个
   - 思考题 1-2 个
```

### 视觉锚点

当前采用“单列小程序杂志阅读器”方向，不采用左右分栏批注：

- 参考图：[daily-reader-design-reference.png](./assets/daily-reader-design-reference.png)
- 首屏：封面图保留沉浸感，标题、来源、日期、标签按杂志内页层级组织。
- 读前导读：放在标题区之后，作为轻量 editorial block，而不是重卡片。
- 正文：单列英文原文是绝对主角，高亮为低干扰纸色标注，使用 icon 区分词汇、短语、语境。
- 透读：每段一个轻量条目，默认一行问题；展开后仅 1-2 行确认理解，不放重解析。
- 译文：按段折叠展开，放在段落下方，类似双语注释版，不做侧栏。
- 词典弹层：复用 `WordPopup`，但需要视觉上更像正文注释卡，不要过重遮挡。
- 文末：改为“今日精读收束”，采用讲义式分节、细分割线和少量语言点，不再堆全文分析。

### 正文透读原则

- 每段最多一个轻量透读入口。
- 默认一行，展开也只给 1-2 句。
- 不放长难句拆解，不放大段语法，不放写作手法。
- 不与主线解析页抢功能边界。

### 译文原则

- 按段生成、按段隐藏。
- 默认不显示译文。
- 用户手动展开某段译文。
- 译文服务“理解文章”，不替代英文阅读。

### 文末讲义原则

- 控制在 1.5-2 屏左右。
- 不默认展示长篇全文讲解。
- 可以保留“完整讲解”作为次级入口，但不是主路径。
- 每篇只提炼少数高价值语言点。

---

## 建议 Schema 方向

### P0：段落透读与译文

```python
class ParagraphReadingNote(BaseModel):
    paragraph_id: str
    focus_question: str
    micro_summary: str
    translation: str
```

用途：
- `focus_question`：正文段前/段后轻量问题。
- `micro_summary`：用户读完后快速确认是否读懂。
- `translation`：按段展开译文。

### P0：全篇高亮

```python
class DailyHighlightDetail(BaseModel):
    id: str
    type: Literal["vocab_highlight", "phrase_gloss", "context_gloss"]
    text: str
    gloss: str
    paragraph_id: str
    start: int
    end: int
    reason: str | None = None
```

要求：
- 按段或按 section batch 生成。
- highlight id 使用稳定格式，如 `hl_p03_01`。
- projection 前做 coverage check。

### P1：文末语言收束

```python
class SentenceNote(BaseModel):
    sentence: str
    paragraph_id: str
    translation: str
    breakdown: str
    takeaway: str

class WritingMove(BaseModel):
    anchor: str
    paragraph_id: str
    move_type: str
    explanation: str
    reusable_pattern: str | None = None

class ExpressionPoint(BaseModel):
    expression: str
    paragraph_id: str
    gloss: str
    context_sentence: str
    usage_note: str

class CloseReadingTakeaways(BaseModel):
    article_takeaway: str
    key_expressions: list[ExpressionPoint]  # 3-5
    sentence_notes: list[SentenceNote]      # 1-2
    writing_moves: list[WritingMove]        # 1-2
    discussion_questions: list[str]         # 1-2
```

### P2：可选 section 层

```python
class DailyReaderSection(BaseModel):
    section_id: str
    title: str
    paragraph_ids: list[str]
    reading_focus: str
    takeaway: str
```

说明：
- 如果文章自然结构清晰，可生成 section。
- 如果文章较短，paragraph note 就足够，不强制 section 化。

---

## 建议 Workflow 方向

### 当前 workflow

```text
light_normalize
→ vocab_highlight
→ phrase_context_gloss
→ footer_analysis
→ full_interpretation
→ quality_review
→ refinement
→ daily_projection
```

### 目标 workflow 草案

```text
light_normalize
→ paragraph_guides_and_translations
→ highlight_by_paragraph_batches
→ close_reading_takeaways
→ quality_review
→ daily_projection
```

### 过渡实现方案

为了降低一次性重构风险，可以先保留节点框架，但替换职责：

| 现节点 | 新职责 |
|--------|--------|
| `vocab_highlight` | 改为按段/批次生成词汇高亮 |
| `phrase_context_gloss` | 改为按段/批次补短语/语境高亮 |
| `footer_analysis` | 改为生成 paragraph notes + translations |
| `full_interpretation` | 改为生成 close reading takeaways |
| `quality_review` | 增加高亮覆盖、译文质量、内容过量检查 |
| `daily_projection` | 输出新 daily reader payload |

---

## 文章拉取链路检查项

> 文章拉取逻辑不是本次主要重构对象，但要顺便做上线级检查。

### P1 — 必查

- [ ] `content_security.py` 是否已真正集成到 `pipeline.py`
- [ ] 每日定时执行是否实现
- [ ] 封面下载 / 本地存储 / 后续 COS+CDN 方案是否清楚
- [ ] 来源多样化是否实际生效
- [ ] 候选文章长度是否适合“按段透读”
- [ ] AI 评分是否更偏“适合英语学习”，而不仅是话题有趣

### P2 — 可优化

- [ ] 文章类型是否过度集中在科技/文化
- [ ] 是否需要筛掉结构过散、不适合精读的新闻快讯
- [ ] 是否需要优先选择论证清晰、有可学表达的文章
- [ ] 是否需要按用户水平选择 B1/B2/C1 内容

---

## 前端改造清单

### P0 — 正文层

- [ ] `DailyReaderBody` 支持每段 `ParagraphReadingNote`
- [ ] 每段渲染轻量“透读”入口
- [ ] 每段译文隐藏展开
- [ ] 高亮仍保持低干扰内联样式
- [ ] 后半篇高亮覆盖验证

### P1 — 文末层

- [ ] `DailyReaderFooterAnalysis` 改为“今日精读收束”
- [ ] 文末只展示 `CloseReadingTakeaways`
- [ ] 长难句控制 1-2 个
- [ ] 写作手法/高级语法控制 1-2 个
- [ ] 表达控制 3-5 个
- [ ] 讨论题控制 1-2 个
- [ ] 可选“完整讲解”入口，不默认铺开

### P1 — 首页与精品感

- [ ] 首页卡片是否足够“每日精选”而非普通列表
- [ ] 首屏封面与标题是否有杂志感
- [ ] 页面整体是否区别于主线解析页
- [ ] 分享卡片是否需要跟精品内容感统一

### P1 — 视觉复刻要点

- [ ] `DailyReaderHeader` 增强首屏杂志感：封面、标题、metadata、读前导读一体化。
- [ ] `DailyReaderBody` 增加单列段落内的 `ReadingNoteStrip` 和 `ParagraphTranslation`。
- [ ] `DailyReaderHighlightWord` 保留 icon 标记，但统一 icon 尺寸、颜色与三类高亮 token。
- [ ] `WordPopup` 在 daily reader 场景下优化尺寸、边框、阴影和锚点位置。
- [ ] `DailyReaderFooterAnalysis` 改为 `DailyReaderCloseReadingRecap` 风格，减少卡片和大段文字。
- [ ] 底部浮动栏保留，但改成更像图中 pill：`Aa / 目录 / 译文` 或 `收藏 / 往期` 需最终确认。

---

## 后端改造清单

### P0 — Schema

- [x] 更新 `server/app/schemas/internal/daily_drafts.py`
- [x] 更新 `client/src/types/api/daily-reader.dto.ts`
- [x] 更新 `client/src/types/view/daily-reader.vm.ts`
- [x] 更新 `daily-reader.adapter.ts`
- [x] 更新 `server/app/schemas/daily_reader.py` (API response schema)
- [x] 更新 `server/app/services/daily_reader/service.py` (row→response mapping)
- [x] 更新 `server/app/services/daily_reader/pipeline.py` (payload assembly & storage)
- [x] 更新 `server/app/api/routes/prompt_debug.py` (strategy builder mapping)
- [x] 更新 `server/tests/test_daily_reader.py` (mock data)
- [x] 创建数据库迁移 `0002_add_paragraph_notes_and_takeaways.sql`

### P0 — 高亮覆盖

- [x] 高亮改为按段/批次生成
- [x] highlight id 改为稳定格式
- [x] 合并 vocab/phrase/context 时避免 ID 冲突
- [x] projection 做 paragraph coverage check
- [x] quality review 增加 coverage-by-paragraph / coverage-by-half 检查

### P1 — Prompt

- [x] `daily_vocab.yaml` 改为要求全篇覆盖、按段预算
- [x] `daily_footer.yaml` 改为 paragraph notes + translations
- [x] `daily_interpretation.yaml` 改为 close reading takeaways
- [x] `daily_review.yaml` 增加译文、内容过量、覆盖率、语言教学价值检查
- [x] `daily_refinement.yaml` 适配新 schema
- [x] `policies/daily.yaml` 全量更新

---

## 验证计划

### 数据验证

- [ ] 生成 3 篇不同来源文章
- [ ] 检查每篇每段是否有 note/translation
- [ ] 检查高亮是否覆盖后半篇
- [ ] 检查文末语言点数量是否受控
- [ ] 检查长难句/写作手法是否真实来自原文

### 前端验证

- [ ] 正文阅读不被重解析打断
- [ ] 段落透读默认足够轻
- [ ] 译文展开/收起稳定
- [ ] 文末不再形成数据墙
- [ ] 页面和主线解析页有明显产品差异
- [x] 小程序构建通过

### 体验验收

- [ ] 用户能在不看译文时读完整篇英文
- [ ] 用户能通过每段透读知道“这一段该读出什么”
- [ ] 用户能按需打开译文理解原文
- [ ] 用户在文末得到少量高价值语言收获
- [ ] 用户不会看到 3-5 屏密集解析内容

---

## 进度

| 日期 | 事项 | 状态 |
|------|------|------|
| 2026-05-10 | 明确每日精读目标：沉浸阅读 + 轻量透读 + 克制讲义 | ✅ 完成 |
| 2026-05-10 | 评审 `redesign-footer.md`：方向偏 footer，需要升级为整体重构 | ✅ 完成 |
| 2026-05-10 | 创建本 tracker | ✅ 完成 |
| 2026-05-10 | 确认视觉方向：单列小程序杂志阅读器，不做左右批注栏 | ✅ 完成 |
| 2026-05-10 | GLM：后端 schema/workflow/prompt 全量重构完成 | ✅ 完成 |
| 2026-05-10 | Gemini：前端单列杂志阅读器 UI 复刻完成 | ✅ 完成 |
| 2026-05-10 | Codex：接通新 payload 到前端 adapter，移除 mock 文案，完成构建与 Daily Reader 测试 | ✅ 完成 |

---

## 并行任务拆分建议

> 2026-05-10 调整：Gemini 更适合做前端 UI 复刻与样式打磨；GLM 负责结构化后端改造；Codex 负责总集成、关键前端交互和验收。

### GLM 任务：后端 schema / workflow / prompt

目标：让 workflow 生成适配新 UI 的结构化内容，而不是生成文末大段全文解析。

建议负责文件：
- `server/app/schemas/internal/daily_drafts.py`
- `server/app/workflow/daily_reader_workflow.py`
- `server/prompts/agents/daily_vocab.yaml`
- `server/prompts/agents/daily_footer.yaml`
- `server/prompts/agents/daily_interpretation.yaml`
- `server/prompts/agents/daily_review.yaml`
- `server/prompts/agents/daily_refinement.yaml`

交付要求：
- 新增 paragraph notes / translations / close reading takeaways schema。
- 高亮改为按段或按小批次生成，保证后半篇覆盖。
- `daily_projection_node` 输出前端可直接消费的新 payload。
- 不做旧数据兼容，允许删除本地旧 daily reader 数据后重跑。
- 增加覆盖率检查：按 paragraph / 前半篇后半篇统计 highlights。

边界：
- 不改 `client/src/components/*` UI 文件。
- 可以改客户端 DTO 类型草案，但最好先在文档中说明，避免和前端实现冲突。

### Gemini 任务：前端 UI 复刻与样式打磨

建议负责文件：
- `client/src/components/DailyReaderHeader/*`
- `client/src/components/DailyReaderBody/*`
- `client/src/components/DailyReaderHighlightWord/*`
- `client/src/components/DailyReaderFooterAnalysis/*`
- `client/src/packageB/daily-reader/index.scss`

交付要求：
- 按视觉锚点复刻单列小程序杂志阅读体验。
- 不做左右批注栏，不做复杂桌面杂志分栏。
- 优化首屏封面、标题、读前导读。
- 优化正文行距、段距、纸感背景、高亮 icon 与三类高亮颜色。
- 设计/实现 `透读` 折叠条和 `译文` 展开块的视觉样式。
- 重做文末“今日精读收束”的视觉层级，避免卡片堆叠和数据墙。
- 允许使用 mock/fallback 字段完成视觉复刻，但不要修改后端 workflow。

边界：
- 不改 `server/app/workflow/*`、`server/prompts/*`。
- 不重构数据适配主逻辑；需要新字段时先在 props/mock 层临时兼容。

### Codex 任务：总集成 / 关键交互 / 文章链路检查

目标：把 GLM 的新 payload 和 Gemini 的视觉稿合并成可运行的小程序功能，并补齐质量验证。

建议负责文件：
- `client/src/packageB/daily-reader/index.tsx`
- `client/src/types/api/daily-reader.dto.ts`
- `client/src/types/view/daily-reader.vm.ts`
- `client/src/services/api/adapters/daily-reader.adapter.ts`
- `client/src/components/WordPopup/*`
- `server/app/services/daily_reader/pipeline.py`
- `server/app/services/daily_reader/discovery.py`
- `server/app/services/daily_reader/extraction.py`
- `server/app/services/daily_reader/scoring.py`
- `server/app/services/daily_reader/content_security.py`

交付要求：
- 接入 GLM 新 schema 到前端 DTO/view model/adapter。
- 实现 `透读` 和 `译文` 展开/收起状态管理。
- 调整 `WordPopup` 在 daily reader 场景下的交互与视觉，不影响主解析页。
- 检查文章拉取链路：content security、来源多样化、文章长度、封面图、评分维度。
- 生成 3 篇样例数据并做体验验收：后半篇高亮覆盖、文末信息密度、译文质量。
- 运行 `npm run build:weapp` 和必要的后端测试。

### 旧数据清理策略

不建议在 schema/workflow 落地前立刻删除旧数据。旧数据现在仍有两个价值：

- 作为当前 UI 问题的对照样本。
- 前端复刻时可以用旧正文、高亮和封面先做 fallback 展示。

建议清理时机：

1. GLM 完成新 payload projection。
2. 前端 adapter 能兼容新字段。
3. 至少有一条 workflow 能成功产出新结构。
4. 再删除旧 `daily_readers` 和旧 `pipeline_runs`，重跑 pipeline。

清理范围建议：
- P0：清空 `daily_readers`。
- P0：清空 `pipeline_runs`，避免旧 pipeline 状态干扰判断。
- 不清空词典、生词本、用户数据、普通解析记录。
- 如需清理收藏中指向旧 daily reader 的记录，单独评估，不和 P0 清理混在一起。

---

## 待决策

1. **是否引入 section 层**
   - 方案 A：只做 paragraph note，简单直接。
   - 方案 B：paragraph + section，支持更强结构导航。
   - 初步建议：先做 paragraph note，section 作为 P2。

2. **译文生成粒度**
   - 方案 A：每段一个 translation。
   - 方案 B：每句 translation。
   - 初步建议：每段 translation，长难句单独 sentence note。

3. **完整全文讲解是否保留**
   - 方案 A：删除，不再生成。
   - 方案 B：保留为可选 `full_explanation`，前端默认不展示。
   - 初步建议：P0 删除或降级，避免内容爆炸。

4. **高亮每段预算**
   - 初步建议：每段 1-3 个，总量按文章长度控制；允许短段无高亮，但不允许后半篇连续空白。

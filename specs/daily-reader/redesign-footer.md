# 每日精读解析区重构方案：Tab 分层 + 导读卡

> **状态**：待评审
> **日期**：2026-05-10
> **前置文档**：[requirements.md](requirements.md)、[design.md](design.md)、[review.md](review.md)

---

## 一、问题诊断

### 1.1 核心矛盾

Spec 定位"杂志式沉浸阅读"，要求"重解析收口到文末"——意图是**不打断阅读流畅性**。但当前实现把"收口到文末"理解成了"全部堆在文末"：6 个解析模块等权平铺、全部展开、无折叠、无分层，形成一堵"分析数据墙"。

### 1.2 量化分析

以一篇典型 800 词文章为例，`footer_analysis_json` 的内容量：

| 模块 | 估算字数 | 占比 |
|------|---------|------|
| summary | ~50 字 | 2% |
| thesis_and_intent | ~100 字 | 4% |
| structure | ~200 字 | 8% |
| **full_article_analysis** | **800-1500 字** | **50%+** |
| key_expressions | ~500 字 | 20% |
| misreading_points | ~300 字 | 12% |
| discussion_questions | ~120 字 | 5% |
| **合计** | **~2000-2800 字** | |

在手机上，这些内容加上排版间距占据 **3-5 屏滚动量**，远超原文本身。

### 1.3 Spec 合规性检查

| Spec 要求 | 当前状态 | 差距 |
|-----------|---------|------|
| "Full Article Interpretation shall be collapsed by default" (Req8 AC6) | ❌ 全展开 | 严重 |
| "Key expressions as tappable cards in a grid layout" (Req8 AC8) | ❌ 垂直列表 | 中等 |
| "Structure as collapsible tree/indented list" (Req8 AC7) | ❌ 简单编号列表 | 中等 |
| "Each analysis module with clear visual separation" (Req8 AC6) | ⚠️ 间距均匀无层级 | 轻微 |

### 1.4 用户体验问题清单

1. **信息过载**：6 模块等权平铺，无主次、无折叠、无渐进揭示
2. **上下文脱节**：解析与原文完全分离，用户需反复滚动对照
3. **零灵活性**：无法跳过不关心的模块，无法快速定位高价值内容
4. **视觉断裂**：Header+Body 杂志感好，Footer 突然变成分析报告
5. **认知负荷过高**：刚读完英文原文（已是负荷），紧接着面对 2000+ 字中文分析

---

## 二、目标架构

### 2.1 当前架构

```
Header → Body(原文+高亮) → FooterAnalysis(6模块全展开堆叠)
```

### 2.2 目标架构

```
Header → Body(原文+高亮+段落锚点) → GuideCard(导读卡) → TabBar → TabContent
                                                          ├─ 速览 Tab（默认）
                                                          └─ 深读 Tab
```

### 2.3 页面流

1. 用户进入 → 封面+标题 → 阅读英文原文（纯净体验不变）
2. 滚过原文后 → **导读卡**（summary + thesis，轻量钩子，给用户继续阅读的理由）
3. 导读卡下方 → **Tab 切换器**（速览 / 深读）
4. **速览 Tab**（默认激活）：文章骨架 + 别读偏了 + 值得带走的表达
5. **深读 Tab**：分段精读讲解 + 思考讨论

### 2.4 内容分层逻辑

| 层级 | 内容 | 交互深度 | 目标用户 |
|------|------|---------|---------|
| 导读卡 | summary + thesis | 始终可见，0 交互 | 所有用户 |
| 速览 Tab | 骨架 + 误区 + 表达 | 扫描级，1-2 分钟 | 快速理解型 |
| 深读 Tab | 分段讲解 + 讨论 | 沉浸级，5-10 分钟 | 深度学习型 |

---

## 三、后端 Workflow 修改

### 3.1 Schema 变更

#### 3.1.1 `StructurePart` — 增加 `paragraph_ids`

```python
# server/app/schemas/internal/daily_drafts.py

class StructurePart(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    label: str
    title: str
    summary: str
    paragraph_ids: list[str] = Field(
        default_factory=list,
        description="关联的原文段落 ID 列表，如 ['p_0', 'p_1', 'p_2']"
    )
```

**目的**：让前端"文章骨架"的每个部分可以点击跳转到对应原文段落。当前 `StructurePart` 只有 label/title/summary，无法关联到原文。

#### 3.1.2 新增 `SectionInterpretation` — 分段讲解

```python
class SectionInterpretation(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    structure_index: int = Field(
        description="对应 structure 列表的索引，如 0 对应 structure[0]"
    )
    title: str = Field(
        description="该段讲解的标题，通常与 structure[structure_index].title 一致"
    )
    analysis: str = Field(
        description="该段的讲解文本，200-400 字"
    )
```

#### 3.1.3 `DailyInterpretationDraft` — 从单文本改为分段

```python
# 之前
class DailyInterpretationDraft(BaseModel):
    full_article_analysis: str = Field(description="Full article interpretation text")

# 之后
class DailyInterpretationDraft(BaseModel):
    section_interpretations: list[SectionInterpretation] = Field(
        default_factory=list,
        description="按文章结构分段的讲解，每段对应 structure 的一部分"
    )
    overview: str = Field(
        default="",
        description="整体导读（1-2 句），放在所有分段讲解之前"
    )
```

**变更理由**：

1. `full_article_analysis` 是一整段 500-1000 字文本，前端只能用 `splitLectureParagraphs` 硬切，语义经常断裂
2. 分段讲解天然对应"文章骨架"的结构，用户可以按需阅读某一部分
3. 每段 200-400 字，认知负荷可控
4. `overview` 提供整体视角，放在分段讲解之前作为过渡

#### 3.1.4 `DailyRefinementDraft` — 更新 refined_interpretation 类型

```python
# 之前
class DailyRefinementDraft(BaseModel):
    abort: bool = False
    refined_highlights: list[DailyHighlightDetail] | None = None
    refined_footer: DailyFooterDraft | None = None
    refined_interpretation: str | None = None  # ← 单文本

# 之后
class DailyRefinementDraft(BaseModel):
    abort: bool = False
    refined_highlights: list[DailyHighlightDetail] | None = None
    refined_footer: DailyFooterDraft | None = None
    refined_interpretation: DailyInterpretationDraft | None = None  # ← 结构化
```

### 3.2 Prompt 修改

#### 3.2.1 `daily_footer.yaml` — 增加 paragraph_ids 指引

```yaml
description: 每日精读文末解析助手的系统指令
content: |
  你是一位英语文章深度分析助手，为每日精读生成文末解析内容。

  你需要生成以下内容：
  1. summary：一句话摘要（中文）
  2. thesis_and_intent：包含 thesis（文章主旨）和 author_intent（作者意图）的对象
  3. structure：文章结构分解（2-4 个部分，每部分含 label、title、summary、paragraph_ids）
     - paragraph_ids：该部分对应的原文段落 ID 列表，如 ["p_0", "p_1"]
     - 段落 ID 在输入的 paragraphs_info 区块中提供，格式为 p_0, p_1, p_2...
  4. key_expressions：3-5 个关键表达（含 expression、gloss、context_sentence）
  5. misreading_points：1-3 个易误读点（含 point、clarification）
  6. discussion_questions：2-3 个讨论问题（英文）

  分析要有深度，帮助中国英语学习者理解文章的深层含义和写作技巧。
  不要逐句翻译，要提供有洞察力的分析。
  structure 中的 paragraph_ids 必须准确对应输入的段落，这是用户跳转阅读的关键。
```

#### 3.2.2 `daily_interpretation.yaml` — 从单文本改为分段讲解

```yaml
description: 每日精读分段讲解助手的系统指令
content: |
  你是一位英语文章讲解助手，为每日精读生成分段讲解。

  你需要生成：
  1. overview：整体导读（1-2 句中文，概括文章核心，放在所有分段讲解之前）
  2. section_interpretations：按文章结构分段的讲解列表
     - 每段对应 structure 中的一个部分（通过 structure_index 关联）
     - 每段包含：structure_index（整数）、title（标题）、analysis（讲解文本）
     - analysis 长度：200-400 字
     - 讲解风格：像一位优秀的英语老师在课堂上讲解这一段——先讲大意，再讲亮点和手法

  讲解要求：
  - 用中文撰写，关键英文表达保留原文
  - 每段讲解独立可读，但整体连贯
  - 不要逐句翻译，要提供有洞察力的分析
  - 涵盖：该段的核心论点、论证逻辑、写作手法、语言亮点
  - structure 信息会在输入的 structure_info 区块中提供，按顺序为每部分生成讲解
```

### 3.3 Agent Deps 修改

#### 3.3.1 `DailyFooterAgentDeps` — 增加 paragraphs_info

```python
@dataclass
class DailyFooterAgentDeps:
    full_text: str
    title: str
    highlights_summary: str = ""
    paragraphs_info: str = ""  # NEW: 段落 ID 列表信息
    prompt_strategy: DailyPromptStrategy = field(default_factory=build_footer_analysis_strategy)
```

`build_daily_footer_prompt` 中加入段落信息：

```python
def build_daily_footer_prompt(deps: DailyFooterAgentDeps) -> str:
    sections = build_daily_prompt_sections(deps.prompt_strategy)
    all_sections = list(sections) + [
        PromptSection("article_info", (f"Title: {deps.title}",)),
        PromptSection("full_text", (deps.full_text[:6000],)),
    ]
    if deps.paragraphs_info:
        all_sections.append(PromptSection("paragraphs_info", (deps.paragraphs_info,)))
    if deps.highlights_summary:
        all_sections.append(PromptSection("highlights_context", (deps.highlights_summary,)))
    return render_prompt_sections(all_sections)
```

#### 3.3.2 `DailyInterpretationAgentDeps` — 增加 structure_info

```python
@dataclass
class DailyInterpretationAgentDeps:
    full_text: str
    title: str
    footer_summary: str = ""
    structure_info: str = ""  # NEW: structure 信息
    prompt_strategy: DailyPromptStrategy = field(default_factory=build_full_interpretation_strategy)
```

`build_daily_interpretation_prompt` 中加入 structure 信息：

```python
def build_daily_interpretation_prompt(deps: DailyInterpretationAgentDeps) -> str:
    sections = build_daily_prompt_sections(deps.prompt_strategy)
    all_sections = list(sections) + [
        PromptSection("article_info", (f"Title: {deps.title}",)),
        PromptSection("full_text", (deps.full_text[:6000],)),
    ]
    if deps.structure_info:
        all_sections.append(PromptSection("structure_info", (deps.structure_info,)))
    if deps.footer_summary:
        all_sections.append(PromptSection("footer_context", (deps.footer_summary,)))
    return render_prompt_sections(all_sections)
```

### 3.4 Workflow 节点修改

#### 3.4.1 `footer_analysis_node` — 传入段落信息

```python
async def footer_analysis_node(state: DailyReaderState) -> dict:
    full_text = state.get("original_text", "")
    title = state.get("title", "")
    highlights = state.get("highlights_json", [])
    paragraphs = state.get("normalized_paragraphs", [])  # NEW

    # 构建段落信息字符串
    paragraphs_info = ""
    if paragraphs:
        lines = []
        for p in paragraphs:
            pid = p.get("paragraph_id", "")
            text_preview = p.get("text", "")[:80]
            lines.append(f"{pid}: {text_preview}...")
        paragraphs_info = "\n".join(lines)

    highlights_summary = ""
    if highlights:
        hl_texts = [h.get("text", "") for h in highlights[:10]]
        highlights_summary = f"已标注的关键词：{', '.join(hl_texts)}"

    deps = DailyFooterAgentDeps(
        full_text=full_text,
        title=title,
        highlights_summary=highlights_summary,
        paragraphs_info=paragraphs_info,  # NEW
    )
    # ... 其余逻辑不变
```

#### 3.4.2 `full_interpretation_node` — 传入 structure 信息

```python
async def full_interpretation_node(state: DailyReaderState) -> dict:
    full_text = state.get("original_text", "")
    title = state.get("title", "")
    footer = state.get("footer_analysis_json", {})

    # 构建 structure 信息
    structure_info = ""
    structure_list = footer.get("structure", [])
    if structure_list:
        lines = []
        for i, part in enumerate(structure_list):
            label = part.get("label", f"Part {i+1}")
            title_part = part.get("title", "")
            summary = part.get("summary", "")
            pids = part.get("paragraph_ids", [])
            lines.append(f"[{i}] {label}: {title_part} — {summary} (段落: {', '.join(pids)})")
        structure_info = "\n".join(lines)

    footer_summary = ""
    if footer:
        footer_summary = json.dumps(footer, ensure_ascii=False)[:1000]

    deps = DailyInterpretationAgentDeps(
        full_text=full_text,
        title=title,
        footer_summary=footer_summary,
        structure_info=structure_info,  # NEW
    )
    # ... 其余逻辑不变
```

#### 3.4.3 `daily_projection_node` — 组装新数据结构

```python
def daily_projection_node(state: DailyReaderState) -> dict:
    paragraphs = state.get("normalized_paragraphs", [])
    highlights = state.get("highlights_json", [])
    footer = state.get("footer_analysis_json", {})
    interpretation = state.get("full_interpretation", {})  # Now a dict from DailyInterpretationDraft

    corrected = _reconcile_highlights(paragraphs, highlights)

    # 合并 interpretation 到 footer
    if isinstance(interpretation, dict):
        footer = {**footer, "interpretation": interpretation}
    elif isinstance(interpretation, str) and interpretation:
        # 向后兼容：如果 interpretation 仍然是字符串（旧数据），包装成旧格式
        footer = {**footer, "full_article_analysis": interpretation}

    # ... 其余 body_paragraphs 逻辑不变
```

**注意**：`full_interpretation` 在 `DailyReaderState` 中的类型需要从 `str` 改为 `dict | str`，以兼容新旧两种格式。

### 3.5 Review / Refinement 修改

#### 3.5.1 `daily_review.yaml` — 增加审核维度

```
审核维度（7 个）：
1. highlight_accuracy
2. highlight_density
3. footer_completeness — 增加 paragraph_ids 完整性检查
4. footer_accuracy
5. interpretation_coherence — 改为检查 section_interpretations 的连贯性
6. interpretation_coverage — NEW: 检查每个 structure 部分是否都有对应讲解
7. annotation_consistency
```

#### 3.5.2 `DailyReviewDraft` — 无结构变更

`DailyReviewDraft` 本身不需要改，因为 `issues` 列表是通用的。但 prompt 中需要增加新维度的审核指引。

### 3.6 数据库 — 无需 Migration

`footer_analysis_json` 是 JSONB 列，可以存储任意 JSON 结构。新数据的 `interpretation` 字段会替代旧的 `full_article_analysis` 字段。前端需要兼容两种格式。

---

## 四、前端修改

### 4.1 类型定义变更

#### `daily-reader.vm.ts`

```typescript
export interface DailyReaderStructurePart {
  label: string
  title: string
  summary: string
  paragraphIds: string[]  // NEW
}

export interface SectionInterpretation {
  structureIndex: number
  title: string
  analysis: string
}

export interface DailyReaderFooterAnalysis {
  summary: string
  thesisAndIntent: {
    thesis: string
    authorIntent: string
  }
  structure: DailyReaderStructurePart[]
  keyExpressions: DailyReaderKeyExpression[]
  misreadingPoints: DailyReaderMisreadingPoint[]
  // 旧格式（向后兼容）
  fullArticleAnalysis?: string
  // 新格式
  interpretation?: {
    overview: string
    sectionInterpretations: SectionInterpretation[]
  }
  discussionQuestions: string[]
}
```

### 4.2 Adapter 变更

`daily-reader.adapter.ts` 中的 `dtoToFooterAnalysis` 需要处理新字段：

```typescript
function dtoToFooterAnalysis(dto: any): DailyReaderFooterAnalysis {
  const thesisAndIntent = dto?.thesis_and_intent
  return {
    summary: dto?.summary ?? '',
    thesisAndIntent: {
      thesis: thesisAndIntent?.thesis ?? '',
      authorIntent: thesisAndIntent?.author_intent ?? '',
    },
    // NEW: structure 的 paragraph_ids
    structure: Array.isArray(dto?.structure) ? dto.structure.map((s) => ({
      label: s.label,
      title: s.title,
      summary: s.summary,
      paragraphIds: Array.isArray(s.paragraph_ids) ? s.paragraph_ids : [],
    })) : [],
    keyExpressions: Array.isArray(dto?.key_expressions) ? dto.key_expressions.map((e) => ({
      expression: e.expression,
      gloss: e.gloss,
      contextSentence: e.context_sentence,
    })) : [],
    misreadingPoints: Array.isArray(dto?.misreading_points) ? dto.misreading_points.map((m) => ({
      point: m.point,
      clarification: m.clarification,
    })) : [],
    // NEW: interpretation（新格式）或 fullArticleAnalysis（旧格式）
    interpretation: dto?.interpretation ? {
      overview: dto.interpretation.overview ?? '',
      sectionInterpretations: Array.isArray(dto.interpretation.section_interpretations)
        ? dto.interpretation.section_interpretations.map((si) => ({
            structureIndex: si.structure_index,
            title: si.title,
            analysis: si.analysis,
          }))
        : [],
    } : undefined,
    fullArticleAnalysis: dto?.full_article_analysis ?? '',
    discussionQuestions: Array.isArray(dto?.discussion_questions) ? dto.discussion_questions : [],
  }
}
```

### 4.3 新组件

#### 4.3.1 `DailyReaderGuideCard` — 导读卡

位置：原文和 Tab 区之间，始终可见。

```
┌──────────────────────────────────┐
│  "这篇文章真正想说的是——          │
│   hybrid work 不是疫情妥协，      │
│   而是生产力的根本性重新定义。"    │
│                                  │
│  [看骨架 ↓]  [看讲解 ↓]          │  ← 快捷锚点按钮
└──────────────────────────────────┘
```

内容：
- summary（一句话摘要，加引号，大字突出）
- thesis（主旨，小字补充）
- 两个快捷按钮：点击切换到对应 Tab 并滚动到目标位置

设计要点：
- 视觉上与 Body 区有明确分隔（渐变分隔线或留白）
- 摘要用大号字体 + 衬线体，延续杂志感
- 按钮用 `--dr-accent` 色调，不抢眼但可发现

#### 4.3.2 `DailyReaderTabBar` — Tab 切换器

```
┌──────────────────────────────────┐
│  [ 速览 ]     [  深读  ]         │
│  ───────                          │  ← 活动指示线
└──────────────────────────────────┘
```

设计要点：
- 两个 Tab 等宽，活动 Tab 有下划线指示
- 切换时内容区平滑过渡
- Tab 标签用中文，与整体中文界面一致

#### 4.3.3 `DailyReaderOverviewTab` — 速览 Tab 内容

1. **文章骨架** — 可折叠列表
   - 每项显示：编号圆圈 + label + title + summary
   - 每项可点击，滚动到原文对应段落（利用 `paragraphIds`）
   - 默认展开，可整体折叠

2. **别读偏了** — 紧凑卡片
   - 误区/正解配对卡片
   - 保持当前视觉风格

3. **值得带走的表达** — **网格布局**（修复 spec 合规性）
   - 从垂直列表改为 2 列网格
   - 每个表达卡片可点击（tappable cards）
   - 点击弹出 bottom sheet 显示完整 context_sentence

#### 4.3.4 `DailyReaderDeepReadTab` — 深读 Tab 内容

1. **整体导读**（overview，1-2 句）
   - 轻量文字，作为分段讲解的前言

2. **分段精读讲解**
   - 每段对应一个 structure 部分
   - 标题 + 可折叠讲解文本
   - **默认展开第一段，其余折叠**（渐进揭示）
   - 每段下方有"回到原文"按钮（跳转到对应段落）

3. **思考讨论**
   - 保持当前样式

### 4.4 现有组件修改

#### 4.4.1 `DailyReaderBody` — 增加段落锚点

为每个段落添加 `id` 属性，支持从骨架跳转：

```tsx
<View key={paragraph.id} id={`para-${paragraph.id}`} className='daily-body__paragraph'>
```

#### 4.4.2 `DailyReaderFooterAnalysis` — 重构或替换

当前组件将被拆分为 `DailyReaderOverviewTab` + `DailyReaderDeepReadTab`，原组件可保留用于旧数据兼容回退，或直接移除。

### 4.5 页面结构变更

```tsx
// daily-reader/index.tsx
export default function DailyReaderPage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'deep'>('overview')
  // ...

  return (
    <View className='daily-page'>
      <NavBar ... />
      <DailyReaderProgress />
      <DailyReaderHeader article={article} />
      <View className='daily-page__body-divider' />
      <DailyReaderBody
        body={article.body}
        highlights={article.highlights}
        onHighlightClick={handleHighlightClick}
        onWordClick={handleWordClick}
        showHighlightHint={showHighlightHint}
      />
      <DailyReaderGuideCard
        summary={article.footerAnalysis.summary}
        thesis={article.footerAnalysis.thesisAndIntent.thesis}
        onNavigate={handleGuideNavigate}
      />
      <DailyReaderTabBar activeTab={activeTab} onTabChange={setActiveTab} />
      {activeTab === 'overview' ? (
        <DailyReaderOverviewTab
          footerAnalysis={article.footerAnalysis}
          onStructureClick={handleStructureClick}
        />
      ) : (
        <DailyReaderDeepReadTab
          footerAnalysis={article.footerAnalysis}
          onBackToParagraph={handleBackToParagraph}
        />
      )}
      {/* sticky bar, word popup, hint overlay — 不变 */}
    </View>
  )
}
```

---

## 五、向后兼容策略

| 场景 | 处理方式 |
|------|---------|
| 新数据（有 `interpretation.sectionInterpretations`） | 使用分段讲解，Tab 架构完整 |
| 旧数据（只有 `fullArticleAnalysis`） | 深读 Tab 回退到旧逻辑：用 `splitLectureParagraphs` 切分，无段落跳转 |
| 旧数据（structure 无 `paragraphIds`） | 骨架跳转按钮隐藏，其余功能正常 |
| 旧数据（无 `interpretation` 也无 `fullArticleAnalysis`） | 深读 Tab 显示空状态 |

兼容判断逻辑：

```typescript
function hasNewFormat(fa: DailyReaderFooterAnalysis): boolean {
  return !!fa.interpretation && fa.interpretation.sectionInterpretations.length > 0
}

function hasLegacyFormat(fa: DailyReaderFooterAnalysis): boolean {
  return !hasNewFormat(fa) && !!fa.fullArticleAnalysis
}
```

---

## 六、实施顺序

| 步骤 | 内容 | 依赖 | 涉及文件 |
|------|------|------|---------|
| **1** | 后端 schema 变更 | 无 | `server/app/schemas/internal/daily_drafts.py` |
| **2** | 后端 prompt 变更 | 步骤 1 | `server/prompts/agents/daily_footer.yaml`、`daily_interpretation.yaml`、`daily_review.yaml` |
| **3** | 后端 agent deps 变更 | 步骤 2 | `server/app/agents/daily_footer_agent.py`、`daily_interpretation_agent.py` |
| **4** | 后端 workflow 节点变更 | 步骤 3 | `server/app/workflow/daily_reader_workflow.py` |
| **5** | 后端 review/refinement 适配 | 步骤 1 | `server/app/agents/daily_review_agent.py`、`daily_refinement_agent.py`、`server/prompts/agents/daily_review.yaml`、`daily_refinement.yaml` |
| **6** | 前端类型 + adapter 变更 | 步骤 1 | `client/src/types/view/daily-reader.vm.ts`、`client/src/services/api/adapters/daily-reader.adapter.ts` |
| **7** | 前端新组件 | 步骤 6 | `client/src/components/DailyReaderGuideCard/`、`DailyReaderTabBar/`、`DailyReaderOverviewTab/`、`DailyReaderDeepReadTab/` |
| **8** | 前端页面结构重构 | 步骤 7 | `client/src/packageB/daily-reader/index.tsx`、`index.scss` |
| **9** | 端到端验证 | 步骤 4+8 | Pipeline → 新数据 → 前端渲染 |
| **10** | 旧数据兼容验证 | 步骤 9 | 旧 article ID → 前端回退渲染 |

---

## 七、风险与注意事项

### 7.1 LLM 输出稳定性

`paragraph_ids` 和 `structure_index` 是结构化字段，LLM 可能生成不准确的值。`_reconcile_highlights` 已有类似的纠偏逻辑，可能需要为 `paragraph_ids` 增加类似校验：

```python
def _validate_paragraph_ids(structure: list[dict], paragraphs: list[dict]) -> list[dict]:
    valid_pids = {p.get("paragraph_id") for p in paragraphs}
    for part in structure:
        pids = part.get("paragraph_ids", [])
        part["paragraph_ids"] = [pid for pid in pids if pid in valid_pids]
    return structure
```

### 7.2 分段讲解的连贯性

从一整段文本改为分段后，需要确保各段之间仍然连贯。`overview` 字段就是为了提供过渡。Prompt 中需要强调"每段独立可读，但整体连贯"。

### 7.3 Token 消耗

分段讲解的总长度可能与原来相当，但 prompt 中需要额外传入 structure 信息，会增加少量 token。预估增加约 200-400 token/篇。

### 7.4 旧数据迁移

不需要迁移旧数据，前端兼容两种格式即可。但如果需要，可以写一个一次性脚本对旧数据重新运行 interpretation 节点。

### 7.5 `DailyReaderState` 类型调整

`full_interpretation` 字段需要从 `str` 改为 `dict | str`，以兼容新旧两种格式。workflow 中所有读取该字段的节点都需要适配。

---

## 八、评审要点

请重点关注以下决策点：

1. **`DailyInterpretationDraft` 从 `full_article_analysis: str` 改为 `section_interpretations: list[SectionInterpretation]`** — 这是最核心的后端变更，影响 workflow、prompt、refinement
2. **`StructurePart` 增加 `paragraph_ids`** — 这依赖 LLM 正确输出段落 ID，需要校验逻辑
3. **Tab 分层的前端组件拆分方式** — 速览/深读的内容划分是否合理
4. **导读卡的位置和内容** — summary + thesis 是否足够吸引人继续阅读
5. **向后兼容策略** — 是否需要旧数据迁移脚本，还是纯前端兼容足够

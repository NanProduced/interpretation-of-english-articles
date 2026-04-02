# V2.1 改造设计稿

> 文档定位：用于指导 Claread透读 当前 workflow 主线的设计、开发、联调与验收。
>
> 生效范围：`v2.1` 相关的 schema、prompt、validator、API 投影、前端 mock、结果页 UI/UX 改造。
>
> 冲突处理：当本文件与 [V2 统一设计文档（归档）](./archive/v2-unified-design.md) 存在冲突时，开发、评审、联调一律以本文件为准；归档文档仅保留为历史背景。
>
> 更新时间：2026-04-01
> 状态：当前主设计稿（唯一参考）

***

## 1. 背景与目标

当前 `v2` 已完成一轮可运行实现，但从同一样本的多次模型输出、Notion 方案对照以及本地代码实现来看，现状存在三类核心问题：

1. 模型输出协议偏离了原始的组件化方案。
2. 输出内容选择和渲染分发不稳定。
3. 前端结果页虽然可演示，但 mock 覆盖不充分，且 UI/UX 质感偏弱，不足以支撑产品化验证。

`v2.1` 的目标不是继续在现有 `inline_marks / sentence_entries / cards` 统一容器上做小修小补，而是：

1. 回归组件化 annotation schema，让模型先决定语义组件，再填最小必要字段。
2. 保留前端所需的统一渲染层，但把它降级为后端投影结果，而不是 LLM 的直接输出目标。
3. 移除当前阶段不必要的百科型卡片能力，集中稳定核心英语教学标注。
4. 同步升级前端 mock 与结果页设计，使其足以评估所有标注类型的真实显示效果。

***

## 2. 范围

### 2.1 In Scope

本次 `v2.1` 改造包含：

1. 后端内部输出协议从统一草稿模型切换为带鉴别器的 annotation union。
2. Prompt 重写为“组件目录式”结构。
3. 增加输出校验与失败兜底逻辑。
4. API 响应层增加从 annotation schema 到 render scene schema 的投影逻辑。
5. 前端 `result-v2` mock 页面重做，要求覆盖全部标注组件与全部解析类型。
6. 前端结果页 UI/UX 重新设计，提升视觉质量、层级表达与交互体验。
7. 点词查释义链路改为：前端调用后端接口，由后端再调用第三方词典能力。

### 2.2 Out of Scope

本次 `v2.1` 改造不包含：

1. `CardDraft` / 段间百科型卡片能力。
2. 全文分析 / 付费能力 / 高阶卡片体系。
3. 历史记录、学习记录、收藏、生词本落库。
4. 完整鉴权、埋点、消息通知。
5. OCR、新输入源、新业务模式。

### 2.3 明确裁剪

`CardDraft` 在 `v2.1` 中直接移出 schema、prompt、assembly 与前端消费链路。后续如果做付费版“全文分析”，再以独立能力重新设计并引入。

***

## 3. 改造性质判断

### 3.1 结论

`v2.1` 对工程实施来说是一次**受控重构**，不是简单更新，也不是整套推倒重做。

### 3.2 判断依据

1. 后端内部协议会发生根本变化：
   - `AnnotationOutput` 从统一容器切回 annotation union。
   - Agent `output_type` 与 prompt 结构要重写。
   - assembly 从“草稿转前端模型”变为“语义组件转渲染模型”。
2. 前端 UI 原语本身不需要推翻：
   - `SentenceRow`
   - `InlineMark`
   - `WordPopup`
   - `SentenceActionChip`
   - `BottomSheetDetail`
3. 但前端数据契约会升级：
   - 不再让模型直接输出 `tone / render_type / entry_type` 组合式渲染决策。
   - 渲染决策改由后端投影层统一生成。

### 3.3 对外建议叫法

为了避免概念混乱，建议：

1. 对外文档与开发讨论统一称为 `v2.1`。
2. 对内实施定义为：
   - 后端内部协议重构
   - API 渲染契约升级
   - 前端结果页与 mock 联动更新

***

## 4. 当前问题复盘

### 4.1 架构层问题

1. `InlineMarkDraft` 吞并了词汇、短语、语境义、语法四种本应独立的组件。
2. `SentenceEntryDraft` 把 grammar / sentence\_analysis / context 压成了一个自由文本入口。
3. `CardDraft` 引入了当前阶段无必要的新概念，并消耗模型注意力预算。
4. `multi_text` 虽已定义，但在统一容器语境下几乎不被模型使用。

### 4.2 输出层问题

1. tone 分配不稳定。
2. 词和短语的锚点粒度不稳定。
3. `ai_note / ai_body / ai_title` 大量为空。
4. 语言不统一，中英文混用。
5. 与 Golden 标注相比，覆盖率偏低，尤其是 `context_gloss` 和长难句拆解。

### 4.3 前端层问题

1. mock 数据没有系统性覆盖全部组件与边界情况。
2. UI 仍偏演示稿，视觉语言保守，缺少产品感。
3. 组件虽然可用，但对不同标注类型的视觉层级表达还不够清晰。

***

## 5. 设计原则

### 5.1 模型只负责语义决策，不直接负责最终渲染决策

LLM 应输出：

1. 这是什么组件类型。
2. 它锚定在哪。
3. 该组件的必要教学信息是什么。

LLM 不应直接决定：

1. 前端颜色体系。
2. 句尾入口与词级入口的视觉细节。
3. 是否插入卡片。

### 5.2 后端承担投影与稳定化职责

后端负责：

1. annotation schema 校验。
2. 锚点解析与失败降级。
3. annotation → render scene 投影。
4. 输出预算与内容分发的二次约束。
5. 统一词典查询代理能力。

### 5.3 前端只消费稳定渲染模型

前端不直接依赖 LLM 的原始 annotation 输出。前端消费的是后端投影后的 render scene，以降低联调噪音并保持 UI 一致性。

### 5.4 mock 页面必须覆盖所有组件与解析类型

`v2.1` 后的 mock 页面不是简单示意，而是前端验收工具。必须覆盖：

1. `VocabHighlight`
2. `PhraseGloss`
3. `ContextGloss`
4. `GrammarNote`
5. `SentenceAnalysis`
6. `SentenceTranslation`
7. 单段锚点
8. 多段锚点
9. 单词查询
10. 短语查询
11. 语法说明
12. 句子拆解
13. 中英双语显示
14. 不同 page mode 下的视觉差异

### 5.5 结果页 UI/UX 必须同步升级

本次改造不仅是 schema 优化，也包含结果页重设计。目标不是“让旧页面继续吃新数据”，而是趁此机会把结果页打磨到足以支撑产品判断。

***

## 6. Pydantic v2 约束

### 6.1 采用带鉴别器的 Union

`v2.1` 的 annotation schema 必须基于 **Pydantic v2 Discriminated Union** 实现，而不是普通 `Union`。

根据 Pydantic 官方文档：

1. Discriminated unions 更高效、更可预测。
2. 每个成员模型需要共享同一个鉴别字段。
3. 该字段在每个成员模型中应使用 `Literal[...]` 固定取值。
4. Union 字段本身需要通过 `Field(discriminator='...')` 指定鉴别器。

官方参考：

- [Pydantic Unions / Discriminated Unions](https://docs.pydantic.dev/latest/concepts/unions/)

### 6.2 设计要求

本项目中统一使用 `type` 作为 annotation 的鉴别字段。

也就是说：

1. 每个 annotation 模型都必须包含 `type: Literal["..."]`
2. 顶层 `annotations` 必须使用带 discriminator 的 union
3. 不允许依赖 `smart union` 猜测成员类型

### 6.3 推荐写法

```python
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class VocabHighlight(BaseModel):
    type: Literal["vocab_highlight"] = "vocab_highlight"
    sentence_id: str
    text: str
    exam_tags: list[str]


class PhraseGloss(BaseModel):
    type: Literal["phrase_gloss"] = "phrase_gloss"
    sentence_id: str
    text: str
    phrase_type: str
    zh: str


Annotation = Annotated[
    Union[VocabHighlight, PhraseGloss],
    Field(discriminator="type"),
]
```

### 6.4 建模收紧原则

为提升结构化输出稳定性，`v2.1` 的 Pydantic 模型遵循以下原则：

1. 内部 schema 默认启用 `extra="forbid"`，禁止模型偷偷输出未定义字段。
2. 内部 schema 默认启用 `str_strip_whitespace=True`，降低无意义空白噪音。
3. 能用 `Literal`、长度约束、列表长度约束表达的约束，优先下沉到 schema，而不是只写在 prose 规则里。
4. 不让 LLM 生成纯协议元数据；例如 `schema_version` 应由后端注入，而不是由模型自由输出。
5. 只在确实需要模型判断的地方保留开放字符串，不把所有字段都做成自由文本。

推荐写法：

```python
from pydantic import BaseModel, ConfigDict


class BaseAnnotationModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )
```

***

## 7. 目标数据分层

`v2.1` 采用双层数据结构：

1. **内部语义层**：LLM 输出的 annotation union。
2. **外部渲染层**：API 返回的 render scene。

### 7.1 内部语义层

```text
AnnotationOutput
├── annotations: list[Annotation]
└── sentence_translations: list[SentenceTranslation]
```

其中：

```text
Annotation =
  VocabHighlight
  PhraseGloss
  ContextGloss
  GrammarNote
  SentenceAnalysis
```

### 7.2 外部渲染层

```text
RenderSceneModel
├── article
├── translations
├── inline_marks
├── sentence_entries
└── warnings
```

说明：

1. `cards` 在 `v2.1` 中移除。
2. `inline_marks` 与 `sentence_entries` 继续保留为前端统一消费层，但不再是模型原始输出结构。

***

## 8. 内部 Schema 设计

### 8.1 基础类型

#### `SpanRef`

用途：表示一个锚点片段，支持多段锚点。

```python
class SpanRef(BaseModel):
    text: str
    occurrence: int | None = None
    role: str | None = None
```

字段说明：

1. `text`
   - 必填
   - 必须是 `sentence_id` 对应句子的真实子串
   - 建议 `min_length=1`, `max_length=80`
2. `occurrence`
   - 可选
   - 当同一句中相同文本出现多次时，指明命中第几次
3. `role`
   - 可选
   - 用于表达该片段在结构中的角色，例如 `trigger`, `result_clause`, `connector`

#### `Chunk`

用途：表示长难句拆解中的一个结构块。

```python
class Chunk(BaseModel):
    order: int
    label: str
    text: str
    occurrence: int | None = None
```

字段说明：

1. `order`
   - 必填
   - 表示阅读顺序，从 1 开始
2. `label`
   - 必填
   - 例如 `主语`、`谓语`、`宾语从句`、`时间状语`
   - 建议 `min_length=1`, `max_length=24`
3. `text`
   - 必填
   - 必须是对应句子的真实子串
   - 建议 `min_length=1`, `max_length=120`
4. `occurrence`
   - 可选
   - 当 chunk 文本重复出现时用于定位

#### `SentenceTranslation`

```python
class SentenceTranslation(BaseModel):
    sentence_id: str
    translation_zh: str
```

要求：

1. 必须覆盖所有句子。
2. 每句只能有一个翻译。
3. 语言统一为自然中文。
4. `translation_zh` 建议 `min_length=1`, `max_length=220`。

#### `ArticleParagraph`

```python
class ArticleParagraph(BaseModel):
    paragraph_id: str
    sentence_ids: list[str]
```

#### `ArticleSentence`

```python
class ArticleSentence(BaseModel):
    sentence_id: str
    paragraph_id: str
    text: str
```

#### `ArticleStructure`

```python
class ArticleStructure(BaseModel):
    source_type: Literal["user_input", "daily_article", "ocr"]
    source_text: str
    render_text: str
    paragraphs: list[ArticleParagraph]
    sentences: list[ArticleSentence]
```

说明：

1. `source_text`
   - 原始输入
2. `render_text`
   - 清洗后用于锚点解析与渲染的标准文本
3. `paragraphs`
   - 提供段落顺序和句子归属
4. `sentences`
   - 提供句级文本，是前端渲染和锚点定位的唯一正文基准

### 8.2 Annotation 组件

#### `VocabHighlight`

用途：考试词、重点词、超纲词高亮。

```python
class VocabHighlight(BaseModel):
    type: Literal["vocab_highlight"] = "vocab_highlight"
    sentence_id: str
    text: str
    occurrence: int | None = None
    exam_tags: list[ExamTag]
```

职责边界：

1. `VocabHighlight` 只负责选词和打 `exam_tags`
2. **不输出释义**
3. 释义、音标、发音、词性等词典数据由后端词典代理接口提供

`exam_tags` 规则：

1. 标签来源于后端预定义集合，不允许自由发明
2. 当前建议范围：
   - `gaokao`
   - `gre`
   - `cet`
   - `ielts_toefl`
3. 模型应优先输出与用户当前配置相关的标签
4. 可以输出多个标签，但不应无节制泛化

建议定义为：

```python
ExamTag = Literal[
    "gaokao",
    "gre",
    "cet",
    "ielts_toefl",
]
```

额外约束建议：

1. `text` 建议 `min_length=1`, `max_length=40`
2. `exam_tags` 建议 `min_length=1`, `max_length=2`

#### `PhraseGloss`

用途：短语、搭配、固定表达、专有名词释义。

```python
class PhraseGloss(BaseModel):
    type: Literal["phrase_gloss"] = "phrase_gloss"
    sentence_id: str
    text: str
    occurrence: int | None = None
    phrase_type: Literal["collocation", "phrasal_verb", "idiom", "proper_noun", "compound"]
    zh: str
```

额外约束建议：

1. `text` 建议 `min_length=1`, `max_length=80`
2. `zh` 建议 `min_length=1`, `max_length=40`

#### `ContextGloss`

用途：词典解释不足时的语境义补充。

```python
class ContextGloss(BaseModel):
    type: Literal["context_gloss"] = "context_gloss"
    sentence_id: str
    text: str
    occurrence: int | None = None
    gloss: str
    reason: str
```

额外约束建议：

1. `text` 建议 `min_length=1`, `max_length=40`
2. `gloss` 建议 `min_length=1`, `max_length=40`
3. `reason` 建议 `min_length=1`, `max_length=100`

#### `GrammarNote`

用途：轻量语法旁注。

```python
class GrammarNote(BaseModel):
    type: Literal["grammar_note"] = "grammar_note"
    sentence_id: str
    spans: list[SpanRef]
    label: str
    note_zh: str
```

要求：

1. `spans` 为必填。
2. 必须支持多段锚点。
3. 不做 grammar tag 枚举约束。
4. 语法名称与标签风格主要通过 few-shot 和 prompt 风格约束保持一致。
5. `spans` 建议 `min_length=1`, `max_length=4`。
6. `label` 建议 `min_length=1`, `max_length=24`。
7. `note_zh` 建议 `min_length=1`, `max_length=120`。

#### `SentenceAnalysis`

用途：真正复杂句的结构化拆解。

```python
class SentenceAnalysis(BaseModel):
    type: Literal["sentence_analysis"] = "sentence_analysis"
    sentence_id: str
    label: str
    teach: str
    chunks: list[Chunk]
```

要求：

1. `chunks` 为必填。
2. `chunks` 按阅读顺序排列。
3. `chunks` 需尽量覆盖整句，不允许明显重叠。
4. `chunks` 建议 `min_length=2`, `max_length=8`。
5. `label` 建议 `min_length=1`, `max_length=24`。
6. `teach` 建议 `min_length=1`, `max_length=300`。

### 8.3 Annotation Union

```python
Annotation = Annotated[
    Union[
        VocabHighlight,
        PhraseGloss,
        ContextGloss,
        GrammarNote,
        SentenceAnalysis,
    ],
    Field(discriminator="type"),
]
```

### 8.4 顶层输出

```python
class AnnotationOutput(BaseModel):
    annotations: list[Annotation]
    sentence_translations: list[SentenceTranslation]
```

说明：

1. `schema_version` 不作为 LLM 输出字段。
2. `schema_version = "2.1.0"` 由后端在最终 API 响应封装阶段注入。
3. `AnnotationOutput` 作为模型直接输出时，只保留语义内容字段，减少无意义协议决策。

***

## 9. Render Scene 投影设计

### 9.1 投影目标

后端将 annotation union 投影为前端当前仍适合消费的 render scene：

1. `VocabHighlight` → `inline_mark`
2. `PhraseGloss` → `inline_mark`
3. `ContextGloss` → `inline_mark`
4. `GrammarNote` → `inline_mark` + `sentence_entry`
5. `SentenceAnalysis` → `sentence_entry`

### 9.2 Render Scene 类型冻结

#### `InlineMark`

```python
class InlineMark(BaseModel):
    id: str
    annotation_type: Literal[
        "vocab_highlight",
        "phrase_gloss",
        "context_gloss",
        "grammar_note",
    ]
    anchor: InlineMarkAnchor
    render_type: Literal["background", "underline"]
    visual_tone: Literal["vocab", "phrase", "context", "grammar"]
    clickable: bool
    lookup_text: str | None = None
    lookup_kind: Literal["word", "phrase"] | None = None
    glossary: InlineGlossary | None = None
```

说明：

1. `annotation_type` 是语义来源，不是鉴别字段，只用于前端识别来源。
2. `visual_tone` 是渲染语义，不再使用当前模糊的 `tone`。
3. `glossary` 用于承载 LLM 提供的附加信息，例如：
   - `PhraseGloss.zh`
   - `ContextGloss.gloss`
   - `ContextGloss.reason`
4. `VocabHighlight` 通常不带 glossary，由后端词典接口补充词典数据。

#### `InlineGlossary`

```python
class InlineGlossary(BaseModel):
    zh: str | None = None
    gloss: str | None = None
    reason: str | None = None
```

说明：

1. 不再使用 `dict[str, str]` 这种隐式协议。
2. `PhraseGloss` 通常只填 `zh`。
3. `ContextGloss` 通常填 `gloss` 和 `reason`。
4. `VocabHighlight` 默认不填。

#### `InlineMarkAnchor`

```python
class TextAnchor(BaseModel):
    kind: Literal["text"] = "text"
    sentence_id: str
    anchor_text: str
    occurrence: int | None = None


class MultiTextAnchor(BaseModel):
    kind: Literal["multi_text"] = "multi_text"
    sentence_id: str
    parts: list[SpanRef]


InlineMarkAnchor = Annotated[
    Union[TextAnchor, MultiTextAnchor],
    Field(discriminator="kind"),
]
```

#### `SentenceEntry`

```python
class SentenceEntry(BaseModel):
    id: str
    sentence_id: str
    entry_type: Literal["grammar_note", "sentence_analysis"]
    label: str
    title: str | None = None
    content: str
```

#### `Warning`

```python
class Warning(BaseModel):
    code: str
    level: Literal["info", "warning", "error"]
    message: str
    sentence_id: str | None = None
    annotation_id: str | None = None
```

说明：

1. `code`
   - 稳定错误码，例如 `anchor_resolve_failed`
2. `level`
   - 前端可据此决定展示层级
3. `message`
   - 面向日志与调试的可读信息
4. `sentence_id`
   - 可选，用于关联具体句子
5. `annotation_id`
   - 可选，用于关联具体标注

#### `RenderSceneModel`

```python
class RenderSceneModel(BaseModel):
    schema_version: Literal["2.1.0"] = "2.1.0"
    article: ArticleStructure
    translations: list[SentenceTranslation]
    inline_marks: list[InlineMark]
    sentence_entries: list[SentenceEntry]
    warnings: list[Warning] = []
```

### 9.3 VocabHighlight 与词典接口适配

点词查释义的固定链路为：

1. 前端点击词或短语。
2. 前端请求后端词典接口。
3. 后端再调用第三方词典能力。
4. 后端返回标准化词典数据。
5. 前端弹出释义卡片。
6. 如果该词同时有 `VocabHighlight / PhraseGloss / ContextGloss` 的 LLM 附加注释，则显示在词典区域上方。

说明：

1. 前端不直接调用有道等第三方 API。
2. 词典调用受微信小程序网络与域名管控影响，统一收口到后端更稳。
3. 后端词典接口后续可以替换第三方实现，不影响前端交互。

### 9.4 词汇释义卡片的 UI 语义

词典弹层是统一入口，固定结构建议为：

1. 顶部：当前词或短语
2. 上方强调区：LLM 附加注释
   - 若存在 `PhraseGloss.zh`
   - 若存在 `ContextGloss.gloss / reason`
3. 下方主区域：词典 API 返回的音标、词性、义项、例句

也就是说：

1. API 释义是基础层
2. LLM 注释是增强层
3. 增强层显示在 API 释义区上方，突出其教学价值

### 9.5 GrammarNote 的投影规则

#### 行内投影

一个 `GrammarNote` 默认投影为 **一个** `inline_mark`，其 `anchor.kind` 可为：

1. `text`
2. `multi_text`

不拆成多个独立 `inline_mark`，原因：

1. 一个语法点在语义上是一个整体
2. 如果拆成多个 mark，前端会丢失“这些锚点属于同一语法现象”的关系

#### 句尾入口投影

一个 `GrammarNote` 默认**始终生成**一个 `sentence_entry`。

原因：

1. 行内标注负责“看见”
2. 句尾入口负责“展开解释”

不把生成条件建立在 spans 数量或 note\_zh 长度上，这样前后端行为更稳定。

#### 前端视觉规则

1. `GrammarNote` 统一使用下划线渲染
2. `multi_text` 各部分使用同色下划线
3. 第一版不强制实现复杂连线
4. 如需关联感，可在 hover/click 态强调同组 span

***

## 10. Prompt 设计要求

### 10.1 Prompt 结构

`v2.1` prompt 必须使用固定分层结构：

1. 角色定义
2. 用户规则
3. 组件目录
4. 锚点规则
5. 输出语言规则
6. density guidance
7. few-shot 示例

### 10.2 强约束

1. 所有中文字段必须输出中文。
2. `text` / `spans.text` / `chunks.text` 必须是对应句子的真实子串。
3. 不确定时不标。
4. `ContextGloss` 仅在词典义明显不够时使用。
5. `SentenceAnalysis` 仅用于真正复杂句。
6. `VocabHighlight` 不输出释义。

### 10.3 density guidance

不向模型下发篇章总量 budget，避免长文覆盖严重不足。

只保留密度指导：

1. 词汇/短语类标注通常多于语法点
2. 语法点通常多于长难句拆解
3. 长文应尽量分布到全文，而不是只覆盖开头几句
4. 不允许为了凑数输出低价值标注

### 10.4 few-shot 要求

至少提供：

1. 一个 `GrammarNote` 多段锚点示例。
2. 一个 `SentenceAnalysis` 带 chunks 的完整示例。
3. 一个 `ContextGloss` 示例。
4. 一个 `VocabHighlight` 只输出 exam\_tags、不输出释义的示例。

### 10.5 语法命名风格

不做 grammar tag 枚举约束，但 few-shot 必须体现：

1. 命名简洁
2. 中文教学表达稳定
3. 不随意发明过度花哨的标签

### 10.6 Prompt 结构化优化建议

为提升跨模型一致性，`v2.1` prompt 采用“短 system + 结构化组件目录 + 小而强的 few-shot”策略，不使用长篇自由说明。

推荐分块如下：

1. `Role`
   - 明确模型身份是“英语阅读教学标注器”，不是百科写作者
2. `Task`
   - 只做 annotation 与逐句翻译
3. `Hard Rules`
   - 中文输出
   - 真实子串锚点
   - 不确定就不标
   - 不输出卡片
   - `VocabHighlight` 不输出释义
4. `Component Catalog`
   - 逐个组件说明“什么时候该用、什么时候不该用”
5. `Anti-goals`
   - 不补背景知识
   - 不为了凑数硬标
   - 不把简单句也做 `SentenceAnalysis`
6. `Density guidance`
   - 只给相对密度提示，不给篇章总量预算
7. `Few-shot`
   - 只保留 3 到 5 个高代表性样例
8. `Output Checklist`
   - 在模型输出前做一次自检

### 10.7 Few-shot 选择策略

few-shot 不追求多，追求覆盖最容易漂移的分支。优先覆盖：

1. `VocabHighlight`
   - 只选词，不写释义
   - `exam_tags` 只给 1 到 2 个
2. `PhraseGloss`
   - 展示短语搭配和 `zh`
3. `ContextGloss`
   - 展示“为什么词典义不够”
4. `GrammarNote`
   - 展示多段锚点
5. `SentenceAnalysis`
   - 展示 `chunks + teach`

few-shot 选择原则：

1. 样例分布要接近真实文章难度
2. 样例风格必须统一中文口径
3. 样例里不要出现当前版本已经裁掉的能力，例如卡片或百科说明
4. 样例必须覆盖最难学会的 schema 分支，而不是最简单分支

### 10.8 Prompt 反模式

当前版本容易导致输出漂移的 prompt 反模式，需要在 `v2.1` 明确避免：

1. 把 UI 细节写进模型任务，导致模型替前端做渲染决策
2. 在同一段说明里混合“必须规则”和“风格建议”，导致强弱约束混淆
3. few-shot 过多但分布不统一，造成示例污染
4. 只说“输出 JSON”，但不强调每个组件的使用边界
5. 没有负例约束，导致模型顺手补百科知识或背景信息

### 10.9 建议的输出前自检

在 prompt 末尾增加短 checklist，要求模型在内部检查后再输出：

1. `annotations` 中每一项都有合法 `type`
2. 所有中文字段都为中文
3. 所有 `text / spans.text / chunks.text` 都是对应句子的真实子串
4. `VocabHighlight` 没有释义字段
5. 没有 `cards`
6. `sentence_translations` 覆盖全部句子

### 10.10 Prompt 评估指标

`v2.1` prompt 迭代建议固定评估以下指标，而不是只看主观感觉：

1. parse 成功率
2. 锚点解析成功率
3. 重复运行一致性
4. 组件覆盖率
5. 中文一致性
6. 平均输出 token
7. 平均耗时
8. Golden 样本召回率

建议每次 prompt 调整只改一类因素，例如：

1. 只改 few-shot
2. 只改组件说明
3. 只改 hard rules

避免多处同时修改后无法归因。

***

## 11. 锚点解析与容错策略

### 11.1 三级降级策略

所有锚点解析遵循：

1. **精确匹配**
   - 直接 `indexOf(text)`
2. **模糊匹配**
   - 在同一句内部做编辑距离或近似匹配
   - 第一版建议阈值：编辑距离 `< 3`
3. **失败丢弃**
   - 丢弃该 annotation
   - 记录 warning

### 11.2 occurrence 策略

`v2.1` 保留 `occurrence`，但规则调整为：

1. 默认不填
2. 仅当同一句中相同子串重复出现时才填
3. 前后端都必须支持

原因：

1. 大多数情况下不需要
2. 但完全删除会丢失多次出现时的精确定位能力

### 11.3 锚点失败率阈值

建议引入运行级阈值：

1. 单条失败：warning
2. 单次输出锚点失败率 `> 20%`：触发整次重试
3. 重试后仍超阈值：返回降级结果并显式记录 warning

### 11.4 SentenceAnalysis 特殊规则

如果 `SentenceAnalysis.chunks` 校验失败：

1. 优先尝试保留 `teach`
2. 降级生成一个普通 `sentence_entry`
3. 不生成错误的 chunk 渲染数据

***

## 12. 后端词典代理能力

### 12.1 新增能力

后端新增统一词典查询接口，负责：

1. 接收前端词或短语查询请求
2. 调用第三方词典服务
3. 返回标准化词典结果

### 12.2 设计动机

1. 微信小程序对外部网络访问和域名管理更严格
2. 第三方词典能力应被后端代理与保护
3. 便于未来统一缓存、限流、回退与多词典切换

### 12.3 与 annotation 的协作

后端词典接口返回：

1. 词典基础释义
2. 如命中了 annotation，可附带 annotation 侧增强信息

这样前端始终只调用一个接口，不分别拼装词典和 LLM 注释。

***

## 13. 前后端变更范围评估

### 13.1 后端

后端属于中到大改动，涉及：

1. `server/app/schemas/internal/analysis.py`
2. `server/app/agents/annotation.py`
3. `server/app/services/analysis/projection.py`
4. `server/app/schemas/analysis.py`
5. `server/tests/test_analyze_workflow.py`
6. `server/tests/test_preprocess_schema.py`
7. 词典代理接口及其服务层

后端改造重点：

1. 替换内部 output schema。
2. 重写 prompt。
3. 增加 validator。
4. 实现 annotation → render scene 投影。
5. 增加词典代理能力。

### 13.2 前端

前端属于中等改动，涉及：

1. `client/src/types/v2-render.ts`
2. `client/src/pages/result-v2/mock-data.ts`
3. `client/src/pages/result-v2/index.tsx`
4. `client/src/components/InlineMark`
5. `client/src/components/SentenceRow`
6. `client/src/components/WordPopup`
7. `client/src/components/BottomSheetDetail`

前端改造重点：

1. mock 页面覆盖全部组件与解析类型。
2. 结果页 UI/UX 重设计以及组件的优化或重构。
3. 词典卡片交互重做。
4. popup 与 bottom sheet 根据新语义分流。

***

## 14. 前端专项要求

### 14.1 Mock 页面验收要求

`result-v2` 的 mock 页面必须做到：

1. 一页内演示所有标注组件。
2. 演示单段锚点和多段锚点。
3. 演示词汇、短语、语境义、语法、句解的全部交互路径。
4. 演示 `immersive / bilingual / intensive` 三种模式。
5. 覆盖长句、短句、多句段落、边界锚点、冲突锚点。

mock 页面不是辅助材料，而是前端验收基线。

### 14.2 结果页 UI/UX 重设计要求

本次改造必须同步处理结果页设计问题。要求：

1. 避免当前“演示稿式”的老套布局。
2. 强化正文、翻译、标注、解释层级之间的区分。
3. `WordPopup` 和 `BottomSheetDetail` 需具备明确的产品感，而不是默认组件感。
4. 标注颜色、按钮、分组、段落节奏要形成统一视觉语言。
5. `immersive / bilingual / intensive` 三种模式要在视觉上明显可感知，而不是只切换显隐。
6. 在移动端小程序场景下保持紧凑、稳定、可快速扫读。

建议前端先出：

1. 新的 mock 页面结构
2. 颜色/层级/token 草案
3. 核心组件视觉方案

再进入联调。

***

## 15. 命名规范约束

本设计稿遵守仓库 [server/README.md](C:\Users\nanpr\miniprogram\interpretation-of-english-articles\server\README.md) 中的命名规范：

1. 版本号不进入业务命名。
2. 版本只出现在文档名、trace metadata、变更记录中，不进入 schema 类名、函数名、JSON 字段名。
3. Python 函数、JSON 字段名统一使用 `snake_case`。

因此：

1. 本设计稿中不再使用 `AnnotationOutputV21`、`RenderSceneModelV21` 这类命名。
2. 版本仅通过 `schema_version = "2.1.0"` 和文档路径表达。

***

## 16. 版本与迁移策略

### 16.1 版本建议

建议将本次能力标记为 `schema_version = 2.1.0`。

### 16.2 接口策略

当前后端主链已经直接收敛到：

1. 仅保留 `POST /analyze`
2. 对外响应统一为 `schema_version = "2.1.0"`
3. 不再保留旧 `v2` 并行接口或兼容链路

### 16.3 命名建议

1. 实现模块不带版本后缀，例如 `annotation.py`、`projection.py`、`analyze.py`
2. 版本信息只保留在文档、sample、trace metadata 和 `schema_version`
3. 历史样本、设计稿、评测数据可以继续使用 `v2.1` 前缀，避免和旧样本混淆

***

## 17. 分阶段实施步骤

### Phase 1：Schema Freeze

目标：冻结 `AnnotationOutput` 与 `RenderSceneModel`。

产出：

1. union schema
2. 基础类型
3. 渲染投影规则
4. validator 规则

### Phase 2：Backend Refactor

目标：完成后端内部协议重构。

产出：

1. 新 schema
2. 新 prompt
3. 新 projection
4. 词典代理接口
5. 单测更新

### Phase 3：Sample Regression

目标：用同一批样本验证稳定性改进。

要求：

1. 同一样本至少双模型双次输出对比。
2. 对比组件覆盖率、一致性、语言统一性、翻译完整性。

### Phase 4：Frontend Mock & Redesign

目标：完成前端 mock 与结果页重设计。

产出：

1. 全量 mock 页面
2. 新视觉方案
3. 新组件交互规范

### Phase 5：API 联调

目标：接通 `v2.1` 真数据联调。

要求：

1. 先联调 mock 对照场景。
2. 再联调真实输出。
3. 联调期间保留 warnings 可视化入口。

***

## 18. 对照表

### 18.1 后端内部 Schema 定稿

| 模型 | 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| `SpanRef` | `text` | `str` | 是 | 必须是对应句子的真实子串 |
| `SpanRef` | `occurrence` | `int \| None` | 否 | 同一句同子串重复出现时用于定位 |
| `SpanRef` | `role` | `str \| None` | 否 | 结构角色，如 `trigger`、`result_clause` |
| `Chunk` | `order` | `int` | 是 | 阅读顺序，从 1 开始 |
| `Chunk` | `label` | `str` | 是 | 成分名称，如 `主语`、`宾语从句` |
| `Chunk` | `text` | `str` | 是 | 必须是对应句子的真实子串 |
| `Chunk` | `occurrence` | `int \| None` | 否 | chunk 文本重复时用于定位 |
| `SentenceTranslation` | `sentence_id` | `str` | 是 | 关联句子 |
| `SentenceTranslation` | `translation_zh` | `str` | 是 | 自然中文翻译 |
| `ArticleParagraph` | `paragraph_id` | `str` | 是 | 段落稳定标识 |
| `ArticleParagraph` | `sentence_ids` | `list[str]` | 是 | 段内句子顺序 |
| `ArticleSentence` | `sentence_id` | `str` | 是 | 句子稳定标识 |
| `ArticleSentence` | `paragraph_id` | `str` | 是 | 句子所属段落 |
| `ArticleSentence` | `text` | `str` | 是 | 句子正文 |
| `ArticleStructure` | `source_type` | `Literal["user_input", "daily_article", "ocr"]` | 是 | 输入来源 |
| `ArticleStructure` | `source_text` | `str` | 是 | 原始输入 |
| `ArticleStructure` | `render_text` | `str` | 是 | 清洗后标准正文 |
| `ArticleStructure` | `paragraphs` | `list[ArticleParagraph]` | 是 | 段落结构 |
| `ArticleStructure` | `sentences` | `list[ArticleSentence]` | 是 | 句子结构 |
| `VocabHighlight` | `type` | `Literal["vocab_highlight"]` | 是 | Discriminator |
| `VocabHighlight` | `sentence_id` | `str` | 是 | 关联句子 |
| `VocabHighlight` | `text` | `str` | 是 | 目标词汇 |
| `VocabHighlight` | `occurrence` | `int \| None` | 否 | 同句重复时使用 |
| `VocabHighlight` | `exam_tags` | `list[ExamTag]` | 是 | 受控考试标签集合，建议 1 到 2 个 |
| `PhraseGloss` | `type` | `Literal["phrase_gloss"]` | 是 | Discriminator |
| `PhraseGloss` | `sentence_id` | `str` | 是 | 关联句子 |
| `PhraseGloss` | `text` | `str` | 是 | 目标短语 |
| `PhraseGloss` | `occurrence` | `int \| None` | 否 | 同句重复时使用 |
| `PhraseGloss` | `phrase_type` | `Literal["collocation", "phrasal_verb", "idiom", "proper_noun", "compound"]` | 是 | 短语分类 |
| `PhraseGloss` | `zh` | `str` | 是 | 中文释义 |
| `ContextGloss` | `type` | `Literal["context_gloss"]` | 是 | Discriminator |
| `ContextGloss` | `sentence_id` | `str` | 是 | 关联句子 |
| `ContextGloss` | `text` | `str` | 是 | 目标词汇 |
| `ContextGloss` | `occurrence` | `int \| None` | 否 | 同句重复时使用 |
| `ContextGloss` | `gloss` | `str` | 是 | 语境义 |
| `ContextGloss` | `reason` | `str` | 是 | 为什么词典义不够好 |
| `GrammarNote` | `type` | `Literal["grammar_note"]` | 是 | Discriminator |
| `GrammarNote` | `sentence_id` | `str` | 是 | 关联句子 |
| `GrammarNote` | `spans` | `list[SpanRef]` | 是 | 支持单段与多段锚点，建议 1 到 4 个 |
| `GrammarNote` | `label` | `str` | 是 | 语法点名称 |
| `GrammarNote` | `note_zh` | `str` | 是 | 中文说明 |
| `SentenceAnalysis` | `type` | `Literal["sentence_analysis"]` | 是 | Discriminator |
| `SentenceAnalysis` | `sentence_id` | `str` | 是 | 关联句子 |
| `SentenceAnalysis` | `label` | `str` | 是 | 句型概述 |
| `SentenceAnalysis` | `teach` | `str` | 是 | 教学讲解 |
| `SentenceAnalysis` | `chunks` | `list[Chunk]` | 是 | 结构化拆句，建议 2 到 8 个 |
| `AnnotationOutput` | `annotations` | `list[Annotation]` | 是 | 带鉴别器的 annotation union |
| `AnnotationOutput` | `sentence_translations` | `list[SentenceTranslation]` | 是 | 全量逐句翻译 |

补充说明：

1. `Annotation` 必须定义为：

```python
Annotation = Annotated[
    Union[
        VocabHighlight,
        PhraseGloss,
        ContextGloss,
        GrammarNote,
        SentenceAnalysis,
    ],
    Field(discriminator="type"),
]
```

2. `VocabHighlight` 不输出词典释义。
3. `GrammarNote` 不做 `tags` 枚举约束。
4. `SentenceAnalysis` 的 `chunks` 允许校验失败后降级为普通句级讲解。
5. `AnnotationOutput` 不包含 `schema_version`；版本信息由后端注入 API 响应。
6. 内部 schema 推荐统一 `extra="forbid"` 与 `str_strip_whitespace=True`。

### 18.2 Render Scene 定稿

| 模型 | 字段 | 类型 | 必填 | 来源 | 说明 |
|------|------|------|------|------|------|
| `TextAnchor` | `kind` | `Literal["text"]` | 是 | 投影生成 | 单段锚点 discriminator |
| `TextAnchor` | `sentence_id` | `str` | 是 | annotation | 关联句子 |
| `TextAnchor` | `anchor_text` | `str` | 是 | annotation | 锚点文本 |
| `TextAnchor` | `occurrence` | `int \| None` | 否 | annotation | 重复出现时定位 |
| `MultiTextAnchor` | `kind` | `Literal["multi_text"]` | 是 | 投影生成 | 多段锚点 discriminator |
| `MultiTextAnchor` | `sentence_id` | `str` | 是 | annotation | 关联句子 |
| `MultiTextAnchor` | `parts` | `list[SpanRef]` | 是 | annotation | 多段锚点部分 |
| `InlineMark` | `id` | `str` | 是 | 后端生成 | 稳定标识 |
| `InlineMark` | `annotation_type` | `Literal["vocab_highlight", "phrase_gloss", "context_gloss", "grammar_note"]` | 是 | annotation.type | 语义来源 |
| `InlineMark` | `anchor` | `InlineMarkAnchor` | 是 | annotation | 单段或多段锚点 |
| `InlineMark` | `render_type` | `Literal["background", "underline"]` | 是 | 投影规则 | 渲染形式 |
| `InlineMark` | `visual_tone` | `Literal["vocab", "phrase", "context", "grammar"]` | 是 | 投影规则 | 渲染语义 |
| `InlineMark` | `clickable` | `bool` | 是 | 投影规则 | 是否可点词查询 |
| `InlineMark` | `lookup_text` | `str \| None` | 否 | 投影规则 | 词典查询文本 |
| `InlineMark` | `lookup_kind` | `Literal["word", "phrase"] \| None` | 否 | 投影规则 | 词典查询类型 |
| `InlineMark` | `glossary` | `InlineGlossary \| None` | 否 | annotation | LLM 附加说明 |
| `SentenceEntry` | `id` | `str` | 是 | 后端生成 | 稳定标识 |
| `SentenceEntry` | `sentence_id` | `str` | 是 | annotation | 关联句子 |
| `SentenceEntry` | `entry_type` | `Literal["grammar_note", "sentence_analysis"]` | 是 | annotation.type | 入口类型 |
| `SentenceEntry` | `label` | `str` | 是 | 投影规则 | chip 文案 |
| `SentenceEntry` | `title` | `str \| None` | 否 | 投影规则 | 面板标题 |
| `SentenceEntry` | `content` | `str` | 是 | 投影规则 | 受限 Markdown 内容 |
| `Warning` | `code` | `str` | 是 | 后端生成 | 稳定错误码 |
| `Warning` | `level` | `Literal["info", "warning", "error"]` | 是 | 后端生成 | 前端展示级别 |
| `Warning` | `message` | `str` | 是 | 后端生成 | 可读信息 |
| `Warning` | `sentence_id` | `str \| None` | 否 | 后端生成 | 关联句子 |
| `Warning` | `annotation_id` | `str \| None` | 否 | 后端生成 | 关联标注 |
| `RenderSceneModel` | `schema_version` | `Literal["2.1.0"]` | 是 | 后端生成 | 响应版本 |
| `RenderSceneModel` | `article` | `ArticleStructure` | 是 | preprocess | 正文结构 |
| `RenderSceneModel` | `translations` | `list[SentenceTranslation]` | 是 | output | 全量逐句翻译 |
| `RenderSceneModel` | `inline_marks` | `list[InlineMark]` | 是 | 投影 | 行内标注 |
| `RenderSceneModel` | `sentence_entries` | `list[SentenceEntry]` | 是 | 投影 | 句级入口 |
| `RenderSceneModel` | `warnings` | `list[Warning]` | 是 | 后端生成 | 渲染与校验告警 |

投影规则冻结如下：

1. `VocabHighlight`
   - 生成 1 个 `InlineMark`
   - `render_type = background`
   - `visual_tone = vocab`
   - `clickable = true`
   - `lookup_kind = word`
   - 不生成 `SentenceEntry`

2. `PhraseGloss`
   - 生成 1 个 `InlineMark`
   - `render_type = background`
   - `visual_tone = phrase`
   - `clickable = true`
   - `lookup_kind = phrase`
   - `glossary.zh = ...`
   - 不生成 `SentenceEntry`

3. `ContextGloss`
   - 生成 1 个 `InlineMark`
   - `render_type = underline`
   - `visual_tone = context`
   - `clickable = true`
   - `lookup_kind = word`
   - `glossary.gloss = ...`
   - `glossary.reason = ...`
   - 不生成 `SentenceEntry`

4. `GrammarNote`
   - 生成 1 个 `InlineMark`
   - `anchor` 可以是 `TextAnchor` 或 `MultiTextAnchor`
   - `render_type = underline`
   - `visual_tone = grammar`
   - `clickable = false`
   - 始终生成 1 个 `SentenceEntry`
   - `entry_type = grammar_note`

5. `SentenceAnalysis`
   - 不生成 `InlineMark`
   - 始终生成 1 个 `SentenceEntry`
   - `entry_type = sentence_analysis`
   - `content` 由 `teach + chunks` 格式化而成

6. `cards`
   - `v2.1` 中不存在

***

## 19. 验收标准

### 19.1 后端

1. `ContextGloss` 能稳定产出。
2. `GrammarNote` 可使用多段锚点。
3. `SentenceAnalysis` 含有效 chunks。
4. 中文输出一致。
5. 不再出现当前大量空字段的情况。
6. 词典查询由后端统一代理。

### 19.2 前端

1. mock 页面完整覆盖全部标注组件与解析类型。
2. 结果页视觉质量明显高于当前版本。
3. 三种 page mode 的阅读体验差异清晰。
4. 词典卡片能同时承载 API 释义与 LLM 附加注释。
5. popup、sheet、正文标注三层交互关系清楚。

### 19.3 联调

1. 同一样本双模型双次输出的一致性达到可接受上线标准，不出现明显漂移。
2. 锚点失败率可观测且可接受。
3. 渲染结果无需人工补救即可被前端稳定消费。

***

## 20. 结论

`v2.1` 不是在当前统一容器上继续打补丁，而是一次围绕“组件化 annotation schema”回正的受控重构。其核心不是增加功能，而是减少模型不必要的自由度、恢复语义清晰的数据结构，并同步提升前端 mock 完整度、词典查询链路和结果页产品质感。

从本文件开始，当前 workflow 主线的开发、评审、联调与验收都应以本稿为唯一设计基线。

# V2 统一设计文档

> 本文档是 workflow v2 的唯一事实来源，统一收敛产品目标、前端渲染方案、结构化 schema、前后端协作方式与当前约束。
>
> 更新时间：2026-03-31
> 状态：前端实验完成，后端 V2 可按本文档进入开发

---

## 1. 文档目标

V2 的核心目标不是继续优化 V1 的“词汇/语法/长难句数组填表”，而是把输出协议改造成一套前端可稳定消费的生成式教学 UI 渲染模型：

1. 前端先验证小程序里哪些标注组件与交互真正可行。
2. 再冻结前端可消费的统一渲染 schema。
3. 最后让后端和 LLM 一起适配该 schema。

本文档统一回答三件事：

1. V2 为什么要做。
2. 前端结果页最终需要什么数据。
3. 后端现在该按什么约束开始开发。

---

## 2. 为什么做 V2

V1 已经验证不可用，主要问题有：

1. 业务分类僵化，LLM 被迫往固定数组里填内容，导致解释方式单一。
2. 为了满足 schema，模型容易输出低价值标注，用户获得感弱。
3. 前后端联调顺序倒置，先调 LLM 输出、后看前端能否接住，导致返工成本高。

V2 的转向是：

**让模型从“表单填写者”变成“教学编排者”，但编排的不是任意 UI，而是一组受约束的前端渲染原语。**

---

## 3. V2 总体原则

### 3.1 前端先行，schema 后定

V2 的正确顺序是：

1. 前端先做实验页和 mock 数据。
2. 验证组件形态、交互优先级和小程序可实现性。
3. 冻结前端可消费 schema。
4. 后端再按 schema 开发 V2 接口。
5. 最后做 LLM structured output 和前后端联调。

### 3.2 渲染能力优先于教学分类

前端定义的是渲染能力，不是业务分类组件。  
也就是说，前端先定义“高亮、下划线、句尾入口、段间卡片、词级弹层、底部详情面板”这些能力，至于某个知识点是词汇、语法还是语境说明，由内容语义决定。

### 3.3 翻译层固定

翻译不是自由标注组件，而是页面固定层。  
结果页采用：

1. 英文正文主层
2. 中文翻译副层
3. 标注叠加层

### 3.4 词典点击优先

点击单词查词是系统级基础交互，优先级高于 AI 标注点击。  
词级 AI 补充说明只能复用同一个 `WordPopup` 入口，不能再定义第二套词级点击行为。

### 3.5 后端负责稳定定位，前端负责稳定渲染

LLM 不输出绝对 span 偏移。  
正式联调时，后端负责锚点解析、校验和降级；前端尽量消费已经稳定的定位结果。

---

## 4. 已确认的关键约束

### 4.1 锚点与定位

1. `sentence_id` 仍然是定位硬边界。
2. 单段锚点使用 `sentenceId + anchorText + occurrence`。
3. 多段锚点使用 `multi_text.parts[]`，覆盖 `so ... that`、`not only ... but also` 等不连续结构。
4. 句级入口绑定 `sentenceId`。
5. 段间卡片使用 `afterSentenceId`，支持插在任意句后。
6. 不再要求 LLM 输出绝对 `start-end` 偏移。

### 4.2 视觉冲突与密度

1. 同一区域 `background + underline` 冲突时，`underline` 优先。
2. 所有标注默认独立渲染，不自动合并。
3. 多段锚点和单段锚点允许共存，但不做复杂连线视觉。
4. 重型解释优先放在句尾入口或段间卡片，不压在正文点击上。

### 4.3 页面模式

1. `immersive`：主看英文，低密度标注，翻译默认隐藏。
2. `bilingual`：逐句双语，是当前主阅读模式。
3. `intensive`：显示更多句尾入口与卡片，用于精读。

### 4.4 Content 格式

详情内容和卡片内容使用受限 Markdown 子集，不支持完整 Markdown。

支持：

1. `**text**`
2. `*text*`
3. `` `code` ``
4. `- item`
5. `\n\n`

不支持：

1. `## 标题`
2. 编号列表
3. fenced code block

---

## 5. 前端结果页组件

V2 第一阶段验证并保留的核心组件如下：

1. `SentenceRow`
   - 承载英文句子、中文翻译、词级标注、句尾入口。
2. `InlineMark`
   - 正文内的背景高亮或下划线。
3. `WordPopup`
   - 统一承载词典结果和 AI 补充说明。
4. `SentenceActionChip`
   - 句尾入口，打开句级或语法级详情。
5. `BottomSheetDetail`
   - 承载句级说明、语法说明、语境说明。
6. `AnalysisCard`
   - 插入在任意句后的重型解释卡片。

当前这套 UI/UX 方向已通过前端 beta 验证，可以作为 V2 主方案继续。

---

## 6. V2 统一渲染模型

### 6.1 根类型

```typescript
type RenderSceneModel = {
  article: ArticleModel
  translations: TranslationModel[]
  inlineMarks: InlineMarkModel[]
  sentenceEntries: SentenceTailEntryModel[]
  cards: AnalysisCardModel[]
}
```

### 6.2 锚点模型

```typescript
type TextAnchorModel = {
  kind: 'text'
  sentenceId: string
  anchorText: string
  occurrence?: number
}

type MultiTextAnchorModel = {
  kind: 'multi_text'
  sentenceId: string
  parts: Array<{
    anchorText: string
    occurrence?: number
    role?: string
  }>
}

type SentenceAnchorModel = {
  kind: 'sentence'
  sentenceId: string
}

type BetweenSentenceAnchorModel = {
  kind: 'after_sentence'
  afterSentenceId: string
}
```

### 6.3 InlineMark

```typescript
type InlineMarkTone = 'info' | 'focus' | 'exam' | 'phrase' | 'grammar'
type InlineMarkRenderType = 'background' | 'underline'

type InlineMarkModel = {
  id: string
  renderType: InlineMarkRenderType
  anchor: TextAnchorModel | MultiTextAnchorModel
  tone: InlineMarkTone
  clickable: boolean
  aiNote?: string
  lookupText?: string
  lookupKind?: 'word' | 'phrase'
  aiTitle?: string
  aiBody?: string
}
```

说明：

1. `clickable=true` 时进入 `WordPopup`。
2. `lookupText` 优先于正文表面文本用于查词。
3. `aiTitle` 和 `aiBody` 用于 AI 补充说明展示。

### 6.4 句尾入口

```typescript
type SentenceEntryType = 'grammar' | 'sentence_analysis' | 'context'

type SentenceTailEntryModel = {
  id: string
  label: string
  title?: string
  anchor: SentenceAnchorModel
  type: SentenceEntryType
  content: string
}
```

说明：

1. `label` 用于 chip 短标签。
2. `title` 用于详情面板标题，缺省时回退到 `label`。
3. `content` 为必填。

### 6.5 段间卡片

```typescript
type AnalysisCardModel = {
  id: string
  anchor: BetweenSentenceAnchorModel
  title: string
  content: string
  expanded?: boolean
}
```

### 6.6 文章与翻译

```typescript
type SentenceModel = {
  sentenceId: string
  paragraphId: string
  text: string
}

type ParagraphModel = {
  paragraphId: string
  sentenceIds: string[]
}

type ArticleModel = {
  paragraphs: ParagraphModel[]
  sentences: SentenceModel[]
}

type TranslationModel = {
  sentenceId: string
  translationZh: string
}
```

---

## 7. 受限 Markdown 约束

为避免 contract 漂移，后端输出 `content` 时必须遵守以下规则：

1. 允许用 `**粗体**` 做小标题式强调。
2. 允许用 `- item` 输出无序列表。
3. 允许用 `` `inline code` `` 标注结构片段。
4. 不允许输出 `## 标题`。
5. 不允许输出编号列表。
6. 不允许输出代码块。

推荐风格：

```text
**语法分析**

- 本句包含 so...that 结构
- 后半句说明前半句造成的结果
```

---

## 8. 前后端协作边界

### 8.1 当前阶段必须先打通的闭环

只对接核心链路：

1. 提交文章内容
2. 提交最小阅读配置
3. 返回 `RenderSceneModel`
4. 词级弹层能查词并展示 AI 补充
5. 句级入口和段间卡片能打开并展示内容

### 8.2 当前阶段不优先对接

以下内容不属于 V2 主链路阻塞项，可后置：

1. 用户完整资料
2. 学习记录
3. 收藏/生词本正式落库
4. 历史记录
5. 完整鉴权体系
6. 埋点和消息通知

---

## 9. 后端 V2 开发建议

当前已经可以进入后端 V2 开发，但要遵守以下约束：

1. 先按本文档产出最小可用 `RenderSceneModel`。
2. 严格限制 `content` 输出在受限 Markdown 子集内。
3. 把 schema 视为 V2 alpha 协议，先打通 `POST /api/v2/analyze`。
4. 后端内部增加 schema 校验，避免 LLM 直接输出非法字段或非法格式。
5. 优先保证锚点稳定和渲染可消费，再谈更复杂的教学表达。

推荐接口：

```text
POST /api/v2/analyze
GET  /api/v2/result/{id}
```

---

## 10. 当前状态

| 阶段 | 状态 | 日期 |
|------|------|------|
| V2 方案讨论 | ✅ 完成 | 2026-03-31 |
| 前端组件实验 | ✅ 完成 | 2026-03-31 |
| 前端 mock 验证 | ✅ 完成 | 2026-03-31 |
| 统一 schema 收敛 | ✅ 完成 | 2026-03-31 |
| 后端评估 | ✅ 可进入开发 | 2026-03-31 |
| 后端实现 | ⏳ 待开发 | - |
| 前后端联调 | ⏳ 待进行 | - |

---

## 11. 结论

V2 不再继续优化 V1 的业务数组式输出，而是以一套经过前端实验验证的统一渲染模型为核心，让前端、后端和 LLM 围绕同一份协议协作；从现在开始，后续所有 V2 实现和讨论都应以本文档为唯一依据。

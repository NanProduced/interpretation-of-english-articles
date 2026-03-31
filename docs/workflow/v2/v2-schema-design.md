# V2 Schema 设计文档

> 本文档定义前端可消费的 `RenderSceneModel` 结构，作为前后端联调的接口协议。
>
> 生成时间：2026-03-31
> 更新时间：2026-03-31
> 状态：**前端 Schema 已冻结，待后端评估**

---

## 1. 文档目的

本文档是 V2 前端实验场的 schema 最终输出，基于 `v2-frontend-rendering-component-design.md` 收敛而来。

**目标**：
1. 明确前端可消费的 `RenderSceneModel` 结构
2. 记录与原始设计文档的差异
3. 为后端 V2 接口提供类型参考

---

## 2. 核心类型定义

### 2.1 锚点模型

```typescript
/** 单段文本锚点 */
type TextAnchorModel = {
  kind: 'text'
  sentenceId: string
  anchorText: string
  occurrence?: number  // 第几次出现，默认1
}

/** 多段文本锚点（用于 so...that, not only...but also 等不连续结构） */
type MultiTextAnchorModel = {
  kind: 'multi_text'
  sentenceId: string
  parts: Array<{
    anchorText: string
    occurrence?: number
    role?: string  // 如 'part1', 'part2'
  }>
}

/** 句级锚点 */
type SentenceAnchorModel = {
  kind: 'sentence'
  sentenceId: string
}

/** 段间插入锚点 */
type BetweenSentenceAnchorModel = {
  kind: 'after_sentence'
  afterSentenceId: string
}

type AnchorModel = TextAnchorModel | MultiTextAnchorModel | SentenceAnchorModel | BetweenSentenceAnchorModel
```

### 2.2 标注原语

```typescript
type InlineMarkTone = 'info' | 'focus' | 'exam' | 'phrase' | 'grammar'

type InlineMarkRenderType = 'background' | 'underline'

type InlineMarkModel = {
  id: string
  renderType: InlineMarkRenderType
  anchor: TextAnchorModel | MultiTextAnchorModel
  tone: InlineMarkTone
  /** clickable=true 时点击进入 WordPopup */
  clickable: boolean
  /** AI 补充说明（可选）- 点击 popup 后显示在 AI Tab */
  aiNote?: string
  /** 要查询的文本（可选，默认使用 anchorText） */
  lookupText?: string
  /** 查询类型（可选） */
  lookupKind?: 'word' | 'phrase'
  /** AI 补充标题（可选） */
  aiTitle?: string
  /** AI 补充正文（可选） */
  aiBody?: string
}
```

**Tone 色系定义**：

| tone | 用途 | 颜色 |
|------|------|------|
| `exam` | 考试重点词 | 红色 #ef4444 |
| `phrase` | 短语搭配 | 紫色 #8b5cf6 |
| `grammar` | 语法标记 | 绿色 #22c55e |
| `focus` | 重点关注 | 橙色 #fb923c |
| `info` | 信息提示 | 蓝色 #4285f4 |

### 2.3 句尾入口

```typescript
type SentenceEntryType = 'grammar' | 'sentence_analysis' | 'context'

type SentenceTailEntryModel = {
  id: string
  label: string  // Chip 显示文案：'语法' | '句解' | '语境'
  title?: string  // 详情面板标题（可选，默认使用 label）
  anchor: SentenceAnchorModel
  type: SentenceEntryType
  /** 详情内容，支持 Markdown 格式（必填） */
  content: string
}
```

### 2.4 段间卡片

```typescript
type AnalysisCardModel = {
  id: string
  anchor: BetweenSentenceAnchorModel
  title: string
  /** 内容，支持 Markdown 格式 */
  content: string
  expanded?: boolean  // 展开状态，默认 false
}
```

### 2.5 文章结构

```typescript
type SentenceModel = {
  sentenceId: string
  paragraphId: string
  text: string  // 英文句子
}

type ParagraphModel = {
  paragraphId: string
  sentenceIds: string[]
}

type ArticleModel = {
  paragraphs: ParagraphModel[]
  sentences: SentenceModel[]
}
```

### 2.6 翻译

```typescript
type TranslationModel = {
  sentenceId: string
  translationZh: string
}
```

### 2.7 统一渲染模型（根类型）

```typescript
type RenderSceneModel = {
  article: ArticleModel
  translations: TranslationModel[]
  inlineMarks: InlineMarkModel[]
  sentenceEntries: SentenceTailEntryModel[]
  cards: AnalysisCardModel[]
}
```

---

## 3. 渲染规则

### 3.1 Multi-text 多段锚点渲染

**渲染方式**：分开高亮 - 每个 part 独立高亮，中间文本正常显示

**示例**：
- `so...that` → [so] [that]（两个独立高亮）
- `not only...but also` → [Not only] [but also]（两个独立高亮）

**交互**：每个 part 可独立点击查词

### 3.2 多标注冲突规则

**分开渲染原则**：所有标注独立渲染，不合并。

| 场景 | 规则 |
|------|------|
| 同一位置 background + underline | underline 优先渲染，background 跳过 |
| 相邻标注（间隔 < 3字符） | 分开渲染，不合并 |
| 多段锚点 + 单段锚点重叠 | 分开渲染，各独立显示 |
| 同 tone 多标注重叠 | 分开渲染，各自独立高亮 |

### 3.3 Content Markdown 格式

**支持语法**：

| 语法 | 效果 |
|------|------|
| `**text**` | 粗体 |
| `*text*` | 斜体/强调 |
| `` `code` `` | 行内代码 |
| `- item` | 无序列表 |
| `\n\n` | 段落分隔 |

**不支持**：

| 语法 | 说明 |
|------|------|
| `## 标题` | 不支持语义化标题（前端统一作纯文本处理） |
| ` ``` 代码块 ``` ` | 不支持代码块 |

**实现**：前端使用正则解析，不引入 Markdown 库

### 3.4 卡片插入规则

**规则**：支持在任意句子后插入卡片（`afterSentenceId` 可指向任意 sentenceId）

**示例**：
- 插在段尾（paragraph 最后一个句子）：常见用法
- 插在句中（非段尾）：用于即时语法提示或词汇辨析

---

## 4. 字段差异记录

### 4.1 InlineMarkModel 新增字段

**新增字段**：`lookupText`, `lookupKind`, `aiTitle`, `aiBody`

**用途**：支持更丰富的词级 Popup 数据需求

### 4.2 SentenceTailEntryModel 新增字段

**新增字段**：`content`

**用途**：详情内容直接挂在 entry 上，组件直接渲染，无需内部 mock

### 4.3 后端需确认事项

| 问题 | 选项 A | 选项 B |
|------|--------|--------|
| AI 补充信息来源 | 放在 `InlineMark.aiNote` | 放在独立数据源，WordPopup 单独获取 |
| 推荐 | ✅ | - |

---

## 4. 后端接口要求

### 4.1 接口路径（建议）

```
POST /api/v2/analyze
GET  /api/v2/result/{id}
```

### 4.2 响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "article": {
      "paragraphs": [
        { "paragraphId": "p1", "sentenceIds": ["s1", "s2"] }
      ],
      "sentences": [
        { "sentenceId": "s1", "paragraphId": "p1", "text": "English sentence here." }
      ]
    },
    "translations": [
      { "sentenceId": "s1", "translationZh": "中文翻译。" }
    ],
    "inlineMarks": [
      {
        "id": "m1",
        "renderType": "background",
        "anchor": {
          "kind": "text",
          "sentenceId": "s1",
          "anchorText": "paradigm",
          "occurrence": 1
        },
        "tone": "exam",
        "clickable": true,
        "aiNote": "paradigm 表示'范式'...",
        "lookupText": "paradigm",
        "lookupKind": "word",
        "aiTitle": "词汇补充",
        "aiBody": "paradigm 是学术写作中的高频词汇..."
      }
    ],
    "sentenceEntries": [
      {
        "id": "e1",
        "label": "语法",
        "anchor": { "kind": "sentence", "sentenceId": "s1" },
        "type": "grammar",
        "content": "**语法分析**\n\n- 本句包含以下语法现象\n- 强调句内结构和作用"
      }
    ],
    "cards": [
      {
        "id": "c1",
        "anchor": { "kind": "after_sentence", "afterSentenceId": "s1" },
        "title": "长难句解析",
        "content": "**结构分析**\n\n- `so...that` 表示结果关系\n- 后半句说明前半句带来的结果"
      }
    ]
  }
}
```

### 4.3 必填字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `article` | ✅ | 至少包含空数组 |
| `translations` | ✅ | 至少包含空数组 |
| `inlineMarks` | ✅ | 至少包含空数组 |
| `sentenceEntries` | ✅ | 至少包含空数组 |
| `cards` | ✅ | 至少包含空数组 |

---

## 5. Mock 数据参考

完整 Mock 数据见：`client/src/pages/result-v2/mock-data.ts`

关键场景覆盖：
- 单段锚点 + 多 tone
- 多段锚点（not only...but also, so...that）
- 句尾入口（grammar/句解/语境）
- 段间卡片（长难句解析/词汇辨析）

---

## 6. 状态说明

| 阶段 | 状态 | 日期 |
|------|------|------|
| 前端 schema 定义 | ✅ 完成 | 2026-03-31 |
| 前端 mock 验证 | ✅ 完成 | 2026-03-31 |
| 后端评估 | ⏳ 待评估 | - |
| 后端实现 | ⏳ 待开发 | - |
| 前后端联调 | ⏳ 待进行 | - |

---

## 7. 附录：字段对照表

### 前端 → 后端字段映射

| 前端字段 | 后端需输出 | 类型 | 说明 |
|---------|-----------|------|------|
| `article.paragraphs[].paragraphId` | ✅ | string | 段落 ID |
| `article.paragraphs[].sentenceIds` | ✅ | string[] | 段落内句子 ID 列表 |
| `article.sentences[].sentenceId` | ✅ | string | 句子 ID |
| `article.sentences[].paragraphId` | ✅ | string | 所属段落 ID |
| `article.sentences[].text` | ✅ | string | 英文句子原文 |
| `translations[].sentenceId` | ✅ | string | 关联句子 ID |
| `translations[].translationZh` | ✅ | string | 中文翻译 |
| `inlineMarks[].id` | ✅ | string | 标注唯一 ID |
| `inlineMarks[].renderType` | ✅ | 'background' \| 'underline' | 渲染类型 |
| `inlineMarks[].anchor` | ✅ | AnchorModel | 锚点定位 |
| `inlineMarks[].tone` | ✅ | InlineMarkTone | 标注语气/类型 |
| `inlineMarks[].clickable` | ✅ | boolean | 是否可点击 |
| `inlineMarks[].aiNote` | ⏳ | string? | AI 补充（可选） |
| `inlineMarks[].lookupText` | ⏳ | string? | 查询文本（可选） |
| `inlineMarks[].lookupKind` | ⏳ | 'word' \| 'phrase'? | 查询类型（可选） |
| `inlineMarks[].aiTitle` | ⏳ | string? | AI 补充标题（可选） |
| `inlineMarks[].aiBody` | ⏳ | string? | AI 补充正文（可选） |
| `sentenceEntries[].id` | ✅ | string | 入口唯一 ID |
| `sentenceEntries[].label` | ✅ | string | Chip 显示文案 |
| `sentenceEntries[].title` | ⏳ | string? | 详情面板标题（可选，默认用 label） |
| `sentenceEntries[].anchor` | ✅ | SentenceAnchorModel | 锚点 |
| `sentenceEntries[].type` | ✅ | SentenceEntryType | 入口类型 |
| `sentenceEntries[].content` | ✅ | string | 详情内容，支持 Markdown（必填） |
| `cards[].id` | ✅ | string | 卡片唯一 ID |
| `cards[].anchor` | ✅ | BetweenSentenceAnchorModel | 锚点 |
| `cards[].title` | ✅ | string | 卡片标题 |
| `cards[].content` | ✅ | string | 卡片内容，支持 Markdown |
| `cards[].expanded` | ⏳ | boolean? | 展开状态（可选） |

---

## 8. 状态说明

| 阶段 | 状态 | 日期 |
|------|------|------|
| 前端 schema 定义 | ✅ 完成 | 2026-03-31 |
| 前端 mock 验证 | ✅ 完成 | 2026-03-31 |
| **前端实现验证** | ✅ 完成 | 2026-03-31 |
| 后端评估 | ⏳ 待评估 | - |
| 后端实现 | ⏳ 待开发 | - |
| 前后端联调 | ⏳ 待进行 | - |

# 输出 Schema 草案

版本：`v0.1.0-draft`

状态：草案。该文档用于指导最小 Workflow、Pydantic 模型和前端渲染契约的设计，后续会根据真实调试结果迭代。

## 文档目标

定义第一版结构化输出的最小正式契约，满足以下要求：

- 能稳定被前端解析
- 能支持默认高亮、点击词汇、句子展开、翻译展示等核心交互
- 能体现用户配置对优先级和解释风格的影响
- 不把词典型确定性数据塞进 Workflow

## 设计原则

### 1. 正式能力不受本地调试模型限制

本地 `Qwen3-8B` 可以用于低成本测试，但正式 Schema 按项目目标和主力模型能力设计。

### 2. 词汇标注是“重点标注”，不是全文词典化

Workflow 输出只保留：

- 哪些词/短语值得标
- 语境义是什么
- 为什么值得关注
- 对当前用户的优先级是什么

词典数据由前端实时调用词典服务获得。

### 3. 语法是正式主维度

语法标注必须进入正式契约，至少覆盖：

- 长难句
- 句子结构
- 语法知识点
- 错误语法风险标记

### 4. 文本结构层与标注层分离

正文结构先被拆成 `paragraphs` 和 `sentences`，标注层再通过 `sentence_id` 和 `span` 引用正文。

### 5. 前端渲染优先

所有字段设计优先考虑：

- 高亮
- 弹卡
- 折叠展开
- 句子定位
- 分层显示

## 顶层结构

```json
{
  "schema_version": "0.1.0",
  "request": {},
  "status": {},
  "article": {},
  "annotations": {},
  "translations": {},
  "discourse": null,
  "warnings": [],
  "metrics": {}
}
```

## 顶层字段说明

### `schema_version`

用于前后端兼容控制。第一版固定为 `0.1.0`。

### `request`

保存本次 Workflow 的输入侧关键快照。

建议字段：

```json
{
  "request_id": "uuid",
  "profile_key": "exam_cet4",
  "profile_snapshot": {
    "usage_purpose": "exam",
    "usage_variant": "cet4"
  },
  "discourse_enabled": false
}
```

### `status`

用于前端统一判断成功、失败、降级。

建议字段：

```json
{
  "state": "success",
  "degraded": false,
  "error_code": null,
  "user_message": null
}
```

### `article`

承载正文结构，是所有标注定位的锚点。

建议字段：

```json
{
  "title": null,
  "language": "en",
  "source_type": "user_input",
  "source_text": "原始输入文本",
  "render_text": "规范化后的渲染文本",
  "paragraphs": [],
  "sentences": []
}
```

约定：

- `source_text` 保留原始文本
- `render_text` 是前端渲染和所有 span 对齐的唯一基准文本
- `paragraphs` 和 `sentences` 是前端渲染正文的基础结构

### `annotations`

承载核心解读标注，当前分三类：

- `vocabulary`
- `grammar`
- `difficult_sentences`

### `translations`

承载翻译相关输出：

- 逐句翻译
- 全文翻译
- 关键短语翻译

### `discourse`

当前允许为 `null`，后续在篇章分析启用时填充：

- 段落大意
- 文章结构
- 逻辑连接词
- 主题句

### `warnings`

用于表达：

- 文本质量问题
- 分析结果风险提示
- 降级原因

### `metrics`

便于前端展示和后端可观测性统计。

## `article` 结构草案

### `paragraphs`

```json
[
  {
    "paragraph_id": "p1",
    "text": "Paragraph text...",
    "start": 0,
    "end": 120,
    "sentence_ids": ["s1", "s2"]
  }
]
```

### `sentences`

```json
[
  {
    "sentence_id": "s1",
    "paragraph_id": "p1",
    "text": "Sentence text...",
    "start": 0,
    "end": 56,
    "difficulty_score": 0.72,
    "is_difficult": true
  }
]
```

## `annotations.vocabulary` 草案

注意：这里只包含“重点词 / 重点短语”，不是给全文每个词做词典化解析。

```json
[
  {
    "annotation_id": "v1",
    "type": "vocabulary",
    "surface": "robust",
    "lemma": "robust",
    "span": { "start": 12, "end": 18 },
    "sentence_id": "s1",
    "phrase_type": "word",
    "context_gloss_zh": "稳健的；有很强适应性的",
    "short_explanation_zh": "这里强调系统在复杂环境下仍然可靠。",
    "objective_level": "intermediate",
    "priority": "core",
    "default_visible": true,
    "exam_tags": ["cet4"],
    "scene_tags": ["academic_reading"]
  }
]
```

### 字段原则

- `context_gloss_zh` 是 Workflow 真正需要负责的语境义
- `short_explanation_zh` 用于快速卡片说明
- 不包含音标、完整词典义、例句
- `objective_level` 是客观难度
- `priority` 是根据用户 profile 映射得到的展示优先级

## `annotations.grammar` 草案

语法是核心维度，当前建议支持三类正式结构。

### 1. 语法知识点

```json
{
  "annotation_id": "g1",
  "type": "grammar_point",
  "sentence_id": "s1",
  "span": { "start": 0, "end": 56 },
  "label": "定语从句",
  "short_explanation_zh": "which 引导定语从句，修饰前面的名词。",
  "objective_level": "intermediate",
  "priority": "core",
  "default_visible": false
}
```

### 2. 句子成分结构

```json
{
  "annotation_id": "g2",
  "type": "sentence_component",
  "sentence_id": "s1",
  "components": [
    {
      "label": "subject",
      "text": "The system",
      "span": { "start": 0, "end": 10 }
    },
    {
      "label": "predicate",
      "text": "provides",
      "span": { "start": 11, "end": 19 }
    },
    {
      "label": "object",
      "text": "a stable output",
      "span": { "start": 20, "end": 35 }
    }
  ],
  "objective_level": "basic",
  "priority": "core",
  "default_visible": false
}
```

### 3. 语法风险标记

```json
{
  "annotation_id": "g3",
  "type": "error_flag",
  "sentence_id": "s2",
  "span": { "start": 80, "end": 96 },
  "label": "possible_grammar_issue",
  "short_explanation_zh": "原文这里可能存在语法问题，以下分析按原文理解给出。",
  "objective_level": "basic",
  "priority": "core",
  "default_visible": true
}
```

## `annotations.difficult_sentences` 草案

这部分是长难句拆解的核心承载块。

```json
[
  {
    "annotation_id": "d1",
    "sentence_id": "s1",
    "span": { "start": 0, "end": 56 },
    "trigger_reason": ["long_sentence", "embedded_clause"],
    "main_clause": "The system provides a stable output.",
    "chunks": [
      {
        "order": 1,
        "label": "主干",
        "text": "The system provides a stable output."
      },
      {
        "order": 2,
        "label": "修饰部分",
        "text": "which can still be parsed by the frontend"
      }
    ],
    "reading_path_zh": "先抓主干，再看 which 引导的补充说明。",
    "objective_level": "intermediate",
    "priority": "core",
    "default_visible": true
  }
]
```

## `translations` 草案

```json
{
  "sentence_translations": [
    {
      "sentence_id": "s1",
      "translation_zh": "该系统会输出一份稳定的结果。",
      "style": "natural"
    }
  ],
  "full_translation_zh": "全文通顺翻译……",
  "key_phrase_translations": [
    {
      "phrase": "be driven by",
      "sentence_id": "s3",
      "span": { "start": 131, "end": 143 },
      "translation_zh": "由……驱动"
    }
  ]
}
```

## `discourse` 草案

当前允许为 `null`。

后续启用时建议逐步支持：

- `paragraph_summaries`
- `article_structure`
- `discourse_markers`
- `topic_sentences`

## `warnings` 草案

```json
[
  {
    "code": "LOW_TEXT_QUALITY",
    "message_zh": "文本存在少量疑似错误，语法分析结果请结合原文判断。"
  }
]
```

## `metrics` 草案

```json
{
  "vocabulary_count": 8,
  "grammar_count": 12,
  "difficult_sentence_count": 3,
  "sentence_count": 14,
  "paragraph_count": 4
}
```

## 枚举建议

### `priority`

- `core`
- `expand`
- `reference`

### `objective_level`

- `basic`
- `intermediate`
- `advanced`

### `status.state`

- `success`
- `partial_success`
- `failed`

## 前端渲染约束

以下约束建议直接作为实现规范：

1. 所有高亮对象必须有 `sentence_id` 和 `span`
2. 所有 span 都基于 `article.render_text`
3. 不允许前端从自然语言解释中反推标注归属
4. 所有标注项必须有稳定的 `annotation_id`
5. `priority` 和 `default_visible` 由前端控制默认展示层级

## 当前不纳入 v0 的字段

以下字段当前明确不进入正式 Workflow 契约：

- 音标
- 词典词性
- 词典基础释义
- 近义词 / 反义词
- 例句
- 词根词缀
- 全量 POS
- 复杂句法树
- 修辞手法

这些能力后续如果需要，应作为：

- 词典服务能力
- 增强块
- 非 v0 强契约字段

## 当前结论

`schema v0` 的正式重点是：

- 重点词汇标注
- 语法标注
- 长难句拆解
- 翻译
- 前端可稳定解析的文本结构与 UI 提示字段

这版草案不是最终定稿，后续会根据真实 Workflow 调试结果继续收敛。


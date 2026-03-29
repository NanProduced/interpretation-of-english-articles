# 输出 Schema 草案

版本：`v0.1.0`

状态：当前已与代码中的 [server/app/schemas/analysis.py](/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/schemas/analysis.py) 和 [server/app/workflow/analyze.py](/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/workflow/analyze.py) 对齐。本文档描述的是 **当前 V0 原型已经实现的结构契约**，不是更远期目标。

## 文档目标

定义 `/analyze` 接口当前返回的最小正式结构，确保：

- 前端可以稳定解析
- LangGraph 各节点的输入输出边界清晰
- 后续调试 prompt 和 agent 时不会因为字段漂移影响联调

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

## 输入请求结构

当前代码中的请求模型是 `AnalyzeRequest`：

```json
{
  "text": "英文文章原文",
  "profile_key": "exam_cet4",
  "source_type": "user_input",
  "request_id": null,
  "discourse_enabled": false
}
```

说明：

- `request_id` 可由调用方传入，不传时由后端在 preprocess 阶段生成。
- `discourse_enabled` 已进入请求结构，但当前 `discourse` 输出固定为 `null`。

## 顶层字段说明

### `schema_version`

固定为 `0.1.0`。

### `request`

保存本次分析请求的关键快照：

```json
{
  "request_id": "uuid",
  "profile_key": "exam_cet4",
  "source_type": "user_input",
  "discourse_enabled": false
}
```

### `status`

用于表达整体执行状态：

```json
{
  "state": "success",
  "degraded": false,
  "error_code": null,
  "user_message": null
}
```

当前 `state` 枚举：

- `success`
- `partial_success`
- `failed`

### `article`

正文结构层，是所有标注定位的锚点：

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

- `render_text` 是前端渲染和所有 span 对齐的唯一基准文本。
- `paragraphs` 中包含 `sentence_ids`。
- `sentences` 当前已经包含 `difficulty_score` 和 `is_difficult`。

### `annotations`

当前分三类：

- `vocabulary`
- `grammar`
- `difficult_sentences`

### `translations`

当前包含：

- `sentence_translations`
- `full_translation_zh`
- `key_phrase_translations`

其中 `SentenceTranslation.style` 枚举为：

- `natural`
- `exam`
- `literal`

### `discourse`

当前固定为 `null`。`discourse_agent` 仍未进入 V0 实现。

### `warnings`

用于表达模型回退、校验不一致和风险提示。当前实现里可能出现的 code 包括：

- `TEXT_TYPE_CHECK`
- `CORE_AGENT_FALLBACK`
- `TRANSLATION_AGENT_FALLBACK`
- `TRANSLATION_COVERAGE_MISMATCH`
- `INVALID_SENTENCE_REFERENCE`

### `metrics`

当前包含：

```json
{
  "vocabulary_count": 8,
  "grammar_count": 12,
  "difficult_sentence_count": 3,
  "sentence_count": 14,
  "paragraph_count": 4
}
```

## `article` 结构

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

## `annotations.vocabulary`

这里只包含重点词/短语，不是全文词典化输出。

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
    "short_explanation_zh": "在这里强调系统在复杂环境下仍然可靠。",
    "objective_level": "intermediate",
    "priority": "core",
    "default_visible": true,
    "exam_tags": ["cet4"],
    "scene_tags": ["academic_reading"]
  }
]
```

当前约束：

- `phrase_type` 只允许 `word` 或 `phrase`。
- `objective_level` 只允许 `basic`、`intermediate`、`advanced`。
- `priority` 只允许 `core`、`expand`、`reference`。
- `exam_tags` 与 `scene_tags` 默认为空数组。

## `annotations.grammar`

当前代码中的单条语法标注结构统一如下：

```json
{
  "annotation_id": "g1",
  "type": "grammar_point",
  "sentence_id": "s1",
  "span": { "start": 0, "end": 56 },
  "label": "定语从句",
  "short_explanation_zh": "which 引导定语从句，修饰前面的名词。",
  "components": [],
  "objective_level": "intermediate",
  "priority": "core",
  "default_visible": false
}
```

说明：

- `type` 允许 `grammar_point`、`sentence_component`、`error_flag`。
- `components` 字段始终存在；只有 `sentence_component` 类型会实际填充内容。
- `SentenceComponent.label` 当前允许：
  - `subject`
  - `predicate`
  - `object`
  - `complement`
  - `modifier`
  - `adverbial`
  - `clause`

示例：

```json
{
  "annotation_id": "g2",
  "type": "sentence_component",
  "sentence_id": "s1",
  "span": null,
  "label": "句子主干",
  "short_explanation_zh": "先看主语和谓语。",
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
    }
  ],
  "objective_level": "basic",
  "priority": "expand",
  "default_visible": false
}
```

## `annotations.difficult_sentences`

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
      }
    ],
    "reading_path_zh": "先抓主干，再看修饰成分。",
    "objective_level": "intermediate",
    "priority": "core",
    "default_visible": true
  }
]
```

## `translations`

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

说明：

- `full_translation_zh` 当前是必填字段。
- `sentence_translations` 应覆盖 `article.sentences` 中全部句子；否则会被 `validate` 节点打 warning 并降为 `partial_success`。

## 前端解析约束

1. 所有需要高亮的对象必须带 `sentence_id` 和 `span`。
2. 所有 span 都以 `article.render_text` 为基准。
3. 前端不应依赖自然语言说明去反推标注归属。
4. 所有标注项必须有稳定的 `annotation_id`。

## 当前不纳入 V0 的字段

以下能力当前不进入正式 Workflow 契约：

- 音标
- 词典词性
- 词典基础释义
- 近义词、反义词
- 例句
- 词根词缀
- 全量 POS
- 复杂句法树
- 修辞手法

## 当前结论

当前代码里的 `schema v0` 已经稳定覆盖：

- 重点词汇标注
- 语法标注
- 长难句拆解
- 逐句与全文翻译
- 前端可稳定消费的正文结构、状态与统计字段

后续迭代重点应该放在输出质量和节点策略，而不是继续扩张字段面。

# 输入规范与预处理 Schema 草案

版本：`v0.1.0`

状态：当前已与代码中的 [server/app/schemas/preprocess.py](/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/schemas/preprocess.py) 和 [server/app/workflow/preprocess.py](/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/workflow/preprocess.py) 对齐。本文档描述的是 **当前 preprocess_v0 已实现的结构与规则**。

## 文档目的

定义 Workflow 第一阶段的稳定输出契约，确保后续：

- `router` 能依据质量与分流字段工作
- `article` 结构能复用预处理阶段的切分结果
- 样本联调时能明确区分“输入问题”和“核心标注问题”

## 这个 Schema 负责什么

把原始文章文本转换为结构化预处理结果，回答这些问题：

- 是否是适合解读的英文正文
- 文本是否已经完成基础规范化
- 是否存在噪音、截断、混合语言等风险
- 是否适合完整分析，还是应该降级或拒绝

## 这个 Schema 不负责什么

- 不输出词汇、语法、翻译等正式分析结果
- 不负责词典类知识
- 不负责前端结果页展示结构
- 不负责多轮对话修正

## 当前实现原则

### 1. 只做轻量规范化，不改写原文语义

当前代码里真正实现的规范化动作只有：

- `normalize_line_breaks`
- `collapse_spaces`

说明：

- HTML 当前会被检测，但不会被自动剥离。
- Unicode 规范化当前还未实现。
- 不会自动纠错、改写句子或调整语序。

### 2. 先判断能否继续，再进入核心标注

预处理阶段的首要任务是提供稳定分流信号，而不是尽可能多地做语言分析。

### 3. fallback 结果也必须结构完整

即使 guardrails 模型不可用，仍要通过本地规则返回完整 `PreprocessResult`，保证链路可联调、可追踪。

## 输入请求结构

当前请求模型是 `PreprocessAnalyzeRequest`：

```json
{
  "text": "英文文章原文",
  "profile_key": "exam_cet4",
  "source_type": "user_input",
  "request_id": null
}
```

## 顶层结构

```json
{
  "schema_version": "0.1.0",
  "request": {},
  "normalized": {},
  "segmentation": {},
  "detection": {},
  "issues": [],
  "quality": {},
  "routing": {},
  "warnings": []
}
```

## 字段说明

### `request`

```json
{
  "request_id": "uuid",
  "profile_key": "exam_cet4",
  "source_type": "user_input"
}
```

### `normalized`

```json
{
  "source_text": "原始输入文本",
  "clean_text": "规范化后的文本",
  "text_changed": true,
  "normalization_actions": [
    "normalize_line_breaks",
    "collapse_spaces"
  ]
}
```

### `segmentation`

```json
{
  "paragraph_count": 3,
  "sentence_count": 12,
  "paragraphs": [
    {
      "paragraph_id": "p1",
      "text": "Paragraph text...",
      "start": 0,
      "end": 120
    }
  ],
  "sentences": [
    {
      "sentence_id": "s1",
      "paragraph_id": "p1",
      "text": "Sentence text...",
      "start": 0,
      "end": 56
    }
  ]
}
```

### `detection`

```json
{
  "language": {
    "primary_language": "en",
    "english_ratio": 0.93,
    "non_english_ratio": 0.07
  },
  "text_type": {
    "predicted_type": "article",
    "confidence": 0.88
  },
  "noise": {
    "noise_ratio": 0.04,
    "has_html": true,
    "has_code_like_content": false,
    "appears_truncated": false
  }
}
```

当前 `predicted_type` 枚举：

- `article`
- `list`
- `subtitle`
- `code`
- `email`
- `other`

### `issues`

`issues` 是把 guardrails 判断出的风险转成最终可返回的问题列表。

```json
[
  {
    "issue_id": "pi1",
    "type": "noise_content",
    "severity": "medium",
    "sentence_id": null,
    "span": null,
    "description_zh": "文本中包含较多噪音内容，可能影响句子切分与后续标注。",
    "suggestion_zh": "建议去除 HTML、代码片段或无关噪音后再分析。"
  }
]
```

当前 `type` 枚举：

- `possible_grammar_issue`
- `possible_spelling_issue`
- `non_english_content`
- `noise_content`
- `truncated_text`
- `unsupported_text_type`

当前 `severity` 枚举：

- `low`
- `medium`
- `high`

### `quality`

```json
{
  "score": 0.81,
  "grade": "good",
  "suitable_for_full_annotation": true,
  "summary_zh": "文本整体质量较好，可进入完整解读流程。"
}
```

当前 `grade` 枚举：

- `good`
- `acceptable`
- `poor`

### `routing`

```json
{
  "decision": "full",
  "should_continue": true,
  "degrade_reason": null,
  "reject_reason": null
}
```

当前 `decision` 枚举：

- `full`
- `degraded`
- `reject`

语义：

- `full`：允许进入完整分析流程
- `degraded`：允许继续，但应标记为降级
- `reject`：不进入后续完整分析

### `warnings`

当前实现里可能出现的 warning code 包括：

- `GUARDRAILS_FALLBACK`
- `GUARDRAILS_LLM_ERROR`

## 当前代码中的关键模型

当前 Pydantic 结构包括：

- `PreprocessAnalyzeRequest`
- `PreprocessRequestMeta`
- `NormalizedText`
- `SegmentedParagraph`
- `SegmentedSentence`
- `SegmentationResult`
- `LanguageDetection`
- `TextTypeDetection`
- `NoiseDetection`
- `DetectionResult`
- `GuardrailsIssue`
- `GuardrailsAssessment`
- `PreprocessIssue`
- `QualityAssessment`
- `RoutingDecision`
- `PreprocessWarning`
- `PreprocessResult`

## 当前规则与未来目标的边界

下面这些仍属于未来目标，当前代码尚未实现：

- 自动去 HTML 标签
- Unicode 规范化
- 更细的语言识别
- 更稳定的句子边界修正
- 基于 LLM 的更强输入修复策略

因此，本文档中的 V0 语义应理解为：**先保证输入层结构稳定、可分流、可追踪**，而不是已经完成了完整的输入清洗系统。

# Workflow V1 设计方案

## 1. 文档目标

本文档定义 Workflow V1 的业务骨架、`user_config` 体系、输出契约和失败策略。

目标：

- 让 workflow 回到“老师在板书”的教学模式，而不是“数据库在填表”
- 缩短总耗时，降低 token 消耗和结构化失败概率
- 保证前端有稳定、可渲染、可分层展示的标注数据
- 为后续引入 few-shot、轻量检索和行为反馈增强预留扩展位

非目标：

- 当前版本不引入付费增强节点
- 当前版本不实现 discourse-level annotation
- 当前版本不接入 RAG / 行为反馈闭环
- 当前版本不保留任何会污染结果页的伪 fallback 标注

## 2. 设计原则

### 2.1 教学优先

模型优先回答“哪里值得讲、为什么值得讲、应该怎么讲”，而不是优先满足复杂表结构。

### 2.2 本地做确定性工作

以下能力优先由本地逻辑完成：

- 输入清洗
- 分段分句
- 安全风险判断
- `user_config -> user_rules`
- `anchor_text -> render_span`
- 去重和低价值过滤
- 渲染索引与展示提示生成

### 2.3 差异化是“软偏好 + 强提示”

- `reading_goal` 是软偏好，控制讲解风格和默认展示层
- `reading_variant` 是强提示，控制更值得关注的点
- 差异化不应导致关键难点漏标

### 2.4 失败显式化

教学节点失败时直接返回失败状态，不输出“待优化翻译”“简化说明”之类的伪内容。

## 2.5 实现规范

V1 在代码实现上需要同步收敛工程规范，避免重蹈 V0 “逻辑能跑但边界不清”的问题。

### 代码注释

- V1 不追求“每行都注释”，但核心逻辑和关键边界必须有简洁注释
- 必须加注释的区域：
  - 输入清洗规则
  - `user_config -> user_rules` 映射
  - `anchor_text -> render_span` 解析逻辑
  - 低价值过滤与丢弃规则
  - 状态降级与失败判定
- 注释目标是解释“为什么这样做”，不是重复代码字面意思

### Prompt 规范

- V1 的 prompt 统一使用中文
- 同一工作流内不混用中英提示词，避免风格和约束不一致
- prompt 结构固定建议：
  - 角色说明
  - 任务目标
  - 输入说明
  - 输出要求
  - 约束规则
  - 反例或 few-shot（如需要）
- 提示词优先强调教学目标、锚点返回规则和禁止事项

### Schema 说明

- 所有核心 Pydantic schema 都应补充 `Field(description="...")`
- 重点字段必须写 description：
  - `reading_goal`
  - `reading_variant`
  - `render_text`
  - `sentence_span`
  - `anchor_text`
  - `anchor_occurrence`
  - `display_mode`
  - `render_index`
- 对枚举字段建议在 description 中直接写清语义，而不是仅依赖字段名
- 如有必要，可补充 `json_schema_extra` 示例，帮助模型和前后端同时理解结构

说明：

- Pydantic/PydanticAI 兼容 `Field(description=...)`
- 这既有利于 schema 可读性，也有利于结构化输出模型更稳定理解字段意图

## 3. User Config 与规则包

## 3.1 前端输入配置

V1 仅保留核心阅读偏好配置：

```json
{
  "reading_goal": "daily_reading",
  "reading_variant": "beginner_reading"
}
```

当前枚举建议：

- `reading_goal`
  - `exam`
  - `daily_reading`
  - `academic`
- `reading_variant`
  - `gaokao`
  - `cet4`
  - `cet6`
  - `kaoyan`
  - `ielts`
  - `toefl`
  - `beginner_reading`
  - `intermediate_reading`
  - `intensive_reading`
  - `academic_general`

说明：

- `academic` 表示阅读目标和讲解倾向，不等于开启 discourse 增强能力
- 付费增强功能后续以额外节点或额外输出层接入，不进入 V1 主链路

## 3.2 后端规则包

Workflow 不直接消费 `reading_goal`，而是消费结构化规则包：

```json
{
  "profile_id": "daily_beginner",
  "teaching_style": "plain_and_supportive",
  "translation_style": "natural",
  "grammar_granularity": "balanced",
  "vocabulary_policy": "high_value_only",
  "annotation_budget": {
    "vocabulary": 6,
    "grammar": 5,
    "sentence_note": 2
  },
  "presentation_policy": {
    "advanced_default_collapsed": true
  }
}
```

规则包职责：

- 控制提示词注入
- 控制 few-shot 选择
- 控制输出优先级和默认展示层
- 为后续检索增强与数据反馈预留挂点

## 3.3 差异化尺度

差异化不作用于“是否发现关键问题”，而作用于：

- 解释风格
- 默认展示方式
- 轻重缓急排序
- 是否把高难项归入“进阶内容”

例如：

- `beginner_reading` 输入高难文章时，仍需标出真正关键的语法点和难句
- 但这些高难项可以：
  - `display_group = "advanced"`
  - `is_default_visible = false`
  - 使用更轻的 `display_mode`

## 4. Workflow Graph

V1 主 workflow 建议压缩为 4 个节点：

1. `prepare_input`
2. `derive_user_rules`
3. `generate_annotations`
4. `assemble_result`

### 4.1 `prepare_input`

职责：

- 读取 `source_text`
- 生成安全可渲染的 `render_text`
- 分段分句
- 判断是否存在明显渲染风险或严重噪音
- 输出 `preprocess_result`

本节点只做低复杂度、高收益的本地处理：

- HTML 标签移除
- URL / email 安全替换或剔除
- markdown / code fence 剔除
- 异常空白与控制字符清理
- 英文比例、噪音比例、文本类型粗判

输出包含：

- `source_text`
- `render_text`
- `paragraphs`
- `sentences`
- `sanitize_report`
- `preprocess_status`

如果输入明显不适合进入教学链路，本节点直接标记失败。

### 4.2 `derive_user_rules`

职责：

- 读取 `user_config`
- 结合文本基础特征生成 `user_rules`
- 把软偏好和强提示转换成 prompt 规则与展示规则

输出包含：

- `profile_id`
- `teaching_style`
- `translation_style`
- `grammar_granularity`
- `vocabulary_policy`
- `annotation_budget`
- `presentation_policy`

### 4.3 `generate_annotations`

职责：

- 作为唯一主教学 LLM 节点
- 读取 `sentences`、`user_rules` 和 few-shot 示例
- 生成教学型结构化结果

输入不再包含整段 `render_text`，只提供：

- `sentences[]`
- 每句的 `sentence_id`
- 每句的 `sentence_text`
- 每句的 `sentence_span`
- `user_rules`

模型只返回句级锚点，不返回全文绝对坐标。

### 4.4 `assemble_result`

职责：

- `anchor_text -> render_span`
- 去重、过滤低价值项
- 生成 `annotation_id`
- 生成 `render_index`
- 生成 `render_marks`
- 汇总状态与最终输出

本节点负责把“教学结果”变成“前端可渲染契约”。

## 5. Annotation 设计

V1 建议保留三类主标注：

- `vocabulary_annotations`
- `grammar_annotations`
- `sentence_annotations`

其中：

- `vocabulary_annotations`
  用于高价值词/短语，不承载完整词典释义
- `grammar_annotations`
  用于重点语法点，不再输出复杂 `SentenceComponent` 绝对位置树
- `sentence_annotations`
  用于难句或句级讲解

### 5.1 模型草稿输出

模型阶段只输出教学语义和锚点：

```json
{
  "sentence_id": "s3",
  "anchor_text": "wishing to purchase",
  "annotation_type": "grammar",
  "title": "现在分词作定语",
  "content": "这里修饰 Customers，表示“想购买的人”。",
  "pedagogy_level": "support"
}
```

### 5.2 最终输出

后端组装后的最终标注应包含：

- `annotation_id`
- `annotation_type`
- `sentence_id`
- `anchor_text`
- `render_span`
- `title`
- `content`
- `pedagogy_level`
- `display_priority`
- `display_group`
- `is_default_visible`
- `render_index`

## 6. Render Contract

前端渲染不应直接消费教学内容本身，而应消费稳定的渲染标记：

```json
{
  "mark_id": "m12",
  "annotation_id": "a12",
  "display_mode": "highlight",
  "render_index": 12,
  "display_priority": "primary",
  "display_group": "core"
}
```

推荐 `display_mode`：

- `underline`
- `highlight`
- `inline_note`
- `footnote_card`
- `bottom_detail`

这样同一条标注可以根据 `user_rules` 映射成不同展示方式，而不需要模型自己决定前端布局。

## 7. Span 与 Anchor 策略

V1 不再要求模型产出全文字符坐标。

统一策略：

1. 模型返回：
   - `sentence_id`
   - `anchor_text`
   - 可选 `anchor_occurrence`
2. 后端仅在该句内部做锚点解析
3. 成功后再转换为相对于 `render_text` 的 `render_span`

优点：

- 显著减少 token
- 降低跨句幻觉和错位
- 保证前端高亮定位稳定

如有重复匹配，按以下顺序处理：

1. exact match
2. normalized match
3. `anchor_occurrence`
4. 失败则丢弃该标注并记录 warning

## 8. 翻译策略

V1 主路径先保留：

- `sentence_translations`

不把 `full_translation_zh` 作为主节点的硬要求。

建议：

- 先以逐句翻译为主
- 组装阶段默认可按句拼接全文翻译
- 如果后测发现连贯性不足，再引入可选的轻量 `translation_polish` 增量步骤

## 9. 失败与降级策略

V1 取消会污染结果页的伪 fallback 数据。

规则：

- `prepare_input` 失败：直接返回输入不可处理
- `generate_annotations` 失败：直接返回服务繁忙或生成失败
- `assemble_result` 发现局部锚点无法解析：
  - 丢弃单条坏标注
  - 只要整体仍然可信，可继续返回
- 如果剩余标注已明显不足以支撑结果页，则整体失败

## 10. V1 预留扩展位

V1 不实现以下能力，但结构上预留：

- `few_shot_examples`
- `retrieval_hints`
- 用户行为反馈信号
- discourse 增强节点
- 阅读理解题生成节点

预留方式：

- `user_rules` 可挂载 few-shot 选择信息
- prompt builder 可接收额外检索片段
- `analysis_result` 可追加高级输出层，不破坏主标注契约

## 11. LangSmith 约定调整

V1 需要保留 LangSmith 可观测性，但要同步清理 V0 的 trace 语义噪音。

调整方向：

- workflow root metadata 与 node metadata 使用统一命名
- 不再沿用 V0 风格的节点名和 tags
- 根 trace 重点记录：
  - `workflow_name`
  - `workflow_version`
  - `profile_id`
  - `reading_goal`
  - `reading_variant`
  - `model_profile`
  - `request_source`
- 主教学节点记录：
  - token usage
  - latency
  - prompt template id
  - few-shot 来源
  - 标注数量
- 组装节点记录：
  - 锚点解析成功率
  - 丢弃标注数量
  - 最终输出数量

LangSmith 目标：

- 既能保留链路调试能力
- 又能直接支持后续的质量评估、样本回放和配置对比

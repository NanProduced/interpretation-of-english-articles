# Workflow 摘要

来源文档：`AI 解读 Workflow 流程设计（草图）`

说明：本文档只记录当前 V0 原型已经实现、并会直接约束开发的部分，避免把草图中的未来设想写成当前能力。

## 当前对外入口

当前人工联调与后续前端调用都统一走：

- `POST /analyze`

说明：

- `preprocess_v0` 仍然存在，但只作为 `analyze_v0` 内部子 workflow
- 它不再单独暴露为 API 路由
- 原因是当前 V0 不做 HITL，中间 guardrails 判断不会单独暂停流程，因此单独调 `/preprocess` 容易误导优化方向

## 当前已实现的 workflow

### 1. preprocess_v0

`preprocess_v0` 是 `analyze_v0` 内部复用的 5 节点子图：

1. `normalize`
2. `segment`
3. `detect`
4. `guardrails`
5. `finalize`

职责：

- 规范化输入文本
- 切分段落与句子
- 检测语言比例、噪音、文本类型与疑似截断
- 通过 guardrails 生成质量评估与路由建议
- 输出 `PreprocessResult`

### 2. analyze_v0

`analyze_v0` 是当前完整主 workflow：

1. `preprocess`
2. `router`
3. `core`
4. `translation`
5. `merge`
6. `enrich`
7. `validate`
8. `finalize_success / finalize_rejected`

职责：

- 复用 `preprocess_v0`
- 按输入质量决定继续或拒绝
- 调用核心标注 agent 与翻译 agent
- 合并输出
- 根据 profile 做优先级富化
- 做最小输出校验

## 当前 V0 输出能力

`/analyze` 当前能稳定返回：

- `article`
- `annotations.vocabulary`
- `annotations.grammar`
- `annotations.difficult_sentences`
- `translations`
- `warnings`
- `metrics`

其中：

- `core_agent` 负责词汇、语法、长难句
- `translation_agent` 负责逐句翻译、全文翻译、关键短语翻译
- `discourse` 仍未实现

## 当前核心设计原则

### 1. 只有一个对外主入口

人工联调和产品调用都应该看最终的 `/analyze` 输出，而不是只看 preprocess 子结果。

### 2. preprocess 仍然独立存在，但只作为内部子图

这符合 LangGraph 的常见实践：

- 把可复用的前置流程保留为子 workflow
- 但不一定对外暴露独立 API

### 3. Schema 优先于 Prompt

前后端的第一约束是结构化输出，不是 prompt 表现。

### 4. 降级优先于中断

当前 V0 已允许：

- preprocess fallback
- core agent fallback
- translation agent fallback

目标是先保证整条链路能返回结构化结果，再持续优化质量。

## 当前与草图的差异

以下内容在草图中已提出，但当前 V0 还未实现：

- `discourse_agent`
- 更复杂的条件路由
- 更强的重试策略
- 更完整的 enrichment 链路
- 更细的输出校验体系

## 当前最值得关注的工程点

### 1. 最终结构是否适合前端渲染

重点看 `/analyze` 输出，不要只看 preprocess。

### 2. span 对齐是否稳定

所有标注都依赖 `article.render_text`，这是前端高亮和点击交互的基础。

### 3. fallback 是否污染主结果

V0 允许 fallback，但 fallback 只是保结构，不代表最终产品质量。

## 当前实施建议

后续迭代顺序建议是：

1. 以 `/analyze` 为唯一人工联调入口
2. 用样本持续调试 `core_agent_v0`
3. 用样本持续调试 `translation_agent_v0`
4. 收敛 warning、fallback 和 validate 规则
5. 再决定是否引入 `discourse_agent`

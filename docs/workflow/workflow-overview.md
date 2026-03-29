# Workflow 摘要

来源文档：`AI 解读 Workflow 流程设计（草图）`

注意：源文档仍未定稿。本文档只保留当前 V0 原型已经落地或已经明确作为下一步目标的部分，避免把“未来设想”误写成“当前实现”。

## 文档定位

本文档描述后端 AI 解读 Workflow 的当前业务骨架，用于约束代码实现、联调和后续迭代。

当前原则：

- 先做最小完成体
- 先验证结构稳定性和可调试性
- 再逐步提升内容质量

## Workflow 的职责

Workflow 负责把：

- 英文文章文本
- 用户配置
- 请求元信息

转成可解析、可渲染、可存储、可追踪的结构化 JSON。

它当前不负责：

- 前端渲染
- 账号体系
- 词典服务
- 篇章分析产出

## 当前实现状态

### 已实现：preprocess_v0

当前 [server/app/workflow/preprocess.py](/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/workflow/preprocess.py) 已实现 5 个节点的线性子图：

1. `normalize`
2. `segment`
3. `detect`
4. `guardrails`
5. `finalize`

职责：

- 规范化输入文本
- 切分段落与句子
- 检测语言比例、文本类型、噪音与截断风险
- 通过 guardrails 做质量评估与分流判断
- 组装 `PreprocessResult`

### 已实现：analyze_v0

当前 [server/app/workflow/analyze.py](/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/workflow/analyze.py) 已实现主图：

1. `preprocess`
2. `router`
3. `core`
4. `translation`
5. `merge`
6. `enrich`
7. `validate`

另外包含两个收口节点：

- `finalize_success`
- `finalize_rejected`

职责：

- 复用 preprocess 子图
- 按输入质量决定继续或拒绝
- 调用核心标注 agent 与翻译 agent
- 合并结果
- 按 profile 做优先级富化
- 做最小结构校验

## 当前 V0 输出能力

当前 `/analyze` 已能稳定返回：

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
- `discourse` 仍固定为 `null`

## 当前核心设计原则

### 1. Schema 优先

前后端的第一约束是 Schema，不是 prompt。

### 2. AI 只做语境相关任务

由 AI 负责：

- 语境义判断
- 语法结构分析
- 长难句拆解
- 翻译生成

尽量不由 AI 负责：

- 音标
- 基础词典释义
- 词表命中
- 规则映射

### 3. 可降级优先于“全成功”

当前代码已经允许：

- preprocess fallback
- core agent fallback
- translation agent fallback

目标是先保证链路完整可回包，再继续优化质量。

### 4. profile 影响展示优先级，不改变基础结构

当前 `enrich` 节点会根据 `profile_key` 调整：

- `priority`
- `default_visible`

但不会改变基础字段结构。

## 当前与草图文档的差异

以下内容在草图里已经提出，但当前 V0 还没有实现：

- `discourse_agent`
- 更复杂的条件路由
- 更强的重试策略
- 更完整的富化链路
- 更细的输出校验体系

以下内容在草图里写得更理想化，但当前 V0 实现更克制：

- 预处理目前只做轻量规范化，没有真正剥离 HTML，也没有做 Unicode 规范化
- validate 节点当前只做最小一致性校验，不做更复杂的语义级校验

## 当前最值得关注的工程点

### 1. span 对齐

所有标注都依赖 `article.render_text`，这是当前前端渲染能否稳定的关键。

### 2. 输出结构稳定性

当前 V0 已经有正式结构，但字段稳定性仍需要通过样本持续验证。

### 3. 降级质量

fallback 已打通，但 fallback 内容只是保底结构，不代表最终产品质量。

## 当前实施建议

后续继续推进时，建议按这个顺序：

1. 用样本持续调试 `core_agent_v0`
2. 用样本持续调试 `translation_agent_v0`
3. 收敛 warning、fallback 和 validate 规则
4. 再决定是否引入 `discourse_agent` 或更复杂的路由

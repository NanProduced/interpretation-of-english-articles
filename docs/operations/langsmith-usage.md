# LangSmith 使用规范

版本：`v0.1.0-draft`

状态：草案。当前用于指导本项目的 tracing、样本沉淀和评估流程，后续会结合实际工作流继续收敛。

## 文档目的

LangSmith 在本项目中承担三类职责：

- Trace：记录请求、节点执行、Prompt 和模型输出
- 样本收集：把高价值 trace 沉淀为测试样本
- Evaluation：基于样本持续比较不同 Workflow / Prompt / 模型版本

## 为什么现在就接入

本项目的核心风险不在“能不能跑通”，而在：

- 输出是否稳定
- Prompt 是否在不同 profile 下表现一致
- 哪些字段容易漂移
- 哪些输入会触发失败或降级

如果没有 trace 和样本积累，后续调优会高度依赖感觉，难以持续比较版本差异。

## 官方参考

- LangSmith 总览：[LangSmith docs](https://docs.langchain.com/langsmith)
- 环境变量配置：[Trace without setting environment variables](https://docs.langchain.com/langsmith/trace-without-env-vars)
- LangGraph tracing：[Trace LangGraph applications](https://docs.langchain.com/langsmith/trace-with-langgraph)
- PydanticAI tracing：[Trace PydanticAI applications](https://docs.langchain.com/langsmith/trace-with-pydantic-ai)
- Evaluation：[LangSmith Evaluation](https://docs.langchain.com/langsmith/evaluation)
- 分布式 tracing：[Implement distributed tracing](https://docs.langchain.com/langsmith/distributed-tracing)

## 项目配置约定

### 环境变量

在 `server/.env` 中配置：

```env
LANGSMITH_ENABLED=true
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=english-article-interpretation-dev
LANGSMITH_API_KEY=your_api_key
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_WORKSPACE_ID=
```

说明：

- `LANGSMITH_ENABLED=false` 时，本地运行不启用 LangSmith
- `LANGSMITH_PROJECT` 用于区分环境和阶段
- 如果 API key 绑定了多个 workspace，可补充 `LANGSMITH_WORKSPACE_ID`

### 代码初始化

后端启动时统一初始化 LangSmith：

- 配置 OTEL integration
- 启用 PydanticAI `Agent.instrument_all()`
- 让后续 Agent 调用自动进入 LangSmith

当前初始化位置：

- `server/app/observability/langsmith.py`

## Project 命名规范

建议至少区分这些 project：

- `english-article-interpretation-dev`
- `english-article-interpretation-eval`
- `english-article-interpretation-prod`

不要把开发调试、离线评估和线上流量混在一个 project 里。

## Trace 命名规范

建议在代码中统一使用稳定的 run / trace 命名：

- `preprocess_v0`
- `core_agent_v0`
- `translation_agent_v0`
- `workflow_v0`

后续版本升级时显式带版本号，避免在 LangSmith 中无法比较：

- `core_agent_v1`
- `core_agent_v2`

## Metadata 规范

每次 trace 至少补充这些 metadata：

- `profile_key`
- `schema_version`
- `workflow_version`
- `prompt_version`
- `model_provider`
- `model_name`
- `degraded`

如果后面接入前后端联调，再增加：

- `request_id`
- `user_id_hash`
- `source_type`

注意：

- 不要直接上传用户敏感信息
- 不要把完整密钥、原始身份信息写入 metadata

## Tags 规范

建议统一使用少量固定 tags，避免失控：

- `dev`
- `eval`
- `prod`
- `preprocess`
- `core-agent`
- `translation-agent`
- `degraded`
- `error-case`

## 样本收集规范

LangSmith 里的样本不要靠人工零散记录，建议从 trace 中系统沉淀。

### 第一阶段收集三类样本

1. 正常样本

- 结构清晰
- 输出较稳定
- 适合作为基准集

2. 边界样本

- 长文
- 噪音文本
- 有语法错误的文本
- 学术句式密集文本

3. 失败样本

- 解析失败
- 结构错误
- 输出缺字段
- 错误分流

### 最小样本集建议

初期先沉淀 20 到 30 条高质量样本，不追求大。

## Evaluation 规范

### 先做离线评估

当前阶段优先使用 LangSmith 的离线评估能力，基于固定样本集比较：

- 不同 Prompt 版本
- 不同 Agent 版本
- 不同模型
- 不同 Router 策略

### 初期重点评估维度

- 结构合法性
- 词汇标注是否合理
- 语法标注是否清晰
- 长难句拆解是否有助于理解
- 翻译是否通顺
- profile 差异是否符合预期

### 不建议一开始就做的事

- 复杂线上自动评估
- 过多 LLM-as-judge 规则
- 大量人工 rubric 体系

先把样本集和最小评估流程跑通。

## 开发阶段使用规范

### 什么时候必须开 tracing

- 调试 preprocess
- 调试新 Prompt 版本
- 调试新 Agent 版本
- 对比不同模型输出
- 处理失败或降级案例

### 什么时候可以关闭 tracing

- 与 LangSmith 无关的纯接口调试
- 不涉及 LLM 调用的本地快速测试
- CI 中的纯单元测试

## 当前结论

LangSmith 在本项目中不是“以后再说”的增强项，而是 Workflow 调试基础设施。

当前最合理的做法是：

1. 先完成基础 tracing 配置
2. 在 preprocess 和后续 Agent 中统一打版本号
3. 从第一批调试开始沉淀样本
4. 再逐步建立离线评估流程


# LangSmith 使用规范

版本：`v0.3.0-draft`

状态：开发中。本文档只记录当前仓库已经验证过、并且与代码保持一致的 tracing 接法。

## 当前目标

当前项目的 LangSmith tracing 目标是：

- 每次完整 workflow 请求只产生 1 条顶层 trace
- 顶层 trace 直接带上最小但稳定的 metadata
- 模型调用作为顶层 trace 的 llm 子 span
- token 记录在 llm 子 span 上，并汇总到顶层 trace
- `preprocess` / `core` / `translation` 三段真实模型调用都应出现 llm 子 span

## 当前对外联调入口

当前人工联调统一走：

- `POST /analyze`

说明：

- `preprocess_v0` 仍然存在，但只作为内部子 workflow
- `preprocess_v0` 不再单独暴露 API
- LangSmith 人工分析也应优先看 `analyze_v0`，不要只看 preprocess 子结果

## 官方依据

- [Trace LangGraph applications](https://docs.langchain.com/langsmith/trace-with-langgraph)
- [Trace PydanticAI applications](https://docs.langchain.com/langsmith/trace-with-pydantic-ai)
- [Custom instrumentation](https://docs.langchain.com/langsmith/annotate-code)
- [Cost tracking](https://docs.langchain.com/langsmith/cost-tracking)
- [Metadata parameters reference](https://docs.langchain.com/langsmith/ls-metadata-parameters)

当前采用的结论：

- 顶层 trace 统一由 LangGraph workflow 创建
- PydanticAI 不启用全局 instrumentation
- 节点内部真实 llm 调用使用 `@traceable(run_type="llm")`
- 当前已接入的 llm 子 span 名称：
  - `guardrails_llm_call`
  - `core_llm_call`
  - `translation_llm_call`

## 当前接法

### 1. 顶层 root trace 由 LangGraph 创建

在 `graph.ainvoke(...)` 时通过 `config` 传入：

- `run_name`
- `tags`
- `metadata`

### 2. 顶层 metadata 只保留最小过滤集

当前统一保留：

- `workflow_version`
- `schema_version`
- `request_id`
- `profile_key`
- `source_type`
- `trace_scope`

可选保留：

- `sample_bucket`
- 与当前 workflow 强相关但确实常用于过滤的字段

不再默认堆很多调试字段到顶层 root 上。

### 3. llm 子 span 手工回填 usage

当前在节点内部：

- 用 `@traceable(run_type="llm")` 包装模型调用
- 从 PydanticAI `result.usage()` 中提取 token
- 通过 `usage_metadata` 回填给 LangSmith
- 通过 `ls_provider` / `ls_model_name` 标记模型信息

## 当前 workflow 过滤建议

### analyze 主流程

建议优先按以下字段过滤：

- `workflow_version = analyze_v0`
- `trace_scope = analyze_local_debug`

### preprocess 子流程

如果需要排查 `analyze_v0` 里的 preprocess 子图，可在 trace 详情里看对应节点，不再通过单独 API trace 排查。

## 不再使用的接法

以下接法当前明确废弃：

- 在 FastAPI 路由层手工再起一个 root trace
- 启用 PydanticAI `Agent.instrument_all()`
- 同时保留 `LangGraph` 顶层 trace 和独立 `agent run` 顶层 trace

## 当前结论

当前 tracing 规范是：

1. `/analyze` 是唯一人工联调入口
2. 顶层 trace 统一由 LangGraph 创建
3. 顶层 metadata 只保留最小过滤集
4. Agent 不启用全局 instrumentation
5. 节点内真实模型调用用 `@traceable(run_type="llm")` 包裹
6. token 用 `usage_metadata` 回填

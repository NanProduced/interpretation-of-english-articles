# LangSmith 使用规范

版本：`v2.0.0`

状态：当前有效。本文档记录 V3 workflow 的 tracing 规范。

## V3 目标

V3 项目的 LangSmith tracing 目标是：

- 每次完整 workflow 请求只产生 1 条顶层 trace
- 顶层 trace 直接带上最小但稳定的 metadata
- 本地节点与模型节点都以统一 node 命名进入同一条 trace
- 三个并行 agent 的 LLM 调用分别作为独立的 llm 子 span
- token 记录在 llm 子 span 上，并汇总到顶层 trace
- drop_log 记录在 normalize_and_ground 节点的 outputs 中

## V3 对外联调入口

V3 人工联调统一走：

- `POST /analyze`

说明：

- V3 采用多 agent 并行架构（vocabulary_agent + grammar_agent + translation_agent）
- 归一化层（normalize_and_ground）记录 drop_log
- 可选的 repair_agent 在 failure_ratio > 0.20 时触发
- LangSmith 人工分析应优先看 `article_analysis`

## 官方依据

- [Trace LangGraph applications](https://docs.langchain.com/langsmith/trace-with-langgraph)
- [Trace PydanticAI applications](https://docs.langchain.com/langsmith/trace-with-pydantic-ai)
- [Custom instrumentation](https://docs.langchain.com/langsmith/annotate-code)
- [Cost tracking](https://docs.langchain.com/langsmith/cost-tracking)
- [Metadata parameters reference](https://docs.langchain.com/langsmith/ls-metadata-parameters)

V3 采用的结论：

- 顶层 trace 统一由 LangGraph workflow 创建
- PydanticAI 不启用全局 instrumentation
- 节点内部真实 llm 调用使用 `@traceable(run_type="llm")`
- V3 LLM 子 span 名称：
  - `vocabulary_llm_call`
  - `grammar_llm_call`
  - `translation_llm_call`
  - `repair_llm_call`

## V3 接法

### 1. 顶层 root trace 由 LangGraph 创建

在 `graph.ainvoke(...)` 时通过 `config` 传入：

- `run_name`
- `tags`
- `metadata`

### 2. 顶层 metadata 只保留最小过滤集

V3 统一保留：

- `workflow_name`
- `workflow_version`（V3 = "3.0.0"）
- `schema_version`（V3 = "3.0.0"）
- `request_id`
- `profile_id`
- `source_type`
- `reading_goal`
- `reading_variant`
- `trace_scope`

可选保留：

- `sample_bucket`
- 与当前 workflow 强相关但确实常用于过滤的字段

不再默认堆很多调试字段到顶层 root 上。

### 3. llm 子 span 手工回填 usage

V3 在节点内部：

- 用 `@traceable(run_type="llm")` 包装模型调用
- 从 PydanticAI `result.usage()` 中提取 token
- 通过 `usage_metadata` 回填给 LangSmith
- 通过 `ls_provider` / `ls_model_name` 标记模型信息

## V3 workflow 过滤建议

### article_analysis 主流程

建议优先按以下字段过滤：

- `workflow_name = article_analysis`
- `workflow_version = 3.0.0`
- `trace_scope = analyze_local_debug`

### V3 关键节点

建议重点关注以下节点：

- `prepare_input`
- `derive_user_config`
- `vocabulary_agent`
- `grammar_agent`
- `translation_agent`
- `normalize_and_ground`
- `repair_agent`（条件触发）
- `project_render_scene`
- `assemble_result`

### V3 drop_log 分析

normalize_and_ground 节点的 outputs 中包含：

- `normalized_result`：归一化后的标注
- `drop_log`：所有被删除/降级的标注记录

drop_log 字段说明：

- `source_agent`：来源 agent（vocabulary/grammar/translation）
- `annotation_type`：被删除的标注类型
- `sentence_id`：句子ID
- `anchor_text`：锚定文本
- `drop_reason`：删除原因（duplicate/low_value/anchor_invalid/conflict 等）
- `drop_stage`：删除阶段（grounding/deduplication/conflict_resolution/density_control/pruning）

### V3 repair_agent 触发条件

当 `failure_ratio > 0.20` 时触发 repair：

```
failure_ratio = drop_count / (annotation_count + drop_count)
```

repair_agent 无法添加新标注，仅修复以下问题：

- sentence_id 错误
- anchor_text 不匹配
- 缺失字段
- 枚举值错误
- 结构格式问题

## 不再使用的接法

以下接法 V3 明确废弃：

- 在 FastAPI 路由层手工再起一个 root trace
- 启用 PydanticAI `Agent.instrument_all()`
- 同时保留 `LangGraph` 顶层 trace 和独立 `agent run` 顶层 trace
- V1/V2 的 `annotation_generation_llm_call` span 名称

## V3 结论

V3 tracing 规范是：

1. `/analyze` 是唯一人工联调入口
2. 顶层 trace 统一由 LangGraph 创建
3. 顶层 metadata 只保留最小过滤集
4. Agent 不启用全局 instrumentation
5. 三个并行 agent 分别用独立 llm span（vocabulary_llm_call/grammar_llm_call/translation_llm_call）
6. token 用 `usage_metadata` 回填
7. drop_log 记录在 normalize_and_ground 节点的 outputs 中

## 环境变量

V3 代码会同时设置以下 tracing 开关：

- `LANGSMITH_TRACING=true|false`
- `LANGSMITH_TRACING_V2=true|false`

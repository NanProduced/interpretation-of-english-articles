# 后端架构约定

## 目录职责

- `app/config/settings.py`
  只负责读取原始环境变量，不承载 profile/preset 解析逻辑。
- `app/database/`
  数据库连接管理（connection.py, session.py）。
- `app/observability/`
  可观测性（langsmith.py）。
- `app/enrichment/`
  预留扩展（当前为空）。
- `app/llm/registry.py`
  负责把部署配置解析成模型注册表。
- `app/llm/router.py`
  负责按 `request override -> preset -> route default -> deployment default` 解析模型。
- `app/llm/provider_factory.py`
  负责把 provider 配置构造成具体 SDK model。
- `app/llm/agent_runner.py`
  Agent 运行器。
- `app/llm/runtime.py`
  运行时配置。
- `app/llm/routes.py`
  模型路由定义。
- `app/llm/types.py`
  类型定义。
- `app/agents/`
  只定义 agent blueprint、deps、prompt，不做模型选择和运行封装。
- `app/services/analysis/`
  负责输入清洗、用户规则映射、锚点解析、结果组装和 agent 执行封装。
  - `planning/` — GoalExecutionPlan 构建
  - `postprocess/` — 归一化、锚点解析、投影、校验
  - `preprocess/` — 输入预处理
  - `prompting/` — Prompt 策略、组合、加载、示例、RAG
  - `runtime/` — Agent 运行器
- `app/services/quota/`
  负责配额查询、额度校验、积分扣减与发放。
- `app/services/auth/`
  负责微信登录、会话管理、用户资料更新（session.py, profile.py）。
- `app/services/feedback/`
  负责反馈提交、查询、状态更新与奖励发放。
- `app/services/user_assets/`
  负责用户资产（records, vocabulary, favorites）的 CRUD 操作。
- `app/services/daily_reader/`
  负责每日精读的 Pipeline 编排、文章 CRUD 与内容安全检测。
- `app/services/dictionary/`
  负责词典查询、lemma 归并、短语候选与缓存。
- `app/workflow/`
  只负责编排、节点状态流转、trace metadata。
  - `analyze.py` — 入口分流（根据 topology_mode 选择 graph）
  - `learning_workflow.py` — Learning 工作流（7 节点）
  - `academic_workflow.py` — Academic 工作流（7 节点）
  - `daily_reader_workflow.py` — 每日精读工作流（8 节点）
  - `analyze_nodes.py` — Learning 节点实现
  - `analyze_state.py` — Learning 状态定义
  - `academic_state.py` — Academic 状态定义
  - `tracing.py` — LangSmith tracing
- `app/schemas/common.py`
  放共享值对象，例如 `TextSpan`。
- `app/schemas/internal/`
  放 agent 与 node 之间的内部 DTO。
  - `academic_drafts.py` — Academic agent 输出
  - `academic_normalized.py` — Academic 归一化结果
  - `daily_drafts.py` — Daily Reader agent 输出
  - `execution_plan.py` — GoalExecutionPlan
  - `analysis.py` — 分析任务内部 schema
  - `drafts.py` — Learning agent 输出
  - `normalized.py` — Learning 归一化结果
- `app/schemas/analysis.py`
  放分析任务 API schema。
- `app/schemas/quota.py`
  放配额与积分明细 schema。
- `app/schemas/auth.py`
  放认证相关 schema。
- `app/schemas/feedback.py`
  放反馈相关 schema。
- `app/schemas/health.py`
  放健康检查 schema。
- `app/schemas/daily_reader.py`
  放每日精读 schema。
- `app/schemas/tasks.py`
  放任务相关 schema。
- `app/schemas/user_assets/`
  放用户资产 schema 子目录（records.py, vocabulary.py, favorites.py）。

## 设计规则

- 不允许在 `agents/` 中直接读取 `Settings` 或解析 model profile。
- 不允许在 `workflow/` 中实现文本归一化、切句、fallback 业务规则。
- 不允许为某个 vendor 在 `Settings` 中添加专属字段，例如 `MINIMAX_*`。
- 新增 provider 时，先扩 `app/llm/provider_factory.py`，再在 `MODEL_PROFILES_JSON` 中注册 profile。
- 新增模型时，只追加 profile，不复制 route/agent 逻辑。
- 运行时实验统一通过请求里的 `model_selection` 或服务端 `MODEL_PRESETS_JSON`，不通过改 legacy env。
- 对外 schema 和内部 schema 必须分层，内部 agent DTO 不直接暴露给 API。
- Pydantic 模型必须放在 `app/schemas/` 对应文件中，不允许在路由文件中定义 BaseModel 子类。
- 所有 API 端点必须声明 `response_model`，不允许省略或使用 `response_model=dict`。
- HTTP 异常的 `detail` 字段禁止暴露内部异常信息（如 `detail=str(e)`），统一使用 `detail="Internal server error"`。原始异常仅通过日志记录。
- API Key 比较必须使用 `secrets.compare_digest()` 进行常量时间比较，禁止使用 `!=` 或 `==` 直接比较（防止时序攻击）。
- 内容安全检测必须采用 fail-closed 策略：API 调用失败、返回异常或字段缺失时，默认拒绝放行（`suggest=review`），不允许 fail-open 默认放行。
- `MODEL_PROFILES_JSON` 支持两种方式：外部 JSON 文件（推荐）或内联 JSON。

## 新增模型流程

1. 在 `MODEL_PROFILES_JSON`（推荐使用 `config/model-profiles.json`）增加一个 profile。
2. 如需服务端命名实验方案，在 `MODEL_PRESETS_JSON` 增加 preset。
3. 如需部署默认切换，修改 `DEFAULT_MODEL_PROFILE` 或节点级 `*_MODEL_PROFILE`。
4. 如需支持新 provider，在 `app/llm/provider_factory.py` 增加 builder，并补测试。

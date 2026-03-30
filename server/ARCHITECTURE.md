# 后端架构约定

## 目录职责

- `app/config/settings.py`
  只负责读取原始环境变量，不承载 profile/preset 解析逻辑。
- `app/llm/registry.py`
  负责把部署配置解析成模型注册表。
- `app/llm/router.py`
  负责按 `request override -> preset -> route default -> deployment default` 解析模型。
- `app/llm/provider_factory.py`
  负责把 provider 配置构造成具体 SDK model。
- `app/agents/`
  只定义 agent blueprint、deps、prompt，不做模型选择和运行封装。
- `app/services/analysis` / `app/services/preprocess`
  负责纯业务逻辑和 agent 执行封装。
- `app/workflow/`
  只负责编排、节点状态流转、trace metadata。
- `app/schemas/common.py`
  放共享值对象，例如 `TextSpan`。
- `app/schemas/internal/`
  放 agent 与 node 之间的内部 DTO。
- `app/schemas/analysis.py` / `app/schemas/preprocess.py`
  放对外 API schema。

## 设计规则

- 不允许在 `agents/` 中直接读取 `Settings` 或解析 model profile。
- 不允许在 `workflow/` 中实现文本归一化、切句、fallback 业务规则。
- 不允许为某个 vendor 在 `Settings` 中添加专属字段，例如 `MINIMAX_*`。
- 新增 provider 时，先扩 `app/llm/provider_factory.py`，再在 `MODEL_PROFILES_JSON` 中注册 profile。
- 新增模型时，只追加 profile，不复制 route/agent 逻辑。
- 运行时实验统一通过请求里的 `model_selection` 或服务端 `MODEL_PRESETS_JSON`，不通过改 legacy env。
- 对外 schema 和内部 schema 必须分层，内部 agent DTO 不直接暴露给 API。

## 新增模型流程

1. 在 `MODEL_PROFILES_JSON` 增加一个 profile。
2. 如需服务端命名实验方案，在 `MODEL_PRESETS_JSON` 增加 preset。
3. 如需部署默认切换，修改 `DEFAULT_MODEL_PROFILE` 或节点级 `*_MODEL_PROFILE`。
4. 如需支持新 provider，在 `app/llm/provider_factory.py` 增加 builder，并补测试。

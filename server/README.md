# 后端说明

这里是 AI 解读 workflow 的后端服务目录，使用 `FastAPI + LangGraph + PydanticAI`。

## 技术栈

- Python 3.11+
- FastAPI
- LangGraph
- PydanticAI
- Pydantic v2
- HTTPX
- Uvicorn

## 环境约定

- 后端使用独立虚拟环境，不与系统 Python 或前端依赖混用
- 虚拟环境固定在 `server/.venv/`
- 依赖管理使用 `uv`
- 依赖声明文件是 `server/pyproject.toml`
- 锁文件是 `server/uv.lock`

常用命令：

```bash
cd server
uv sync
uv run uvicorn app.main:app --reload
```

## 模型配置

当前支持三层模型配置方式：

- 兼容旧配置：`ANALYSIS_*` / `GUARDRAILS_*`
- 部署默认路由：`DEFAULT_MODEL_PROFILE` + 节点级 `*_MODEL_PROFILE`
- 运行时覆盖：请求里的 `model_selection`

当前节点映射：

- `PREPROCESS_MODEL_PROFILE` -> `preprocess_guardrails`
- `CORE_MODEL_PROFILE` -> `core_agent_v0`
- `TRANSLATION_MODEL_PROFILE` -> `translation_agent_v0`

内置了一个便捷 profile：`minimax_m27`。

部署默认切换示例：

```bash
CORE_MODEL_PROFILE=minimax_m27
TRANSLATION_MODEL_PROFILE=minimax_m27
MINIMAX_M27_API_KEY=your-key
```

服务端命名 preset 示例：

```bash
MODEL_PRESETS_JSON='{"minimax_eval":{"routes":{"analysis_core":{"profile":"minimax_m27"},"analysis_translation":{"profile":"minimax_m27"}}}}'
```

请求级 runtime override 示例：

```json
{
  "text": "Your article here",
  "profile_key": "exam_cet4",
  "model_selection": {
    "preset": "minimax_eval",
    "routes": {
      "analysis_translation": {
        "profile": "minimax_m27",
        "model_settings": {
          "temperature": 0.2,
          "max_tokens": 4000
        }
      }
    }
  }
}
```

推荐做法：

- env 只负责 secrets、可用 profile 和部署默认值
- `MODEL_PRESETS_JSON` 负责服务端命名实验方案
- `model_selection` 负责单次请求的实验、灰度和 case 复盘

## 当前对外接口

- `POST /analyze`

说明：

- `preprocess_v0` 仍然作为内部子 workflow 保留
- 但它不再单独暴露 API，避免人工调试只盯着 preprocess 结果而忽略整条链路

## 当前 workflow

`analyze_v0` 主流程：

- `preprocess`
- `router`
- `core`
- `translation`
- `merge`
- `enrich`
- `validate`

其中：

- `preprocess_v0` 是内部子图，负责输入规范化、切分、检测和 guardrails 判断
- `core_agent_v0` 负责词汇、语法、长难句
- `translation_agent_v0` 负责逐句翻译、全文翻译和关键短语翻译

## LangSmith 约定

- 顶层 trace 统一由 LangGraph workflow 创建
- PydanticAI 不启用全局 instrumentation
- 节点内部真实模型调用使用 `@traceable(run_type="llm")` 创建子 span
- token 通过 `usage_metadata` 回填

相关规范见：

- `../docs/operations/langsmith-usage.md`

## 当前职责

- workflow 编排
- 模型调用
- 结构化 JSON 输出
- 输出校验与降级控制
- 后续数据持久化与增强能力扩展

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

当前只保留一套生产化模型配置路径：

- `MODEL_PROFILES_JSON`
  声明所有可用 profile。profile 是 provider + model + provider-specific 配置的组合。
- `DEFAULT_MODEL_PROFILE` 与节点级 `*_MODEL_PROFILE`
  声明部署默认路由。
- `MODEL_PRESETS_JSON`
  声明服务端可复用的命名实验方案。
- 请求里的 `model_selection`
  声明单次请求的 runtime override。

当前节点映射：

- `PREPROCESS_MODEL_PROFILE` -> `preprocess_guardrails`
- `CORE_MODEL_PROFILE` -> `analysis_core`
- `TRANSLATION_MODEL_PROFILE` -> `analysis_translation`

profile 示例：

```bash
MODEL_PROFILES_JSON='{
  "local_qwen": {
    "provider": "openai_compatible",
    "model_name": "Qwen/Qwen3-8B",
    "base_url": "http://127.0.0.1:8000/v1",
    "api_key": ""
  },
  "minimax_m27": {
    "provider": "openai_compatible",
    "model_name": "MiniMax-M2.7",
    "base_url": "https://api.minimax.io/v1",
    "api_key": "your-minimax-key"
  }
}'
```

部署默认切换示例：

```bash
DEFAULT_MODEL_PROFILE=local_qwen
CORE_MODEL_PROFILE=minimax_m27
TRANSLATION_MODEL_PROFILE=minimax_m27
```

服务端 preset 示例：

```bash
MODEL_PRESETS_JSON='{
  "minimax_eval": {
    "routes": {
      "analysis_core": {"profile": "minimax_m27"},
      "analysis_translation": {"profile": "minimax_m27"}
    }
  }
}'
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

- env 只负责注册 profile 和部署默认值
- preset 只负责实验方案
- request 只负责单次 case 的运行时切换
- 不再使用 legacy `ANALYSIS_*` / `GUARDRAILS_*` 配置

## 目录约定

- `app/config`
  只放原始配置读取
- `app/llm`
  负责 profile registry、route resolution、provider factory、agent runtime injection
- `app/agents`
  只放 agent blueprint
- `app/services`
  放纯业务逻辑和 agent runner
- `app/workflow`
  只做 LangGraph 编排与 tracing
- `app/schemas/common.py`
  放共享值对象
- `app/schemas/internal`
  放内部 DTO
- `app/schemas/analysis.py` / `app/schemas/preprocess.py`
  放对外 API schema

详细规范见 `ARCHITECTURE.md`。

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

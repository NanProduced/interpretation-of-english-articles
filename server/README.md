# 后端说明

这里是 Claread透读 的 AI 解读 workflow 后端服务目录，使用 `FastAPI + LangGraph + PydanticAI`。

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

详细说明见 [模型配置教程](../docs/operations/model-configuration-usage.md)。

核心概念：

- `MODEL_PROFILES_JSON` - 声明所有可用 profile
- `DEFAULT_MODEL_PROFILE` / `*_MODEL_PROFILE` - 声明部署默认路由
- `MODEL_PRESETS_JSON` - 声明服务端可复用的命名实验方案
- 请求里的 `model_selection` - 声明单次请求的 runtime override

节点映射：

- `ANNOTATION_MODEL_PROFILE` -> `annotation_generation`

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
- `app/schemas/analysis.py`
  放对外 API schema

详细规范见 `ARCHITECTURE.md`。

## 命名规范

后端 workflow、schema 与前端渲染契约必须使用统一命名，避免文档、代码和 API 漂移。

### 通用规则

- 版本号不进入业务命名。
  版本只出现在文档名、trace metadata、变更记录中；不要出现在 node 名、schema 类名、JSON 字段名里。
- Python 函数、LangGraph node 名、JSON 字段名统一使用 `snake_case`。
- Pydantic 模型类名使用 `PascalCase`。
- 动作用动词开头，数据用名词短语。
- 命名要表达职责，不使用 `data`、`info`、`helper`、`thing` 这类宽泛词。

### Graph / Workflow

- workflow 名使用名词短语，例如：`article_analysis`
- node 名使用 `verb_object`，例如：
  - `prepare_input`
  - `derive_user_rules`
  - `generate_annotations`
  - `assemble_result`

不要使用：

- 带版本号的 node 名，例如 `teach_v1`
- 含糊的 node 名，例如 `merge_node`、`finalize_success_node`

### State / Schema / JSON

- state key 与 JSON 对象使用名词短语，例如：
  - `preprocess_result`
  - `user_rules`
  - `annotation_draft`
  - `analysis_result`
- 布尔字段统一使用前缀：
  - `is_*`
  - `has_*`
  - `should_*`
  - `can_*`
- 计数字段统一使用 `*_count`
- 比率字段统一使用 `*_ratio`
- 分数字段统一使用 `*_score`
- 时间字段统一使用 `*_ms`

### Span / Anchor

- 坐标空间必须显式命名，不允许长期保留含糊的裸 `span`
- 推荐字段：
  - `render_span`
  - `sentence_span`
  - `anchor_text`
  - `anchor_occurrence`
- `render_text` 是唯一渲染基准文本

### 渲染契约

- 标注主体字段与渲染字段分层命名：
  - `vocabulary_annotations`
  - `grammar_annotations`
  - `sentence_annotations`
  - `render_marks`
- 展示相关字段统一使用：
  - `display_mode`
  - `display_priority`
  - `display_group`
  - `is_default_visible`
  - `render_index`

当前 workflow 设计以 [Workflow V0 回顾](../docs/workflow/v0/v0-retrospective-report.md) 和 [Workflow V1 设计](../docs/workflow/v1/workflow-v1-design.md) 为准。

## 当前对外接口

- `POST /analyze`

说明：

- 当前仅保留 `POST /analyze`
- 返回结构统一为当前主线 render scene schema（`schema_version = "2.1.0"`）
- 不再保留旧 `v2` 并行接口或兼容响应层
- 结果页主渲染基准是 `render_text`
- `source_text` 仅用于“查看原文”等非默认展示场景

## 当前 workflow

`article_analysis` 主流程：

- `prepare_input`
- `derive_user_rules`
- `generate_annotations`
- `assemble_result`

其中：

- `prepare_input` 负责输入清洗、分段分句和基础拒绝判断
- `derive_user_rules` 负责把 `reading_goal + reading_variant` 转成规则包
- `generate_annotations` 是唯一主教学 LLM 节点，负责词汇、语法、句级讲解与逐句翻译
- `assemble_result` 负责 annotation 投影、锚点解析、渲染标记、全文翻译组装和最终结果收敛

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
- 教学型结构化输出
- 本地锚点解析与前端渲染契约生成
- LangSmith 可观测性与后续增强能力扩展

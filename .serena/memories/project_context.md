# 项目上下文

## 项目定位

本仓库用于开发一个面向非零基础英语用户的微信小程序，核心能力是对英文文章做教学型解读，而不是只返回数据库式的结构化标注。

当前产品方向已经从 V0 的“复杂填表式 workflow”切换到 V1 的“老师在板书”模式，强调：

- 高价值词汇标注
- 重点语法点讲解
- 句级难点讲解
- 可渲染、可分层展示的前端标注数据

## 当前技术栈

- 前端：微信小程序
- 后端：FastAPI + LangGraph + PydanticAI + Pydantic v2
- 模型路由：`server/app/llm`
- 依赖管理：`uv`
- 虚拟环境：`server/.venv`

## 当前后端架构

后端代码集中在 `server/`，并遵循明确分层：

- `app/config`
  只读取原始环境变量
- `app/llm`
  负责 profile registry、route resolution、provider factory、agent runtime injection
- `app/agents`
  只定义 agent blueprint、deps 和中文 prompt
- `app/services/analysis`
  负责输入清洗、用户规则映射、锚点解析、结果组装和 agent runner
- `app/workflow`
  只做 LangGraph 编排、状态流转和 tracing
- `app/schemas/common.py`
  放共享值对象
- `app/schemas/internal`
  放内部 DTO
- `app/schemas/analysis.py`
  放对外 API schema

详细规范以 `server/README.md` 和 `server/ARCHITECTURE.md` 为准。

## 当前 Workflow 状态

V0 已完成回顾，运行时代码层面的 V0 主链路已移除。当前主 workflow 为 V1：

- workflow 名：`article_analysis`
- 主节点：
  - `prepare_input`
  - `derive_user_rules`
  - `generate_annotations`
  - `assemble_result`

职责概览：

- `prepare_input`
  本地清洗输入、生成 `render_text`、分段分句、做基础安全判断
- `derive_user_rules`
  将 `reading_goal + reading_variant` 转为结构化 `user_rules`
- `generate_annotations`
  唯一主教学 LLM 节点，返回句级锚点、教学内容和逐句翻译
- `assemble_result`
  做 `anchor_text -> render_span`、去重过滤、`render_marks` 和最终结果组装

## 当前 API 契约

对外主入口仍为：

- `POST /analyze`

V1 请求侧保留：

- `text`
- `source_type`
- `request_id`
- `model_selection`
- `reading_goal`
- `reading_variant`

V1 响应侧核心结构包括：

- `request`
- `status`
- `article`
  - 同时保留 `source_text` 与 `render_text`
- `vocabulary_annotations`
- `grammar_annotations`
- `sentence_annotations`
- `render_marks`
- `translations`
- `warnings`
- `metrics`

说明：

- 前端主渲染基准是 `render_text`
- `source_text` 仅用于“查看原文”等非默认展示场景
- 坐标只保留相对 `render_text` 的绝对坐标

## 当前用户配置体系

V1 主链路当前采用轻量 `user_config`：

- `reading_goal`
  软偏好，影响讲解风格和默认展示层
- `reading_variant`
  强提示，影响更值得关注的点

后端不直接消费裸配置，而是转换成 `user_rules`，用于：

- prompt 注入
- 差异化标注策略
- 前端展示提示
- 后续 few-shot / 轻量检索扩展预留

当前不在主链路中引入付费增强 feature flag，也不实现 discourse-level annotation。

## 当前模型配置体系

模型配置已经从 V0 的 legacy env 切换到 V1 的 profile/preset 路由体系：

- `MODEL_PROFILES_JSON`
  声明所有可用模型 profile
- `DEFAULT_MODEL_PROFILE` / `ANNOTATION_MODEL_PROFILE`
  声明部署默认路由
- `MODEL_PRESETS_JSON`
  声明服务端命名实验方案
- 请求里的 `model_selection`
  声明单次请求的 runtime override

当前 V1 主链路只使用一个核心 route：

- `annotation_generation`

原则：

- env 负责 profile 注册和部署默认值
- preset 负责服务端实验方案
- request 负责单次 case 的运行时切换
- 不再使用 legacy `ANALYSIS_*` / `GUARDRAILS_*` 配置

## 当前命名与实现约束

必须遵循统一命名规范：

- 版本号不进入业务命名
- Python 函数、LangGraph node 名、JSON 字段统一使用 `snake_case`
- Pydantic 模型类名使用 `PascalCase`
- 坐标空间显式命名：
  - `render_text`
  - `render_span`
  - `sentence_span`
  - `anchor_text`
  - `anchor_occurrence`
- 渲染层字段统一使用：
  - `display_mode`
  - `display_priority`
  - `display_group`
  - `is_default_visible`
  - `render_index`

实现约束：

- 核心代码要补简洁注释，重点注释边界和规则，不注释显而易见字段搬运
- prompt 统一使用中文
- 核心 schema 要补 `Field(description="...")`

## 当前观测与调试

LangSmith 仍然保留并已切换到 V1 语义：

- 顶层 trace 由 LangGraph workflow 创建
- PydanticAI 不启用全局 instrumentation
- 节点内部真实模型调用使用 `@traceable(run_type="llm")`
- 主 llm 子 span 名称为 `annotation_generation_llm_call`

推荐关注的 root metadata：

- `workflow_name`
- `workflow_version`
- `profile_id`
- `reading_goal`
- `reading_variant`
- `model_profile`

## 当前阶段

当前已经完成：

- V0 问题回顾文档
- V1 设计文档
- V1 主链路代码重构
- V0 运行时代码清理
- 静态检查和测试收口

最近一次后端验证状态：

- `ruff` 通过
- `mypy` 通过
- `compileall` 通过
- `pytest` 通过，当前为 `14 passed`

## 接下来最重要的工作

当前项目已经进入 V1 的样本输入测试阶段，接下来重点是：

1. 用真实样本验证 V1 标注质量
2. 重点观察：
   - 锚点解析成功率
   - 跨句污染是否消失
   - 低价值标注过滤是否过强或过弱
   - `reading_goal / reading_variant` 是否只影响展示层和讲解侧重点，而不会导致关键难点漏标
3. 结合 LangSmith trace 和样本 case 继续做 prompt、规则和组装层微调

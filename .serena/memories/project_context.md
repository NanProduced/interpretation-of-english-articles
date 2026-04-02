# 项目上下文

## 项目定位

本仓库用于开发一个面向非零基础英语用户的微信小程序，核心能力是对英文文章做教学型解读，而不是只返回数据库式的结构化标注。

产品方向已经从 V0 的"复杂填表式 workflow"演进到"老师在板书"模式，强调：

- 高价值词汇标注
- 重点语法点讲解
- 句级难点讲解
- 可渲染、可分层展示的前端标注数据

当前状态：V2 已完成并确认不符合预期，正在进行 V2.1 优化规划。

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

## Workflow 版本历史

### V1（已稳定）

- workflow 名：`article_analysis`
- 主节点：
  - `prepare_input`
  - `derive_user_rules`
  - `generate_annotations`
  - `assemble_result`

### V2（已完成，评估未通过）

- workflow 名：`article_analysis`，版本 `v2`
- 主节点（线性顺序）：
  - `prepare_input` → `derive_user_rules` → `generate_annotations` → `assemble_result`

V2 核心变化：

- 输出协议从 V1 的 `vocabulary/grammar/sentence` 三数组切换为统一渲染模型 `RenderSceneModel`
- 前端验证了组件形态（SentenceRow、InlineMark、WordPopup、SentenceActionChip、BottomSheetDetail、AnalysisCard）
- 锚点模型支持 `text` 和 `multi_text` 两种类型
- 翻译层固定为页面独立层，不再是数组字段

V2 评估结论（来自 `docs/workflow/v2/v2-unified-design.md`）：

- 业务分类僵化，LLM 被迫往固定数组里填内容，导致解释方式单一
- 为了满足 schema，模型容易输出低价值标注，用户获得感弱
- 前后端联调顺序倒置，先调 LLM 输出、后看前端能否接住，导致返工成本高

### V2.1（规划中）

V2.1 是 V2 的优化版本，核心方向：

- 让模型从"表单填写者"变成"教学编排者"
- 保留 V2 前端验证过的组件能力，但放宽对 LLM 输出的结构约束
- 后端仍负责锚点稳定和渲染契约，但增强语义校验和质量保障

## 当前 API 契约

对外主入口：

- `POST /api/v2/analyze`
- `GET /api/v2/result/{id}`

V2 请求侧：

- `text`
- `source_type`
- `request_id`
- `model_selection`
- `reading_goal`
- `reading_variant`

V2 响应侧核心结构（`RenderSceneModel`）：

- `request`: AnalyzeRequestMeta
- `article`: ArticleStructure（含 paragraphs/sentences）
- `translations`: 逐句翻译
- `inline_marks`: 行内标注（高亮/下划线）
- `sentence_entries`: 句尾入口
- `cards`: 段间卡片
- `warnings`: 警告信息

前端组件渲染基准：

- `sentence_id` 作为定位硬边界
- 单段锚点使用 `sentenceId + anchorText + occurrence`
- 多段锚点使用 `multi_text.parts[]`
- 不再使用绝对 `start-end` 偏移

## 当前用户配置体系

主链路采用轻量配置：

- `reading_goal`
  软偏好，影响讲解风格和默认展示层
- `reading_variant`
  强提示，影响更值得关注的点

后端转换成 `user_rules`：

- `profile_id`
- `teaching_style`
- `translation_style`
- `grammar_granularity`
- `vocabulary_policy`
- `annotation_budget`（vocabulary_count / grammar_count / sentence_note_count）

## 当前模型配置体系

模型配置采用 profile/preset 路由体系：

- `MODEL_PROFILES_JSON`
  声明所有可用模型 profile
- `DEFAULT_MODEL_PROFILE` / `ANNOTATION_MODEL_PROFILE`
  声明部署默认路由
- `MODEL_PRESETS_JSON`
  声明服务端命名实验方案
- 请求里的 `model_selection`
  声明单次请求的 runtime override

核心 route：

- `annotation_generation`

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

LangSmith 用于全链路追踪：

- 顶层 trace 由 LangGraph workflow 创建
- PydanticAI 不启用全局 instrumentation
- 节点内部真实模型调用使用 `@traceable(run_type="llm")`
- 主 llm 子 span 名称为 `annotation_generation_llm_call`

推荐关注的 root metadata：

- `workflow_name`
- `workflow_version`
- `schema_version`
- `profile_id`
- `reading_goal`
- `reading_variant`
- `model_profile`

## 当前阶段

### 已完成

- V0 问题回顾文档
- V1 设计文档、V1 主链路代码重构、V1 样本测试
- V2 设计文档（`docs/workflow/v2/v2-unified-design.md`）
- V2 前端组件实验与 mock 验证
- V2 统一 schema 收敛
- V2 后端可运行版本
- V2 评估分析

### 进行中

- V2.1 优化规划

V2 评估发现的主要问题：

1. **LLM 输出质量不稳定**：TeachingOutput 完全依赖 LLM 生成，无结构校验，质量波动大
2. **Budget 约束未生效**：prompt 传入 budget 数值但 LLM 未必遵守
3. **Few-shot 示例空置**：`few_shot_examples=[]` 未实际使用
4. **错误处理粒度粗**：未区分 transient error 和 fatal error
5. **翻译覆盖风险**：LLM 可能漏译或重复翻译 sentence_id

## 接下来最重要的工作

V2.1 优化规划
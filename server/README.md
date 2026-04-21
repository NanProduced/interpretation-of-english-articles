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

> **注意**：`prepare_input` 模块依赖 spaCy 语言模型 `en_core_web_sm`（需手动 `python -m spacy download en_core_web_sm`）。完整依赖说明见 [prepare-input-preprocessing-redesign.md](../docs/workflow/v3/prepare-input-preprocessing-redesign.md#122-完整依赖说明与启动检查)。

## 本地数据库与缓存

当前正式方向已经收敛为：

- 正式主库：`PostgreSQL`
- 词典数据：`TECD3` 离线导入 `PostgreSQL`
- 缓存：第一阶段先使用进程内缓存，`Redis` 作为本地调试和后续增强预留

本地可直接使用仓库根目录的 [docker-compose.local.yml](../docker-compose.local.yml) 拉起：

```bash
docker compose -f docker-compose.local.yml up -d
```

默认本地连接：

- PostgreSQL: `postgresql://claread:claread_dev@127.0.0.1:5432/claread`
- Redis: `redis://127.0.0.1:6379/0`

说明：

- 初始 schema 会通过 `server/db/migrations/0001_initial_schema.sql` 在首次建库时自动导入
- 如果你修改了初始 migration，并希望重新初始化本地数据库，需要清掉本地 volume 再重新启动
- 开发期如只想清空业务数据，请执行 `server/db/reset_dev_keep_dict.sql`；该脚本**不会删除或清空** `dict_entries`、`dict_lookup_targets`、`dict_redirects`
- 非特殊情况，**禁止删除、清空或重建** `dict_*` 相关表；如确需处理，必须先确认有完整重导方案（含 `exam_tag` 数据）
- `Redis` 当前不是首发阻塞项，但本地环境先保留，便于后续 session/cache 接入

仅清空非词典业务表的示例命令：

```bash
docker exec -i claread-postgres psql -U claread -d claread < server/db/reset_dev_keep_dict.sql
```

如果你已经在宿主机安装了 `psql`，也可以直接执行：

```bash
psql "postgresql://claread:claread_dev@127.0.0.1:5432/claread" -f server/db/reset_dev_keep_dict.sql
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
- `app/services/analysis`
  分析任务业务逻辑和 agent runner
- `app/services/quota/`
  配额查询、额度校验、积分扣减与发放
- `app/services/auth/`
  微信登录、会话管理、用户资料更新
- `app/services/feedback/`
  反馈提交、查询、状态更新与奖励发放
- `app/services/user_assets/`
  用户资产（records, vocabulary, favorites）CRUD
- `app/services/daily_reader/`
  每日精读 Pipeline、文章 CRUD、内容安全检测
- `app/services/dictionary/`
  词典查询、lemma 归并、短语候选、缓存
- `app/workflow`
  只做 LangGraph 编排与 tracing
- `app/schemas/common.py`
  放共享值对象
- `app/schemas/internal`
  放内部 DTO
- `app/schemas/analysis.py`
  放分析任务 API schema
- `app/schemas/quota.py`
  放配额与积分明细 schema
- `app/schemas/auth.py`
  放认证 schema
- `app/schemas/feedback.py`
  放反馈 schema
- `app/schemas/health.py`
  放健康检查 schema
- `app/schemas/daily_reader.py`
  放每日精读 schema
- `app/schemas/tasks.py`
  放任务 schema
- `app/schemas/user_assets/`
  放用户资产 schema 子目录（records, vocabulary, favorites）

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

当前 workflow 的重构设计以 [Workflow V3 设计与重构文档](../docs/workflow/v3/workflow-v3-design.md) 为准。  
当前代码实现若尚未完成迁移，可参考 [Workflow V2.1 改造设计稿](../docs/workflow/v2/v2-1-refactor-design.md) 理解现状。

## 当前对外接口

- `POST /analysis-tasks` — 提交分析任务
- `GET /analysis-tasks/{task_id}` — 查询任务状态
- `GET /analysis-tasks/current` — 获取当前活跃任务
- `POST /analyze` — 直接分析（匿名用户）
- `GET/POST/PATCH/DELETE /records` — 分析记录 CRUD
- `GET/POST/PATCH/DELETE /vocabulary` — 生词本 CRUD
- `GET/POST/DELETE /favorites` — 收藏 CRUD
- `GET /dict` — 词典查询
- `POST /auth/wechat/login` — 微信登录
- `GET /me/quota` — 用户配额查询

### 任务接口字段语义

任务接口响应中的 ID 字段：

| 字段 | 类型 | 语义 | 状态 |
|------|------|------|------|
| `task_id` | UUID | 任务主键 | 当前 |
| `record_id` | UUID | 云端 analysis_records.id | **已弃用**，用 `cloud_record_id` 替代 |
| `cloud_record_id` | UUID | 云端 analysis_records.id | 新增 |
| `client_record_id` | string | 前端生成的稳定记录主键 | 新增 |

### 生词本接口字段语义

生词本响应中的来源记录 ID 字段：

| 字段 | 类型 | 语义 | 状态 |
|------|------|------|------|
| `analysis_record_id` | UUID | 来源记录云端 ID | **已弃用**，用 `source_cloud_record_id` 替代 |
| `client_record_id` | string | 来源记录前端主键 | **已弃用**，用 `source_client_record_id` 替代 |
| `source_cloud_record_id` | UUID | 来源记录云端 ID | 新增 |
| `source_client_record_id` | string | 来源记录前端主键 | 新增 |

说明：

- 当前仅保留 `POST /analyze`
- 返回结构统一为当前主线 render scene schema（`schema_version = "2.1.0"`）
- 不再保留旧 `v2` 并行接口或兼容响应层
- 结果页主渲染基准是 `render_text`
- `source_text` 仅用于“查看原文”等非默认展示场景

## 当前实现状态

当前代码中的主流程仍为：

- `prepare_input`
- `derive_user_rules`
- `generate_annotations`
- `assemble_result`

这是 v2.1 阶段的实现形态，其中：

- `prepare_input` 负责输入清洗、分段分句和基础拒绝判断
- `derive_user_rules` 负责把 `reading_goal + reading_variant` 转成规则包
- `generate_annotations` 是唯一主教学 LLM 节点，负责词汇、语法、句级讲解与逐句翻译
- `assemble_result` 负责 annotation 投影、锚点解析、渲染标记、全文翻译组装和最终结果收敛

v3 的目标形态将拆分为：

- `prepare_input`
- `derive_user_config`
- `vocabulary_agent`
- `grammar_agent`
- `translation_agent`
- `normalize_and_ground`
- `repair_agent`
- `project_render_scene`
- `assemble_result`

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

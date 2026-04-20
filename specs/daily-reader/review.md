# Code Review Notes

## Findings

### 1. 每日精读功能完全缺失

严重程度：高

当前项目中不存在任何每日精读相关的代码实现：

- 无 Daily Reader 页面、组件或路由
- 无 Daily Reader API 端点
- 无 Daily Reader 数据库表
- 无文章拉取 Pipeline 或定时任务
- 无专用 Daily Reader Workflow

涉及文件：

- 无（空白区域）

结论：

- 这是当前项目的功能空白，需要从零构建
- 设计文档已迁移至 [specs/daily-reader/](../../specs/daily-reader/)

### 2. 首页每日精选为静态占位

严重程度：中

首页 [home/index.tsx](../../client/src/pages/home/index.tsx) 中存在硬编码的推荐文章卡片，但未接入真实数据，点击无跳转逻辑：

- 3 篇文章为硬编码 mock 数据
- 卡片点击事件未绑定导航
- 无 API 调用逻辑

涉及文件：

- [client/src/pages/home/index.tsx](../../client/src/pages/home/index.tsx) — 静态推荐卡片区域

结论：

- 首页入口需要重新设计为动态数据驱动的杂志封面卡片
- 需要新增 Daily Reader API client 和状态管理

### 3. 现有 Workflow 可复用基础但必须隔离

严重程度：低（正面发现）

现有 LangGraph Workflow 基础设施完善，Daily Reader 可复用运行时但必须独立建图：

- LangGraph 图构建模式可复用（StateGraph、节点注册、边定义）
- PromptComposer + PromptSection 机制可复用框架，新建 Daily 专用策略
- Agent 基础设施（LLM 调用、结构化输出）可复用
- 但 Daily Reader 不需要 preprocess/repair/degraded fallback，必须独立

涉及文件：

- [server/app/workflow/learning_workflow.py](../../server/app/workflow/learning_workflow.py) — Learning Workflow 图定义
- [server/app/workflow/academic_workflow.py](../../server/app/workflow/academic_workflow.py) — Academic Workflow 图定义
- [server/app/services/analysis/prompting/prompt_composer.py](../../server/app/services/analysis/prompting/prompt_composer.py) — Prompt 组装机制
- [server/app/services/analysis/prompting/prompt_strategy.py](../../server/app/services/analysis/prompting/prompt_strategy.py) — Prompt 策略体系

结论：

- 新建 `daily_reader_workflow.py`，复用 LangGraph 运行时
- 新建 Daily Reader 专用 Prompt 策略，不复用主线策略
- 不复用 `goal_planner.py` 的 topology 分流逻辑

### 4. 词典查询能力可直接复用

严重程度：低（正面发现）

现有 `/dict` API 和前端词典交互组件完善，可直接在每日精读页复用：

- 后端：`/dict` API + TECD3 + spaCy 短语嗅探 + 两级缓存
- 前端：`WordPopup` 组件（mini 卡片 → full 详情）
- 前端：`ClickableWord` 组件（正文中的词级交互）
- 前端：`dict.adapter.ts`（DTO → VM 转换）

涉及文件：

- [server/app/services/dictionary/service.py](../../server/app/services/dictionary/service.py) — 词典服务入口
- [client/src/components/WordPopup/index.tsx](../../client/src/components/WordPopup/index.tsx) — 单词弹窗
- [client/src/components/ClickableWord/index.tsx](../../client/src/components/ClickableWord/index.tsx) — 可点击单词
- [client/src/services/api/adapters/dict.adapter.ts](../../client/src/services/api/adapters/dict.adapter.ts) — 词典适配器

结论：

- 每日精读页的词典交互复用现有组件，调整视觉样式即可
- mini 卡片 → bottom sheet 的两层交互与设计文档一致
- LLM 标注词的语境解释需在 bottom sheet 中优先展示

### 5. 高亮渲染组件可复用核心逻辑

严重程度：低（正面发现）

现有 `InlineMark` 组件支持多种标注类型渲染，核心逻辑可复用：

- `vocab_highlight`：词汇高亮
- `phrase_gloss`：短语高亮
- `context_gloss`：语境高亮
- `grammar_note`：语法标注（Daily Reader 中弱化）

涉及文件：

- [client/src/components/InlineMark/index.tsx](../../client/src/components/InlineMark/index.tsx) — 行内标注渲染

结论：

- 复用 InlineMark 的核心渲染逻辑，调整视觉样式（更柔和的背景色块）
- Daily Reader 中不渲染 `grammar_note` 类型
- 高亮视觉风格需与杂志式阅读感一致（浅色背景+柔和边框，非强色块）

### 6. 数据库 Migration 体系已建立

严重程度：低（正面发现）

项目已有 migration 体系：

- `server/db/migrations/0001_initial_schema.sql` — 初始表结构
- `server/db/migrations/0002_feedback_system.sql` — 反馈系统

涉及文件：

- [server/db/migrations/](../../server/db/migrations/) — Migration 目录

结论：

- 新建 `0003_daily_reader.sql`，遵循现有命名和风格规范
- 使用 UUID 主键、JSONB 扩展、CHECK 约束枚举等现有约定

### 7. 文章拉取技术栈需新增依赖

严重程度：中

当前后端 Python 依赖中不包含文章拉取所需的库：

- `feedparser`：RSS/Atom 解析（需新增）
- `trafilatura`：正文提取（需新增）
- `httpx`：HTTP 客户端（可能已有，需确认）

涉及文件：

- [server/requirements.txt](../../server/requirements.txt) — Python 依赖

结论：

- 需要在 requirements.txt 中新增 `feedparser` 和 `trafilatura`
- Guardian API 调用可复用现有 `httpx` 客户端
- 定时任务可使用 `APScheduler` 或复用现有 Celery 配置

### 8. 版权合规需注意

严重程度：高（合规）

从外部媒体拉取文章涉及版权问题：

- BBC RSS 条款：仅限个人非商用，商用需授权
- Guardian API：非商用免费，商用需付费
- NPR RSS：免费但需遵守使用条款
- The Atlantic：全文可能受付费墙保护

结论：

- 初期阶段（非商用）可直接使用 Guardian API 和 BBC/NPR RSS
- 页面上必须标注原文来源和链接，引导用户访问原始网站
- Daily Reader 页面展示的是 AI 解析后的精读内容，不是原文全文复制
- 如后续商业化，需要与各来源谈内容授权

## Architectural Direction

### Good current foundations

- LangGraph Workflow 基础设施完善，Daily Reader 可复用运行时独立建图
- PromptComposer + PromptSection 机制灵活，可快速构建 Daily 专用策略
- 词典服务完整（TECD3 + spaCy + 两级缓存），可直接复用
- 前端高亮/点词组件体系成熟，调整视觉即可复用
- 数据库 Migration 体系规范，新增表无障碍
- `article.ts` store 的状态管理模式可参考，但 Daily Reader 需要独立 store

### Design direction

- 四层 Pipeline 架构：发现层（RSS/API）→ 提取层（trafilatura）→ 安全检测层（微信 msgSecCheck）→ 筛选层（AI 评分）
- Guardian API 为主力源（全文+封面+标签+字数筛选一条龙）
- BBC/NPR RSS 为辅助源（需 trafilatura 二次提取全文）
- Daily Reader Workflow 独立建图，8 个节点（含 quality_review 必经审核 + refinement 条件优化）
- `daily_readers` 表独立存储，JSONB 存储 body/highlights/footer_analysis
- 前端独立页面 `pages/daily-reader/index`，不复用结果页布局
- 首页入口为 2-3 张杂志封面式卡片（横向滑动或纵向排列），动态数据驱动

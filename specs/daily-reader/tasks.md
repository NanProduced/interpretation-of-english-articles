# Implementation Plan

## Phase 1 — 文章拉取 Pipeline + 专用 Workflow + 数据入库

### A1. 数据库 Migration

- [ ] A1.1 新建 `server/db/migrations/0003_daily_reader.sql`
  - 创建 `daily_readers` 表（含 content_sec_check 字段、约束、索引、触发器、注释）
  - _Requirement: 6_

### A2. Python 依赖

- [ ] A2.1 修改 `server/requirements.txt`
  - 新增 `feedparser`（RSS/Atom 解析）
  - 新增 `trafilatura`（正文提取）
  - _Requirement: 1_

### A3. Pipeline 发现层

- [ ] A3.1 新建 `server/app/services/daily_reader/discovery.py`
  - `discover_guardian()` — Guardian API 搜索，含 wordcount 筛选
  - `discover_rss()` — BBC/NPR RSS 解析，提取标题/链接/摘要/封面
  - `ARTICLE_SOURCES` 配置常量
  - _Requirement: 1_

### A4. Pipeline 提取层

- [ ] A4.1 新建 `server/app/services/daily_reader/extraction.py`
  - `extract_with_trafilatura()` — 从 URL 提取正文+元数据
  - 处理提取失败、空文本等边界情况
  - _Requirement: 1_

### A5. Pipeline 内容安全检测

- [ ] A5.1 新建 `server/app/services/daily_reader/content_security.py`
  - `check_content_security()` — 微信 msgSecCheck API 调用
  - `get_wechat_access_token()` — 复用现有微信认证逻辑
  - 结果判定：pass 放行，review/risky 拒绝；API 异常或字段缺失时默认 review（fail-closed）
  - 结果存储到 content_sec_check JSONB
  - _Requirement: 2_

### A6. Pipeline 筛选层

- [ ] A6.1 新建 `server/app/services/daily_reader/scoring.py`
  - `score_article()` — LLM 4维评分（language_richness, topic_interest, structure_clarity, cultural_value）
  - `estimate_cefr()` — CEFR 难度估算
  - `deduplicate()` — URL 去重 + 标题模糊匹配
  - _Requirement: 3_

### A7. Pipeline 编排

- [ ] A7.1 新建 `server/app/services/daily_reader/pipeline.py`
  - `run_daily_pipeline()` — 四层编排（发现→提取→安全检测→筛选）
  - `select_diverse_candidates()` — 来源多样化+主题多样化+封面图优先选择逻辑
  - 每天选择 2-3 篇候选执行 workflow（同来源不超过 2 篇，优先有封面图的文章）
  - Pipeline 运行元数据记录
  - 定时执行时间：UTC+8 8:00-9:00
  - _Requirement: 1, 2, 3, 4_

### A8. 模型路由扩展

- [ ] A8.1 修改 `server/app/llm/routes.py`
  - 新增 `daily_annotation`、`daily_analysis`、`daily_review` 三个 ModelRoute
  - _Requirement: 5_

### A9. Daily Reader Workflow

- [ ] A9.1 新建 `server/app/services/analysis/prompting/daily_prompt_strategy.py`
  - Daily Reader 专用 Prompt 策略
  - 与主线策略的关键差异：克制标注密度、无语法标注、增加全篇解析、增加质量审核
  - _Requirement: 5_

- [ ] A9.2 新建 `server/app/agents/daily_vocab_agent.py`
  - 词汇高亮 Agent，每段不超过 3-5 个
  - 优先标注 B1-C1 级词汇
  - 使用 `daily_annotation` 模型路由
  - _Requirement: 5_

- [ ] A9.3 新建 `server/app/agents/daily_footer_agent.py`
  - 文末分析 Agent，生成摘要/主旨/结构/关键表达/易误读点/讨论问题
  - 使用 `daily_analysis` 模型路由
  - _Requirement: 5_

- [ ] A9.4 新建 `server/app/agents/daily_interpretation_agent.py`
  - 全篇解析 Agent，生成连贯讲解式解析（非逐句拆解）
  - 使用 `daily_analysis` 模型路由
  - _Requirement: 5_

- [ ] A9.5 新建 `server/app/agents/daily_review_agent.py`
  - 质量审核 Agent，6 维审核（highlight_accuracy/density, footer_completeness/accuracy, interpretation_coherence, annotation_consistency）
  - 输出 QualityReviewResult（passed, issues, overall_score）
  - 使用 `daily_review` 模型路由
  - _Requirement: 5_

- [ ] A9.6 新建 `server/app/agents/daily_refinement_agent.py`
  - 优化修正 Agent，根据审核建议修正具体问题
  - 仅执行一轮，支持 abort 返回
  - 使用 `daily_review` 模型路由
  - _Requirement: 5_

- [ ] A9.7 新建 `server/app/workflow/daily_reader_workflow.py`
  - 8 节点图：light_normalize → vocab_highlight → phrase_context_gloss → footer_analysis → full_interpretation → quality_review → (conditional) refinement → daily_projection
  - DailyReaderState 定义
  - `_should_refine()` 条件边
  - daily_projection 节点组装最终 payload
  - 每个节点使用对应的模型路由
  - _Requirement: 5_

### A10. Pipeline + Workflow 端到端验证

- [ ] A10.1 手动触发 Pipeline → 生成 payload → 入库 daily_readers 表
  - 验证 Guardian API 拉取 → 全文提取 → 内容安全检测 → AI 评分 → Workflow 生成 → 入库
  - 验证 BBC RSS 拉取 → trafilatura 提取 → 内容安全检测 → AI 评分 → Workflow 生成 → 入库
  - 验证内容安全检测：违规文章被过滤
  - 验证 quality_review 节点正常执行
  - 验证 refinement 条件触发
  - 验证 top-3 候选尝试策略
  - _Requirement: 1, 2, 3, 4, 5, 6_

---

## Phase 2 — 后端 Daily Reader API

### B1. Schema

- [ ] B1.1 新建 `server/app/schemas/daily_reader.py`
  - `DailyReaderArticleResponse` — 完整文章响应
  - `DailyReaderListItem` — 列表项
  - `DailyReaderListResponse` — 列表响应
  - `DailyReaderGenerateRequest` — 管理端生成请求
  - `DailyReaderPublishRequest` — 管理端发布请求
  - _Requirement: 6, 7_

### B2. Service

- [ ] B2.1 新建 `server/app/services/daily_reader/service.py`
  - `get_today_articles()` — 获取今日已发布文章列表
  - `get_article_by_id()` — 按 ID 获取文章
  - `list_articles()` — 分页列表
  - `generate_article()` — 触发 Pipeline + Workflow
  - `publish_article()` — 发布文章（设置 published_at）
  - _Requirement: 6, 7_

### B3. Routes

- [ ] B3.1 新建 `server/app/api/routes/daily_reader.py`
  - `GET /daily-reader/today` — 今日文章
  - `GET /daily-reader/{id}` — 按 ID 获取
  - `GET /daily-reader` — 文章列表
  - _Requirement: 7_

- [ ] B3.2 新建 `server/app/api/routes/daily_reader_admin.py`
  - `POST /daily-reader/admin/generate` — 触发生成（异步，返回 task_id）
  - `POST /daily-reader/admin/publish` — 发布文章
  - `POST /daily-reader/admin/unpublish` — 取消发布
  - `DELETE /daily-reader/admin/{id}` — 删除 draft 文章
  - `GET /daily-reader/admin/drafts` — 获取 draft 列表
  - `POST /daily-reader/admin/retry` — 重试 workflow
  - API Key 认证，预留后续接入小程序云开发-云后台
  - _Requirement: 7_

- [ ] B3.3 修改 `server/app/api/router.py`
  - 注册 daily_reader 路由
  - 注册 daily_reader_admin 路由
  - _Requirement: 7_

---

## Phase 3 — 前端每日精读页面

### C1. 类型定义与 API Client

- [ ] C1.1 新建 `client/src/types/api/daily-reader.dto.ts`
  - 后端 DTO 类型（snake_case）
  - _Requirement: 7, 8_

- [ ] C1.2 新建 `client/src/types/view/daily-reader.vm.ts`
  - 前端 VM 类型（camelCase）
  - _Requirement: 8_

- [ ] C1.3 新建 `client/src/services/api/daily-reader.client.ts`
  - `fetchTodayArticles()` — 获取今日文章列表
  - `fetchArticleById()` — 按 ID 获取
  - `fetchArticleList()` — 文章列表
  - _Requirement: 7_

- [ ] C1.4 新建 `client/src/services/api/adapters/daily-reader.adapter.ts`
  - DTO → VM 转换
  - _Requirement: 7, 8_

- [ ] C1.5 新建 `client/src/services/api/adapters/daily-reader-highlight.adapter.ts`
  - DailyReaderHighlight → InlineMarkModel 适配（供 WordPopup 使用）
  - _Requirement: 8_

### C2. 状态管理

- [ ] C2.1 新建 `client/src/stores/daily-reader.ts`
  - Zustand store：todayArticles, articleList, loading, error
  - fetchToday / fetchList actions
  - _Requirement: 8, 9_

### C3. 核心组件

- [ ] C3.1 新建 `client/src/components/DailyReaderHeader/index.tsx`
  - 页头：标题、副标题、来源、日期、难度、时长、标签
  - 封面图/氛围渐变背景
  - _Requirement: 8_

- [ ] C3.2 新建 `client/src/components/DailyReaderHighlightWord/index.tsx`
  - 高亮词组件：浅色背景色块，点击触发 mini 卡片
  - 与主线 InlineMark 视觉差异化
  - _Requirement: 8_

- [ ] C3.3 新建 `client/src/components/DailyReaderBody/index.tsx`
  - 正文：杂志式排版（衬线体、1.6-1.8 行高、宽松段间距）
  - 高亮词渲染（使用 DailyReaderHighlightWord）
  - 点词查词交互（复用 ClickableWord 逻辑）
  - _Requirement: 8_

- [ ] C3.4 新建 `client/src/components/DailyReaderFooterAnalysis/index.tsx`
  - 文末解析：摘要、结构（可折叠树）、关键表达（卡片网格）、全篇解析（默认折叠）、讨论问题
  - 每个模块用图标+标题分隔
  - _Requirement: 8_

- [ ] C3.5 复用 `client/src/components/WordPopup/index.tsx`
  - 精读页集成 WordPopup（mode='mini' + mode='full'）
  - 通过 daily-reader-highlight.adapter 将 DailyReaderHighlight 转为 InlineMarkModel
  - 点击高亮词 → mini 卡片（AI 标注 + 词典摘要）→ 点击展开 → full 词典详情
  - 点击非高亮词 → mini 卡片 → 调用 /dict API
  - _Requirement: 8_

- [ ] C3.6 新建 `client/src/components/DailyReaderProgress/index.tsx`
  - 阅读进度条（scroll-based）
  - _Requirement: 10_

### C4. 页面

- [ ] C4.1 新建 `client/src/pages/daily-reader/index.tsx`
  - 组合所有组件：Header → Body → FooterAnalysis → 往期精选入口
  - 集成 WordPopup（mini + full 模式）
  - 进度条浮层
  - 分享配置（onShareAppMessage）
  - _Requirement: 8, 10, 11_

- [ ] C4.2 新建 `client/src/pages/daily-reader-archive/index.tsx`
  - 归档页：逆序分页列表，每条含标题/来源/日期/难度/时长/封面缩略图
  - 使用 fetchArticleList API
  - 点击跳转精读页
  - _Requirement: 10_

- [ ] C4.3 修改 `client/src/app.config.ts`
  - 注册 `pages/daily-reader/index`
  - 注册 `pages/daily-reader-archive/index`
  - _Requirement: 8_

### C5. 首页入口

- [ ] C5.1 修改 `client/src/pages/home/index.tsx`
  - 替换硬编码推荐卡片为 `GET /daily-reader/today` 动态数据
  - 展示 2-3 张杂志封面式卡片（横向滑动或纵向排列），每张含标题+来源+难度+封面图/渐变
  - 点击导航到 `pages/daily-reader/index?id={articleId}`
  - 无今日文章时优雅降级（隐藏卡片区域或显示 fallback）
  - "每日精选"标题旁添加"更多 →"链接，导航到归档页
  - _Requirement: 9_

---

## Phase 4 — 验证与收尾

### D1. 编译检查

- [ ] D1.1 Python 后端编译检查
  - schema / route / service / workflow / agents 编译通过
  - _Requirement: 1, 2, 3, 4, 5, 6_

- [ ] D1.2 TypeScript 前端编译检查
  - `tsc --noEmit` 通过
  - _Requirement: 7, 8, 9, 10, 11_

### D2. 端到端验证

- [ ] D2.1 Pipeline 生成 → 数据库有记录
  - 手动触发 `POST /daily-reader/admin/generate`
  - 验证 daily_readers 表有新记录
  - 验证 content_sec_check 字段有安全检测结果
  - _Requirement: 1, 2, 3, 4, 5_

- [ ] D2.2 API 验证
  - `GET /daily-reader/today` → 返回今日文章
  - `GET /daily-reader/{id}` → 返回指定文章
  - `GET /daily-reader` → 返回文章列表
  - _Requirement: 7_

- [ ] D2.3 前端页面验证
  - 首页卡片 → 点击 → 进入每日精读页
  - 正文阅读 → 点词 → mini 卡片 → bottom sheet
  - 文末解析区 → 折叠/展开全篇解析
  - 关键表达卡片 → 点击查看详情
  - _Requirement: 8_

- [ ] D2.4 分享验证
  - 分享按钮 → 生成分享卡片
  - 分享消息标题和描述正确
  - _Requirement: 11_

- [ ] D2.5 视觉走查
  - 页面看起来像杂志，不像分析报告
  - 正文阅读流畅，不被过多解释打断
  - 文末解析有明显价值
  - _Requirement: 8_

---

## 后续预留功能（不在本次范围）

| 功能 | 预留方式 | 预计优先级 |
|------|---------|-----------|
| 音频朗读（TTS） | body_json 可扩展 audio_url 字段 | P1 |
| 阅读打卡/连续天数 | 暂不做，避免学习压力感 | P2 |
| AI 生成封面图 | cover_image_url 字段已预留 | P3 |
| 多难度版本 | difficulty 字段已预留，后续可按用户水平推送 | P2 |
| 定时自动发布 | admin/generate API 已预留，后续加 APScheduler（UTC+8 8:00-9:00） | P1 |
| Guardian 商用授权 | source_url 字段已预留，后续谈授权 | P2 |
| Medium 文章源 | discovery.py 可扩展新 source type | P3 |
| msgSecCheck openid 保活 | 定时触发小程序访问保活管理员 openid | P1 |

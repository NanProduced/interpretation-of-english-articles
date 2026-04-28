# Code Review Notes

> **审查更新：2026-04-27**
> 原始审查结论"每日精读功能完全缺失"已过时。当前 Daily Reader 已基本实现（~90%），后端 Pipeline + Workflow + API + 前端页面均已落地。本文件已更新为当前状态。

## Findings

### 1. 每日精读已基本实现

严重程度：信息（原为"高"）

当前项目中每日精读功能已全面落地：

- ✅ Daily Reader Workflow：8 节点 LangGraph 图（`daily_reader_workflow.py`）
- ✅ 5 个专用 Agent：daily_vocab / daily_footer / daily_interpretation / daily_review / daily_refinement
- ✅ 四层 Pipeline：发现层（Guardian API + BBC/NPR RSS）→ 提取层（trafilatura）→ 安全检测层（msgSecCheck）→ 筛选层（AI 4维评分）
- ✅ `daily_readers` 数据库表 + `pipeline_runs` 追踪表
- ✅ 用户侧 API（`/daily-reader/today`、`/daily-reader`、`/daily-reader/{id}`）
- ✅ 管理端 API（`/daily-reader/admin/generate`、`/publish`、`/unpublish`、`/delete`、`/drafts`、`/retry`、`/status/{id}`）
- ✅ 前端精读页（`packageB/daily-reader/index`）+ 归档页（`packageB/daily-reader-archive/index`）
- ✅ 首页精读卡片列表已接入动态数据
- ✅ 6 个专用前端组件（DailyReaderHeader / DailyReaderBody / DailyReaderFooterAnalysis / DailyReaderProgress / DailyReaderHighlightWord / DailyReaderBottomSheet）

涉及文件：

- [server/app/workflow/daily_reader_workflow.py](../../server/app/workflow/daily_reader_workflow.py)
- [server/app/services/daily_reader/pipeline.py](../../server/app/services/daily_reader/pipeline.py)
- [server/app/api/routes/daily_reader.py](../../server/app/api/routes/daily_reader.py)
- [server/app/api/routes/daily_reader_admin.py](../../server/app/api/routes/daily_reader_admin.py)
- [client/src/packageB/daily-reader/index.tsx](../../client/src/packageB/daily-reader/index.tsx)
- [client/src/packageB/daily-reader-archive/index.tsx](../../client/src/packageB/daily-reader-archive/index.tsx)

### 2. 首页精读入口已动态化

严重程度：信息（原为"中"）

首页已从硬编码 mock 卡片升级为动态数据驱动的精读卡片列表：

- ✅ 通过 `useDailyReaderStore` 拉取当日精读列表
- ✅ 卡片展示封面图/主题色、难度标签、来源、阅读时长
- ✅ 点击跳转到精读详情页
- ✅ 空状态展示（文章准备中插画提示）

涉及文件：

- [client/src/pages/home/index.tsx](../../client/src/pages/home/index.tsx)

### 3. 内容安全检测层未集成到 Pipeline 执行流

严重程度：中

`content_security.py` 代码已实现（微信 msgSecCheck API 调用），但 `pipeline.py` 中未调用 `check_content_security()`。Spec 明确要求在提取全文后、AI 评分前执行安全检测，当前 Pipeline 跳过了这一层。

涉及文件：

- [server/app/services/daily_reader/content_security.py](../../server/app/services/daily_reader/content_security.py) — 已实现但未被调用
- [server/app/services/daily_reader/pipeline.py](../../server/app/services/daily_reader/pipeline.py) — 缺少安全检测调用

结论：

- 需在 Pipeline 的提取层和筛选层之间插入安全检测调用
- 检测不通过的文章应标记为 rejected 并跳过

### 4. 定时自动执行 Pipeline 未实现

严重程度：中

Spec 要求 UTC+8 每天 8:00-9:00 自动执行 Pipeline，当前仅支持通过管理端 API 手动触发 `POST /daily-reader/admin/generate`。

结论：

- 需引入 APScheduler 或类似机制实现定时执行
- 需实现 msgSecCheck openid 保活机制

### 5. 分享卡片自定义图片未实现

严重程度：低

[daily-reader/index.tsx:43](../../client/src/packageB/daily-reader/index.tsx) 有 TODO 注释：上线前需为分享卡片生成自定义 imageUrl（使用 cover_theme 渐变 + 标题 + 来源绘制）。

### 6. 精读页生词/收藏持久化未完成

严重程度：低

`handleAddVocab` 和 `handleFavorite` 回调仅显示 Toast，未接入实际的生词本/收藏持久化逻辑。

### 7. ARTICLE_SOURCES 配置与 Spec 有差异

严重程度：低

实际实现的 RSS sections 与 spec 规划有差异：
- Guardian：spec 含 lifeandstyle/society，实际只有 science/technology/culture
- BBC：spec 含 health/culture/business，实际只有 science/technology/business
- NPR：spec 含 culture，实际只有 science/technology

结论：当前配置更聚焦科技/文化类文章，与产品定位一致，可保持现状。

### 8. Spec 规划的前端路径与实际分包路径不一致

严重程度：低（信息）

Spec 规划前端页面为 `pages/daily-reader/`，实际为 `packageB/daily-reader/`（微信小程序分包）。功能无差异，仅路径不同。

## Architectural Direction

### Current foundations (updated)

- ✅ LangGraph Workflow 基础设施已复用，Daily Reader 独立建图完成
- ✅ PromptComposer + Daily 专用策略（`daily_prompt_strategy.py`）已实现
- ✅ 词典服务完整复用（TECD3 + spaCy + 两级缓存）
- ✅ 前端高亮/点词组件体系复用（InlineMark + WordPopup + ClickableWord）
- ✅ 数据库 Migration 体系规范（0003-0006 四个迁移文件）
- ✅ 独立 Store（`daily-reader.ts`）和 API Client（`daily-reader.client.ts`）

### Remaining work

- 集成内容安全检测到 Pipeline 执行流
- 实现定时自动执行 Pipeline
- 实现分享卡片自定义图片
- 实现精读页生词/收藏持久化
- 上线前封面存储迁移至 COS + CDN

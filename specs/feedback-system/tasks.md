# Implementation Plan

## Phase 1 — 数据库与后端 API

### A1. 数据库 migration

- [ ] A1.1 新建 `server/db/migrations/0002_feedback_system.sql`
  - 创建 `feedback` 表（含所有字段、约束、索引、触发器、注释）
  - 扩展 `user_credit_ledger` entry_type CHECK 约束（新增 `feedback_reward`）
  - _Requirement: 8_

### A2. Feedback Schema

- [ ] A2.1 新建 `server/app/schemas/feedback.py`
  - `FeedbackCreateRequest` — 提交请求体
  - `FeedbackResponse` — 提交响应体
  - `FeedbackListItem` — 列表项
  - `FeedbackListResponse` — 列表响应体
  - `FEEDBACK_TYPES_BY_SCOPE` — 枚举常量
  - 校验逻辑：dictionary 仅允许 negative、annotation 必填 annotation_type 等
  - _Requirement: 1, 2, 3, 4, 8_

### A3. Feedback Service

- [ ] A3.1 新建 `server/app/services/feedback/service.py`
  - `submit_feedback()` — 提交/更新反馈（upsert 语义）
  - `list_user_feedback()` — 查询用户反馈列表（游标分页）
  - `delete_feedback()` — 删除反馈（仅自己的 + pending 状态）
  - `update_feedback_status()` — 更新反馈状态（内部 API 用）
  - `reward_feedback()` — 发放反馈奖励积分（内部 API 用）
  - `get_feedback_stats()` — 反馈统计概览（内部 API 用）
  - _Requirement: 1, 2, 3, 4, 5, 7, 8_

### A4. Feedback Routes

- [ ] A4.1 新建 `server/app/api/routes/feedback.py`
  - `POST /api/feedback` — 提交反馈
  - `GET /api/feedback` — 查询反馈列表
  - `DELETE /api/feedback/{id}` — 删除反馈
  - _Requirement: 1, 2, 3, 4, 7_

- [ ] A4.2 新建 `server/app/api/routes/internal_feedback.py`
  - `PATCH /api/internal/feedback/{id}/status` — 更新反馈状态
  - `POST /api/internal/feedback/{id}/reward` — 发放奖励积分
  - `GET /api/internal/feedback/stats` — 反馈统计概览
  - API Key 认证（非用户 session）
  - _Requirement: 5_

- [ ] A4.3 修改 `server/app/api/router.py`
  - 注册 feedback 路由
  - 注册 internal_feedback 路由
  - _Requirement: 1, 2, 3, 4, 5_

### A5. Credit Service Extension

- [ ] A5.1 修改 `server/app/services/analysis/credit_service.py`
  - 新增 `grant_bonus_credits()` 函数
  - 补充每日重置时写入 `daily_grant` ledger 记录
  - _Requirement: 5, 6_

- [ ] A5.2 修改 `server/app/api/routes/quota.py`
  - 新增 `GET /me/credit/ledger` 端点
  - `LedgerEntryResponse` — 含 description、article_title
  - `LedgerListResponse` — 游标分页
  - description 生成逻辑（按 entry_type 映射中文描述）
  - article_title 通过 task_id JOIN analysis_records 获取
  - _Requirement: 6_

---

## Phase 2 — 前端反馈组件与页面

### B1. API Client

- [ ] B1.1 新建 `client/src/services/api/feedback.client.ts`
  - `submitFeedback()` — 提交反馈
  - `fetchFeedbackList()` — 查询反馈列表
  - `deleteFeedback()` — 删除反馈
  - DTO 类型定义与映射
  - _Requirement: 1, 2, 3, 4, 7_

- [ ] B1.2 新建 `client/src/services/api/credit.client.ts`
  - `fetchCreditLedger()` — 查询积分流水
  - DTO 类型定义与映射
  - _Requirement: 6_

### B2. 结果页整体反馈

- [ ] B2.1 新建 `client/src/components/FeedbackWidget/index.tsx`
  - 👍 / 👎 按钮组件
  - 👎 展开面板（5 个选项 + 可选文本 + 提交）
  - 已反馈状态展示
  - Props: `recordId`, `readingGoal`, `readingVariant`, `userFacingState`
  - _Requirement: 1_

- [ ] B2.2 修改 `client/src/pages/result/index.tsx`
  - 在底部操作栏区域集成 FeedbackWidget
  - 传递 recordId 等参数
  - _Requirement: 1_

### B3. 批注级反馈

- [ ] B3.1 新建 `client/src/components/AnnotationFeedback/index.tsx`
  - 反馈选项浮层组件
  - 正面选项：有帮助
  - 负面选项：标注有误、释义不准确、标注范围有误、不该标注、其他
  - 可选文本输入
  - _Requirement: 2_

- [ ] B3.2 修改 `client/src/components/ParagraphBlock/index.tsx`
  - 长按 InlineMark 标注时弹出反馈选项
  - 提交时从 sceneData 构造 context_json
  - _Requirement: 2_

- [ ] B3.3 修改 `client/src/components/AnalysisCard/index.tsx`
  - 展开状态下右上角增加反馈图标
  - 点击后弹出 AnnotationFeedback 组件
  - _Requirement: 2_

### B4. 词典反馈

- [ ] B4.1 新建 `client/src/components/DictionaryFeedback/index.tsx`
  - 词典负面反馈选项浮层
  - 仅负面选项：释义错误、释义缺失、词性标注有误、音标有误、例句不当、其他
  - 可选文本输入
  - _Requirement: 4_

- [ ] B4.2 修改 `client/src/components/WordPopup/index.tsx`
  - 底部操作栏改为三按钮：[收藏] [反馈] [记入生词本]
  - 新增 `onFeedback` prop
  - 点击"反馈"弹出 DictionaryFeedback
  - 提交时构造 context_json（word, phonetic, meaning, dict_source, dict_entry_id, sentence）
  - _Requirement: 4_

### B5. 应用功能反馈页

- [ ] B5.1 新建 `client/src/pages/feedback/index.tsx`
  - 反馈分类选择（6 个 chip）
  - 问题描述文本框（必填）
  - 提交按钮
  - 底部"我的反馈"入口
  - 不收集联系方式
  - _Requirement: 3_

- [ ] B5.2 新建 `client/src/pages/feedback/my-feedback.tsx`
  - 反馈列表（按时间倒序）
  - 每项：反馈类型、内容预览、状态标签、提交时间
  - 已采纳显示奖励积分徽标
  - 游标分页加载
  - _Requirement: 7_

- [ ] B5.3 修改 `client/src/app.config.ts`
  - 注册 `pages/feedback/index` 和 `pages/feedback/my-feedback`
  - 注册 `pages/credit-detail/index`
  - _Requirement: 3, 6, 7_

### B6. 积分明细页

- [ ] B6.1 新建 `client/src/pages/credit-detail/index.tsx`
  - 顶部摘要：当前可用（每日常规 + 奖励）
  - 流水列表（按时间倒序，按日期分组）
  - 每条流水：图标 + 类型标签 + 积分变动（颜色区分）+ 描述 + 余额 + 时间
  - entry_type 中文映射与颜色
  - 滚动加载更多（游标分页）
  - _Requirement: 6_

- [ ] B6.2 修改 `client/src/pages/profile/index.tsx`
  - 额度明细区域增加点击跳转（navigateTo credit-detail）
  - 新增"意见反馈"菜单项（navigateTo feedback）
  - 展示 daily_used_points（利用已有 API 字段）
  - _Requirement: 3, 6_

---

## Phase 3 — 验证与收尾

### C1. 编译检查

- [ ] C1.1 Python 后端编译检查
  - schema / route / service 编译通过
  - _Requirement: 1, 2, 3, 4, 5, 6, 7, 8_

- [ ] C1.2 TypeScript 前端编译检查
  - `tsc --noEmit` 通过
  - _Requirement: 1, 2, 3, 4, 6, 7_

### C2. 手工验证链路

- [ ] C2.1 结果页 👍👎 → 数据库有记录
  - _Requirement: 1_

- [ ] C2.2 长按标注 → 反馈选项 → 提交成功
  - _Requirement: 2_

- [ ] C2.3 AnalysisCard 反馈图标 → 提交成功
  - _Requirement: 2_

- [ ] C2.4 WordPopup 反馈按钮 → 词典负面反馈 → 提交成功
  - _Requirement: 4_

- [ ] C2.5 应用功能反馈页 → 提交 → 我的反馈列表可见
  - _Requirement: 3, 7_

- [ ] C2.6 积分明细页 → 显示 analysis_deduct / feedback_reward / daily_grant
  - _Requirement: 6_

- [ ] C2.7 内部 API 标记采纳 → 积分到账 → 积分明细可见
  - _Requirement: 5, 6_

---

## 后续预留功能（不在本次范围）

| 功能 | 预留方式 | 预计优先级 |
|------|---------|-----------|
| 微信小程序云后台集成 | 内部管理 API 已预留，云后台直接消费 | P1 |
| AI 智能标签分类 | context_json GIN 索引已建，后续可加 tags 字段 | P2 |
| 反馈频率限制 | API 层可加每日上限（如 50 条/天） | P2 |
| RAG 数据提取工具 | rag_harvested 字段已预留，后续写脚本批量提取 | P2 |
| 词典反馈自动修正 | dictionary 反馈数据可驱动词典数据修正流程 | P3 |

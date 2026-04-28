# Code Review Notes

> **审查更新：2026-04-27**
> 原始审查结论"反馈机制完全缺失"已过时。当前反馈系统已全面实现（~95%），后端 API + 数据库 + 前端组件/页面均已落地。本文件已更新为当前状态。

## Findings

### 1. 反馈系统已全面实现

严重程度：信息（原为"高"）

当前项目中反馈系统已完整落地：

- ✅ `feedback` 数据库表 + `user_credit_ledger` entry_type 扩展（含 `feedback_reward`）
- ✅ 用户侧 API：`POST /feedback`（upsert 语义）、`GET /feedback`、`DELETE /feedback/{id}`
- ✅ 内部管理 API：`PATCH /internal/feedback/{id}/status`、`POST /internal/feedback/{id}/reward`、`GET /internal/feedback/stats`（API Key 认证）
- ✅ `grant_bonus_credits()` 函数已实现（credit_service.py）
- ✅ 积分明细 API：`GET /me/credit/ledger`
- ✅ FeedbackWidget 组件（结果页 👍👎 + 负面选项面板）
- ✅ AnnotationFeedback 组件（批注级反馈）
- ✅ DictionaryFeedback 组件（词典反馈，仅负面选项）
- ✅ 应用功能反馈页（`packageC/feedback/index`）+ 我的反馈页（`packageC/feedback/my-feedback`）
- ✅ 积分明细页（`packageA/credit-detail/index`）

涉及文件：

- [server/app/api/routes/feedback.py](../../server/app/api/routes/feedback.py)
- [server/app/api/routes/internal_feedback.py](../../server/app/api/routes/internal_feedback.py)
- [server/app/services/feedback/service.py](../../server/app/services/feedback/service.py)
- [server/app/services/analysis/credit_service.py](../../server/app/services/analysis/credit_service.py)
- [client/src/components/FeedbackWidget/index.tsx](../../client/src/components/FeedbackWidget/index.tsx)
- [client/src/components/AnnotationFeedback/index.tsx](../../client/src/components/AnnotationFeedback/index.tsx)
- [client/src/components/DictionaryFeedback/index.tsx](../../client/src/components/DictionaryFeedback/index.tsx)
- [client/src/packageC/feedback/index.tsx](../../client/src/packageC/feedback/index.tsx)
- [client/src/packageC/feedback/my-feedback.tsx](../../client/src/packageC/feedback/my-feedback.tsx)
- [client/src/packageA/credit-detail/index.tsx](../../client/src/packageA/credit-detail/index.tsx)

### 2. 积分展示已补全

严重程度：信息（原为"中"）

积分展示的原始问题已解决：

- ✅ 积分明细页已实现，按日期分组展示流水
- ✅ 额度区域可点击跳转明细页
- ✅ 支持的流水类型：分析扣减、反馈奖励、每日发放、奖励到账、积分退回、管理员调整

涉及文件：

- [client/src/packageA/credit-detail/index.tsx](../../client/src/packageA/credit-detail/index.tsx)
- [server/app/api/routes/quota.py](../../server/app/api/routes/quota.py)

### 3. bonus_points 发放机制已实现

严重程度：信息（原为"中"）

`grant_bonus_credits()` 已在 `credit_service.py` 中完整实现：

- ✅ 支持 `feedback_reward` entry_type
- ✅ task_id=NULL、bucket_type=bonus、事务内完成
- ✅ 内部管理 API `/internal/feedback/{id}/reward` 可触发发放

涉及文件：

- [server/app/services/analysis/credit_service.py](../../server/app/services/analysis/credit_service.py)

### 4. 标注标识体系已复用

严重程度：信息（正面发现，已验证）

标注级反馈已使用 `_stable_id()` 生成的确定性 ID 作为 `target_id`：

- ✅ InlineMark 和 SentenceEntry 的 `id` 可直接用作反馈目标
- ✅ AnnotationFeedback 组件已集成到 ParagraphBlock 和 AnalysisCard

### 5. 微信小程序合规已遵循

严重程度：信息（合规，已遵循）

反馈功能已遵循合规要求：

- ✅ 不收集任何联系方式
- ✅ 反馈采纳后静音发放积分，不推送通知
- ✅ 积分明细页作为"静音通知"载体

### 6. 待确认项

严重程度：低

- 每日重置时是否写入 `daily_grant` ledger 记录（当前 `check_quota` 只更新 `daily_used_points=0`，未见写入 ledger）
- Profile 页额度区域是否已展示 `daily_used_points` 完整视图

## Architectural Direction

### Current foundations (updated)

- ✅ `feedback` 表单表统一设计，`feedback_scope` 区分四个场景
- ✅ 标注 ID 体系（`_stable_id()`）为批注级反馈提供天然目标标识
- ✅ `user_credit_ledger` 表结构完整，积分明细查询已实现
- ✅ `context_json` JSONB 存储上下文快照
- ✅ 内部管理 API 供云后台消费，不在前端暴露管理界面
- ✅ Upsert 语义（UNIQUE 约束 `(user_id, target_id, feedback_type)` 冲突时更新）

### Remaining work

- 确认每日重置时 `daily_grant` ledger 记录是否需要写入
- 确认 Profile 页额度展示完整性

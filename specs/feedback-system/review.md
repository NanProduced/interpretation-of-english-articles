# Code Review Notes

## Findings

### 1. 反馈机制完全缺失

严重程度：高

当前项目中不存在任何用户反馈或评分机制：

- 无结果评分/点赞/踩的 UI 或 API
- 无分析质量反馈表单
- 无 `feedback` 或 `rating` 相关的数据库表
- 无后端 feedback API 路由

涉及文件：

- 无（空白区域）

结论：

- 这是当前项目的功能空白，需要从零构建
- 文档 [mini-program-integration-and-ux-design.md](../../docs/architecture/mini-program-integration-and-ux-design.md) 中已将"增加用户反馈入口"列为未来规划项

### 2. 积分展示信息不完整

严重程度：中

个人配置页的额度展示存在以下问题：

- 前端未使用 API 已返回的 `daily_used_points` 字段
- 无法看到"总额度/已用/剩余"的完整视图
- 额度区域无点击交互，无法跳转详情
- 没有任何消费/充值历史记录展示

涉及文件：

- [client/src/pages/profile/index.tsx](../../client/src/pages/profile/index.tsx) — 仅展示 remaining + bonus 两个数字
- [server/app/api/routes/quota.py](../../server/app/api/routes/quota.py) — API 已返回 daily_used_points 但前端未消费
- [server/app/services/analysis/credit_service.py](../../server/app/services/analysis/credit_service.py) — 只有 deduct_credits 写入 ledger，无读取接口

结论：

- 积分明细页是必要的补充，不仅承载反馈奖励可见性，也补全了现有积分展示的缺失
- `user_credit_ledger` 表已有 `idx_credit_ledger_user_created` 索引，可直接用于分页查询

### 3. bonus_points 发放机制缺失

严重程度：中

`user_credit_accounts.bonus_points` 和 `user_credit_ledger` 的 `bonus_grant` / `manual_adjust` entry_type 在 schema 中定义了，但代码中无任何发放入口：

- `credit_service.py` 只有 `deduct_credits()` 写入 `analysis_deduct`
- 没有 `grant_bonus_credits()` 或类似函数
- bonus_points 只会被扣减（daily_free 用完后从 bonus 扣），但从未被增加

涉及文件：

- [server/app/services/analysis/credit_service.py](../../server/app/services/analysis/credit_service.py)
- [server/db/migrations/0001_initial_schema.sql](../../server/db/migrations/0001_initial_schema.sql) — entry_type CHECK 约束

结论：

- 反馈奖励需要新增 `grant_bonus_credits()` 函数
- 需要扩展 `entry_type` CHECK 约束，新增 `feedback_reward`

### 4. WordPopup 底部操作栏可扩展

严重程度：低

WordPopup full 模式底部操作栏当前有两个按钮（收藏、记入生词本），各占 `flex: 1`。新增"反馈"按钮需要调整布局为三按钮平铺。

涉及文件：

- [client/src/components/WordPopup/index.tsx](../../client/src/components/WordPopup/index.tsx) — footer-actions 区域

结论：

- 三按钮平铺（收藏 | 反馈 | 记入生词本）是可行的，每个 `flex: 1`
- "反馈"使用 `secondary` 样式，与"收藏"风格一致
- 需要新增 `onFeedback` prop

### 5. 标注标识体系可复用

严重程度：低（正面发现）

每个 InlineMark 和 SentenceEntry 都有后端生成的确定性 `id`（`{prefix}_{sha1[:12]}`），可直接用作反馈的 `target_id`：

- Learning 模式：`im_*`（inline mark）、`se_*`（sentence entry）
- Academic 模式：`aim_*`（academic inline mark）、`ase_*`（academic sentence entry）
- GrammarNote 的 inline_mark 和 sentence_entry 共享相同 digest 但前缀不同，可关联

涉及文件：

- [server/app/services/analysis/postprocess/projection.py](../../server/app/services/analysis/postprocess/projection.py) — `_stable_id()` 函数

结论：

- 标注级反馈可直接使用 `mark.id` / `sentence_entry.id` 作为 `target_id`
- 不需要额外生成标识符

### 6. 微信小程序联系方式收集合规风险

严重程度：高（合规）

根据调研：

- 《微信小程序平台运营规范》第十五条：不得要求用户输入个人信息才可使用功能
- 《关于小程序收集用户手机号行为的规范》：非必要场景不得强制收集手机号
- 多款小程序因收集联系方式被通报违规

结论：

- 反馈功能中不收集任何联系方式（手机号、邮箱、微信号等）
- 反馈采纳通知不使用微信订阅消息推送
- 信息下沉到小程序内部（积分明细页），用户主动查看时自然发现

## Architectural Direction

### Good current foundations

- `favorite_records` 表的 `target_type` + `target_key` 模式可直接复用于反馈表
- 标注 ID 体系（`_stable_id()`）为批注级反馈提供了天然的目标标识
- `user_credit_ledger` 表结构完整，已有索引，可直接用于积分明细查询
- `context_json` JSONB 模式在项目中广泛使用（`settings_json`、`payload_json` 等），团队熟悉

### Design direction

- 单表统一设计（`feedback` 表），用 `feedback_scope` 区分四个场景
- JSONB `context_json` 存储上下文快照，避免后续数据变更导致反馈无法关联
- 积分明细页作为反馈奖励的"静音通知"载体，一举两得
- 内部管理 API 供云后台消费，不在前端暴露管理界面

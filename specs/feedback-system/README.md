# Feedback System

建议 agent 按以下顺序阅读并执行：

1. [requirements.md](requirements.md)
2. [review.md](review.md)
3. [design.md](design.md)
4. [tasks.md](tasks.md)

执行原则：

- 先做 Phase 1：数据库、后端 API、积分明细
- 再做 Phase 2：前端反馈组件与页面
- 最后做 Phase 3：内部管理 API 与验证
- 词典反馈（feedback_scope='dictionary'）仅收集负面反馈
- 不收集用户联系方式，不使用微信订阅消息推送
- 不引入 AI 分类能力，feedback_type 按场景硬编码枚举
- 管理后台后续用微信小程序云开发-云后台实现，本次仅预留管理字段

约束条件：

- 项目尚在开发阶段，不需要数据迁移，可直接新建表
- 遵循现有代码风格（UUID 主键、JSONB 扩展、CHECK 约束枚举）
- feedback 表与 favorite_records 采用相同的 target_type/target_key 模式
- user_credit_ledger 的 entry_type 扩展需 ALTER CHECK 约束

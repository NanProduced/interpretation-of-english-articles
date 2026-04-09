# 文档说明

`docs/` 只保留当前阶段直接指导开发的少量主线文档，不作为 Notion 的镜像备份。

当前文档主要服务于 Claread透读 的产品、workflow、架构与运行维护协作。

当前仅维护四类文档：

- 产品共识：明确做什么、不做什么、核心用户和主链路
- Workflow 共识：明确后端解读流程的业务骨架与当前未定项
- 小程序技术边界：明确哪些能力可以由小程序原生或微信生态完成，哪些必须由我们自己实现
- 运行与调试规范：明确模型配置、观测、实验与联调方式

`docs/architecture/` 当前只保留 5 份主文档，不再继续平行扩张：

- 主文档：[小程序联调与用户体验开发设计文档](./architecture/mini-program-integration-and-ux-design.md)
- 词典执行文档：[TECD3 本地词典接入方案](./architecture/tecd3-local-dictionary-integration.md)
- 边界结论文档：[微信小程序技术边界](./architecture/mini-program-boundaries.md)
- 上线与部署文档：[小程序正式上线架构与部署方案](./architecture/production-architecture-and-deployment-plan.md)
- 每日精读文档：[每日精读模块设计文档](./architecture/daily-reader-module-design.md)

维护原则：

- 只迁入已经收敛、会直接影响开发决策的内容
- 只写当前版本的有效共识，不保存大量发散调研
- 文档数量控制在必要最小，避免后期文档爆炸导致业务逻辑漂移
- 以 Notion 为源头长文档，仓库内以提炼版为准
- 已实现且不再需要路线指导的内容，优先回写到主文档的“当前结论 / 状态跟踪”，不再拆独立新文档

当前文档列表：

- [产品需求摘要](./product/prd-summary.md)
- [Workflow V0 架构回顾与问题诊断报告](./workflow/v0/v0-retrospective-report.md)
- [Workflow V1 设计草案](./workflow/v1/workflow-v1-design.md)
- [Workflow V3 设计与重构文档（当前重构参考）](./workflow/v3/workflow-v3-design.md)
- [Workflow V2.1 改造设计稿（上一版主线参考）](./workflow/v2/v2-1-refactor-design.md)
- [Workflow V2 统一设计文档（归档）](./workflow/v2/archive/v2-unified-design.md)
- [微信小程序技术边界](./architecture/mini-program-boundaries.md)
- [小程序联调与用户体验开发设计文档](./architecture/mini-program-integration-and-ux-design.md)
  - 包含当前结果页状态映射、前后端边界和 workflow 之外的小程序开发路线图
- [TECD3 本地词典接入方案](./architecture/tecd3-local-dictionary-integration.md)
  - 覆盖 `/dict` 切换到 `TECD3` 离线词典导入、前后端协议、单词卡片字段、底部详情弹层与 PostgreSQL 真源方案
- [小程序正式上线架构与部署方案](./architecture/production-architecture-and-deployment-plan.md)
  - 覆盖微信登录、云端资产、PostgreSQL、缓存分层、`TECD3` 词典真源、analyze 任务中心、幂等/单任务控制与额度账本
  - 微信登录已实现：Session 管理（随机 Token + PostgreSQL）、`/auth/wechat/login`、`/auth/session/logout`、`/auth/session/me`
- [每日精读模块设计文档](./architecture/daily-reader-module-design.md)
  - 覆盖每日精读页面的信息架构、专用 workflow、正文轻量辅助、文末全篇解析与内容生产链路
- [LangSmith 使用规范](./operations/langsmith-usage.md)
- [回归集使用说明](./operations/regression-suite-usage.md)
- [模型配置教程](./operations/model-configuration-usage.md)

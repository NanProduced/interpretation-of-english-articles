# 文档说明

`docs/` 只保留当前阶段直接指导开发的少量主线文档，不作为 Notion 的镜像备份。

当前文档主要服务于 Claread透读 的产品、workflow、架构与运行维护协作。

当前仅维护四类文档：

- 产品共识：明确做什么、不做什么、核心用户和主链路
- Workflow 共识：明确后端解读流程的业务骨架与当前未定项
- 小程序技术边界：明确哪些能力可以由小程序原生或微信生态完成，哪些必须由我们自己实现
- 运行与调试规范：明确模型配置、观测、实验与联调方式

维护原则：

- 只迁入已经收敛、会直接影响开发决策的内容
- 只写当前版本的有效共识，不保存大量发散调研
- 文档数量控制在必要最小，避免后期文档爆炸导致业务逻辑漂移
- 以 Notion 为源头长文档，仓库内以提炼版为准

当前文档列表：

- [产品需求摘要](./product/prd-summary.md)
- [Workflow V0 架构回顾与问题诊断报告](./workflow/v0/v0-retrospective-report.md)
- [Workflow V1 设计草案](./workflow/v1/workflow-v1-design.md)
- [Workflow 主设计稿（当前唯一参考）](./workflow/v2/v2-1-refactor-design.md)
- [Workflow V2 统一设计文档（归档）](./workflow/v2/archive/v2-unified-design.md)
- [微信小程序技术边界](./architecture/mini-program-boundaries.md)
- [LangSmith 使用规范](./operations/langsmith-usage.md)
- [回归集使用说明](./operations/regression-suite-usage.md)
- [模型配置教程](./operations/model-configuration-usage.md)

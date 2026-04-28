# 文档说明

`docs/` 只保留当前阶段直接指导开发的少量主线文档，不作为 Notion 的镜像备份。

当前文档主要服务于 Claread透读 的产品、workflow、架构与运行维护协作。

## 文档分类规则

本目录文档分为四类：

| 分类 | 含义 | 索引位置 |
|------|------|----------|
| 当前真相源 | 直接指导当前开发、联调、部署和运维 | 下方"当前真相源文档" |
| 模块级长期设计 | 已收敛但尚未实施，或独立模块的设计文档 | 下方"模块级长期设计文档" |
| 历史参考 | 保留阶段性设计、复盘和归档，不再作为当前实现依据 | 下方"历史参考文档" |
| 临时开发指引 | 开发 handoff / 实施步骤文档，使命完成后建议删除 | 下方"临时开发指引" |

维护原则：

- 只迁入已经收敛、会直接影响开发决策的内容
- 只写当前版本的有效共识，不保存大量发散调研
- 文档数量控制在必要最小，避免后期文档爆炸导致业务逻辑漂移
- 已实现且不再需要路线指导的内容，优先回写到主文档的"当前结论 / 状态跟踪"，不再拆独立新文档
- 新增文档前，先判断是否能回写到已有主文档

## 当前真相源文档

### 架构

- [Claread 透读架构决策记录](./architecture/ARCHITECTURE.md)
  - 技术栈选型、数据模型、认证登录、积分配额、异步任务中心、词典查询策略、前端状态管理、ID 契约、离线优先同步策略
- [词典服务架构与查询策略](./architecture/dictionary-service-architecture.md)
  - TECD3 离线导入、PostgreSQL 真源、查询策略、缓存策略、dict_* 表保护规则
- [每日精读 Specs](../specs/daily-reader/)
  - 每日精读页面形态、专用 workflow、数据结构、内容生产链路
- [小程序联调与用户体验设计文档](./architecture/mini-program-integration-and-ux-design.md)
  - 用户主链路、结果页状态映射、前后端边界、用户资产管理、微信平台能力接入

### Workflow

- [Workflow V3 设计与重构文档](./workflow/v3/workflow-v3-design.md)
  - V3 架构核心设计：语义层与渲染层分离、多 agent 拆分、projection 机制
- [差异化输出执行架构设计](./workflow/v3/differentiated-output-strategy-design.md)
  - GoalExecutionPlan 运行时真相源、三类 reading_goal 执行差异、academic v1 当前状态
- [输入预处理重构设计](./workflow/v3/prepare-input-preprocessing-redesign.md)
  - prepare_input 重构：spaCy 句切分、语言检测、快速退出机制

### 产品

- [产品需求摘要](./product/prd-summary.md)
  - 核心定位、目标用户、产品边界、主链路定义

### 运维

- [LangSmith 使用规范](./operations/langsmith-usage.md)
- [回归集使用说明](./operations/regression-suite-usage.md)
- [模型配置教程](./operations/model-configuration-usage.md)

## 模块级长期设计文档

以下文档已收敛但尚未实施，或属于独立模块的前瞻性设计：

- [Grammar RAG 设计文档](./architecture/grammar-rag-design.md)
  - grammar_agent 的 RAG few-shot 检索增强，尚未实施
- [Scholarly Achievement System](./product/scholarly_achievement_system.md)
  - 勋章进化系统设计
- [学术阅读差异化策略](./differentiated/academic_reading_differentiation.md)
  - 第 12 节是 academic v1 唯一实现规范；第 1-6 节是研究依据；第 7-11 节已废弃
- [高考差异化策略](./differentiated/exam_gaokao_differentiation.md)
- [CET 差异化策略](./differentiated/exam_cet_differentiation.md)
- [考研差异化策略](./differentiated/exam_kaoyan_differentiation.md)
- [雅思托福差异化策略](./differentiated/exam_ielts_toefl_differentiation.md)

## 历史参考文档

以下文档保留作为历史参考，不再作为当前实现依据：

- [Workflow V0 架构回顾与问题诊断报告](./workflow/v0/v0-retrospective-report.md)
- [Workflow V1 设计草案](./workflow/v1/workflow-v1-design.md)
- [Workflow V2.1 改造设计稿](./workflow/v2/v2-1-refactor-design.md)
  - 仍被 server/README.md 引用为 v2.1 现状参考，但新开发以 V3 为准
- [Workflow V2 统一设计文档（归档）](./workflow/v2/archive/v2-unified-design.md)
- [日常阅读差异化研究参考](./differentiated/daily_reading_differentiation.md)
  - 纯语言学/教学学研究参考，不是实现规范
- [TEM 差异化分析](./differentiated/exam_tem_differentiation.md)
  - 决策记录：TEM variant 已推迟为方案 B，不合并入 kaoyan

## 临时开发指引

以下文档是开发 handoff / 实施步骤文档，结论已被主文档吸收，不再列入当前有效文档：

- [Release + RAG Readiness 临时进度跟踪](./operations/release-rag-progress-tracker.tmp.md)
  - 临时开发指引。本轮用于协调上线阻断项收口、RAG readiness 和测试补强；完成后删除
- [用户资产层重构开发指引](./architecture/user-assets-sync-refactor-guide.md)
  - 临时开发指引。ID 契约、离线优先同步策略、Vocabulary 接口语义等结论已吸收到 ARCHITECTURE.md 第 7.4-7.6 节
- [academic v1 开发对照文档](./differentiated/academic_v1_dev_handoff.md)
  - 临时开发指引。权威来源以 academic_reading_differentiation.md 第 12 节为准

## 已被替代的文档引用

以下文件名曾在旧版索引中引用，但实际不存在或已被替代：

| 旧引用名 | 当前状态 |
|----------|----------|
| `tecd3-local-dictionary-integration.md` | 不存在。内容已整合到 [dictionary-service-architecture.md](./architecture/dictionary-service-architecture.md) |
| `mini-program-boundaries.md` | 不存在。小程序技术边界结论已整合到 [mini-program-integration-and-ux-design.md](./architecture/mini-program-integration-and-ux-design.md) |
| `production-architecture-and-deployment-plan.md` | 不存在。上线架构相关决策已整合到 [ARCHITECTURE.md](./architecture/ARCHITECTURE.md) |

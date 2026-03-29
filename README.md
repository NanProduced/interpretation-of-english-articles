# AI 英语文章解读小程序

本仓库是一个以 agentic workflow 为核心的微信小程序父工作区，面向有一定英语基础的用户，帮助他们更高效地读懂英文文章。

这个产品的重点不是通用翻译，而是围绕英文阅读场景，输出稳定、结构化、可交互的解读结果。核心闭环是：

1. 用户提交英文文章。
2. 后端 Workflow 执行结构化解读。
3. 前端将结果渲染为分层、可交互的阅读辅助页面。

首期核心解读维度包括：

- 重点词汇标注与语境义
- 语法分析
- 长难句拆解
- 高质量翻译

后续可扩展能力包括：

- 篇章级分析
- OCR 输入
- RAG 富化
- 生词收藏与历史记录

## 仓库结构

```text
.
├── client/                  # 微信小程序前端（Taro + React + TypeScript）
├── server/                  # 后端工作流服务（FastAPI + LangGraph + PydanticAI）
├── docs/                    # 本地项目参考文档与实施说明
└── .serena/                 # Serena 项目配置与简版记忆
```

## 推荐技术栈

### 前端

- Taro 3
- React
- TypeScript
- Sass
- Zustand

### 后端

- Python 3.11+
- FastAPI
- LangGraph
- PydanticAI
- Pydantic v2
- HTTPX
- Uvicorn

### 平台与服务

- 微信小程序开发者工具
- 微信云开发 / 云托管
- 大模型服务商：优先 Qwen，后续可加 fallback
- 内容安全：`msgSecCheck`

## 本地开发工具

开始开发前，建议先安装：

- Node.js 20 LTS
- pnpm
- Python 3.11 及以上
- uv
- Git
- VS Code
- 微信小程序开发者工具

可选但推荐：

- Docker Desktop
- Postman 或 Insomnia

## 当前状态

当前仓库已经包含：

- 项目基础目录骨架
- 初始本地参考文档
- Serena 项目配置与简版记忆
- 前后端占位入口文件
- 本地 Codex / RTK 支持文件

## 开发策略

本项目应按标准前后端分离方式开发：

- `client/` 负责页面、交互、结果渲染。
- `server/` 负责 AI workflow 编排、模型调用、结构化校验和业务 API。

微信小程序本身不是后端运行环境，因此模型调用、API Key、Workflow、未来的 RAG 都必须放在后端。

## 环境约定

当前约定采用双环境结构：

- `client/` 使用 `pnpm`
- `server/` 使用 `uv + .venv`

后端虚拟环境固定放在 `server/.venv/`，不要与全局 Python 或前端依赖混用。

## 建议的里程碑顺序

1. 先完成后端输出 Schema 和最小 Workflow 原型。
2. 再完成前端输入页和最小结果页。
3. 打通前后端联调。
4. 稳定质量、延迟和结果渲染。
5. 再逐步增加历史记录、生词收藏和高级能力。

## 本地参考文档

- [文档说明](./docs/README.md)
- [产品需求摘要](./docs/product/prd-summary.md)
- [初版用户配置草案 v0.1.0-draft](./docs/product/user-config-v0-draft.md)
- [Workflow 摘要](./docs/workflow/workflow-overview.md)
- [输入规范与预处理 Schema 草案 v0.1.0-draft](./docs/workflow/preprocess-schema-v0-draft.md)
- [输出 Schema 草案 v0.1.0-draft](./docs/workflow/schema-v0-draft.md)
- [微信小程序技术边界](./docs/architecture/mini-program-boundaries.md)
- [LangSmith 使用规范](./docs/operations/langsmith-usage.md)
- [前端说明](./client/README.md)
- [后端说明](./server/README.md)

## Serena

仓库内包含本地 `.serena/` 目录，用于保存项目配置和从 Notion 主线文档提炼出来的简版记忆。

## RTK / Codex 本地支持

仓库内还包含通过 RTK 初始化生成的本地支持文件：

- `AGENTS.md`
- `RTK.md`

它们用于定义本项目的本地指令入口以及 shell 命令的 RTK 使用约定。

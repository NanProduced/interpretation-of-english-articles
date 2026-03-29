# 后端说明

这里是 AI 解读 Workflow 后端服务工作区，计划使用 FastAPI + LangGraph + PydanticAI 开发。

## 推荐技术栈

- Python 3.11+
- FastAPI
- LangGraph
- PydanticAI
- Pydantic v2
- HTTPX
- Uvicorn

## 环境约定

- 后端使用独立虚拟环境，不与系统 Python 或前端依赖混用
- 虚拟环境固定放在 `server/.venv/`
- 依赖管理使用 `uv`
- 依赖声明文件为 `server/pyproject.toml`
- 锁文件为 `server/uv.lock`

推荐的日常命令：

```bash
cd server
uv sync
uv run uvicorn app.main:app --reload
```

## 计划职责

- 内容安全编排
- Workflow 执行
- 结构化 JSON 输出
- 输出校验与重试控制
- 数据持久化与后续富化扩展

## 当前初始化内容

- 最小 FastAPI 应用入口
- 健康检查路由
- 基础设置模块
- `uv` 项目配置

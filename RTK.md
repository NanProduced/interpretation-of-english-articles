# RTK - Rust Token Killer（Codex CLI）

用途：对常见 shell 命令输出做压缩、去噪、聚合和裁剪，减少 LLM 上下文消耗。

项目约定：**所有 shell 命令默认都要加 `rtk` 前缀。**

参考：
- [rtk-ai/rtk 仓库](https://github.com/rtk-ai/rtk)
- [README](https://github.com/rtk-ai/rtk/blob/master/README.md)

## 基础规则

优先这样写：

```bash
rtk git status
rtk pytest -q
rtk powershell.exe -Command "Get-ChildItem"
```

不要默认直接跑原始命令，除非你明确需要完整原始输出。

## 在本仓库里优先使用的省 token 命令

### 1. 文件与目录

优先用于看目录、读文件、找文件、看 diff。

```bash
rtk ls .
rtk read RTK.md
rtk read server/app/workflow/preprocess.py
rtk read server/app/workflow/preprocess.py -l aggressive
rtk smart server/app/workflow/analyze.py
rtk find "*.py" server
rtk diff docs/workflow/schema-v0-draft.md server/app/schemas/analysis.py
```

使用建议：
- 读大文件时，优先 `rtk read`
- 只想快速理解文件结构时，优先 `rtk smart`
- 只想看签名和骨架时，用 `rtk read -l aggressive`

### 2. 搜索

用于替代直接把大量 `rg` 结果塞进上下文。

```bash
rtk grep "run_preprocess_v0" server
rtk grep "schema_version" docs
rtk grep "LANGSMITH_" server
```

使用建议：
- 大范围搜索优先 `rtk grep`
- 只有在需要精确保留原始 `rg` 输出格式时，才考虑 `rtk proxy rg ...`

### 3. Git

```bash
rtk git status
rtk git diff
rtk git log -n 10
rtk git push
```

使用建议：
- 看工作区状态、diff、最近提交时优先走 `rtk git ...`
- 提交、推送等成功/失败类反馈很适合用 RTK 压缩

### 4. 测试

这是当前仓库最值得长期使用的一组命令。

```bash
rtk pytest
rtk pytest tests/test_preprocess_workflow.py
rtk test uv run pytest
rtk test uv run pytest tests/test_preprocess_workflow.py
```

使用建议：
- 跑测试默认优先 `rtk pytest`
- 当原始命令比较长时，可用 `rtk test <原始测试命令>`
- 失败输出需要聚焦时，优先 `rtk test ...`

### 5. 构建与静态检查

```bash
rtk err pnpm run build
rtk err pnpm exec tsc -p tsconfig.json --noEmit
rtk err uv run ruff check
rtk err uv run python -m compileall server
```

使用建议：
- 构建、类型检查、lint 默认优先 `rtk err ...`
- 目标是只看错误和 warning，不看大段成功日志

### 6. JSON、日志与接口输出

这组命令适合当前 AI workflow 项目。

```bash
rtk json server/.env.example
rtk log server.log
rtk summary powershell.exe -Command "Invoke-RestMethod -Uri http://127.0.0.1:8000/preprocess -Method Post"
rtk curl http://127.0.0.1:8000/docs
```

使用建议：
- 大 JSON 优先 `rtk json`
- 长日志优先 `rtk log`
- 长命令输出想先看摘要时，用 `rtk summary ...`

### 7. 统计与漏用检查

```bash
rtk gain
rtk gain --history
rtk gain --daily
rtk discover
rtk session
```

使用建议：
- `rtk gain`：看节省统计
- `rtk discover`：找当前还有哪些命令没被 RTK 覆盖
- `rtk session`：看最近会话里的 RTK 采用情况

## 全局参数

```bash
rtk -u git status
rtk --ultra-compact pytest
rtk -v pytest
```

建议：
- 默认保持普通模式
- 输出仍偏长时再用 `-u` / `--ultra-compact`
- 排查 RTK 行为时才加 `-v`

## 什么时候用 `rtk proxy`

`rtk proxy` 表示：
- 仍然通过 RTK 追踪这次命令
- 但不对输出做压缩过滤

适合这些场景：

```bash
rtk proxy uv run uvicorn app.main:app --reload
rtk proxy uv run pytest tests/test_preprocess_workflow.py
rtk proxy powershell.exe -Command "Invoke-RestMethod -Uri http://127.0.0.1:8000/preprocess -Method Post -ContentType 'application/json' -Body '{...}'"
```

使用建议：
- 启动服务、需要完整实时输出时用 `rtk proxy`
- 需要完整原始测试堆栈时用 `rtk proxy`
- 默认不要滥用，否则会失去压缩收益

## 当前仓库的推荐习惯

### 默认优先级

1. `rtk read` / `rtk smart`
2. `rtk grep`
3. `rtk git ...`
4. `rtk pytest` / `rtk test ...`
5. `rtk err ...`
6. 只有必须保留原始输出时，才用 `rtk proxy ...`

### 对应替换关系

```bash
cat file.py                    -> rtk read file.py
rg "pattern" server            -> rtk grep "pattern" server
git status                     -> rtk git status
git diff                       -> rtk git diff
pytest                         -> rtk pytest
pnpm exec tsc --noEmit         -> rtk err pnpm exec tsc --noEmit
uv run uvicorn ... --reload    -> rtk proxy uv run uvicorn ... --reload
```

## 安装与验证

```bash
rtk --version
rtk gain
where.exe rtk
```

如果要给当前 AI 工具重新安装 hook：

```bash
rtk init -g --codex
```

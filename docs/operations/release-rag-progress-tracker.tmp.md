# Release + RAG Readiness 临时进度跟踪

> 临时文档。用于本轮上线阻断项收口与 Grammar RAG 接入前置准备。  
> 本轮完成后删除，不沉淀为长期架构文档。长期结论应回写到对应正式文档。

## 1. 本轮目标

本轮不是直接上线 RAG，也不是做大范围新功能。目标是：

1. 清零小程序 MVP 上线阻断项。
2. 补齐上线前必须有的基础页面与生产配置。
3. 完成 Grammar RAG Readiness Gate，让 RAG 后续可以作为后端内部增强灰度接入。
4. 保持前端分析协议稳定，不向小程序暴露 RAG 开关。
5. 补一批高价值测试，优先覆盖 Daily Reader、用户资产和 RAG fallback。

## 2. 协作规则

### 2.1 状态枚举

所有任务只能使用以下状态：

| 状态 | 含义 |
|------|------|
| `TODO` | 尚未开始 |
| `IN_PROGRESS` | 正在开发 |
| `BLOCKED` | 被外部条件阻塞，必须写清阻塞原因 |
| `REVIEW` | 已完成实现，等待他人 review 或验证 |
| `DONE` | 已验证完成 |
| `DEFERRED` | 本轮明确暂缓 |

### 2.2 更新规则

每个 agent 修改代码后，必须同步更新本文档对应任务行：

1. 更新 `状态`。
2. 更新 `最后更新`，格式为 `YYYY-MM-DD HH:mm`，使用 Asia/Shanghai 时间。
3. 在 `进展记录` 增加一条简短记录，包含改动摘要、验证命令、剩余风险。
4. 如果任务被阻塞，必须在 `阻塞/风险` 中写清楚需要谁决策或提供什么资源。
5. 不要删除他人进展记录，只能追加。

### 2.3 代码边界

| Agent | 主要责任 | 避免触碰 |
|-------|----------|----------|
| Claude | 后端主链路、生产配置、COS/CDN、RAG readiness 接口与 fallback | 前端 UI 大改、vocab-display-overhaul |
| GLM | 数据结构、seed 生成、测试补齐、Academic 闭环诊断 | 前端页面重构、生产配置最终决策 |
| Gemini | 小程序上线体验、Daily Reader 页面交互、协议/隐私/关于页面、分享卡片 | 后端 workflow 结构、RAG 外部服务接入 |

### 2.4 验证规则

每个任务至少写一个验证方式。优先使用：

| 区域 | 推荐验证 |
|------|----------|
| 前端 | `pnpm exec tsc -p tsconfig.json --noEmit` 或 `npm run build:weapp` |
| 后端 | `uv run pytest <相关测试> -q` |
| API | 本地 FastAPI 路由测试或 pytest 集成测试 |
| 文档/配置 | 明确列出检查文件和最终配置值 |

## 3. 里程碑

| 里程碑 | 目标 | 状态 | 完成标准 |
|--------|------|------|----------|
| M1 MVP 上线候选 | 清零红色上线阻断项 | TODO | API 地址、分享卡片、精读收藏/生词、封面 CDN、基础页面均完成并验证 |
| M2 RAG Readiness Gate | RAG 可插拔但默认关闭 | TODO | grammar RAG 配置开关、fallback、seed 数据、测试骨架完成 |
| M3 测试补强 | 覆盖高风险业务侧 | TODO | Daily Reader、用户资产、反馈/额度至少补齐关键路径测试 |

## 4. P0 上线阻断任务

| ID | 任务 | Owner | 状态 | 依赖 | 验收标准 | 最后更新 |
|----|------|-------|------|------|----------|----------|
| P0-01 | 修正开发/正式环境 API 地址配置 | Gemini | TODO | 生产 API 域名决策 | `env.ts` 不再使用占位值；dev/staging/prod 语义清晰；构建通过 | - |
| P0-02 | Daily Reader 分享卡片自定义封面 | Gemini | TODO | P0-04 的封面 URL 策略 | `daily-reader/index.tsx` 分享 `imageUrl` 使用稳定远程或 fallback 图片 | - |
| P0-03A | 精读页生词/收藏持久化后端契约确认 | Claude | TODO | 现有 vocabulary/favorites API | 明确 Daily Reader 调用现有 vocabulary/favorites API 所需字段；如后端缺口只补服务/API，不改前端页面 | - |
| P0-03B | 精读页生词/收藏持久化前端接入 | Gemini | TODO | P0-03A | `handleAddVocab` / `handleFavorite` 调用真实 API 或本地优先同步；失败有提示；重复点击幂等；不改后端 | - |
| P0-04 | 封面图从本地 static/covers 迁移到 COS+CDN | Claude | TODO | COS bucket/CDN 域名 | 后端保存并返回远程 cover URL；本地 static 仅作为 dev fallback | - |
| P0-05 | 用户协议与隐私政策页面 | Gemini | TODO | 正式文案或临时合规文案 | 个人中心可跳转；页面可返回；不再是 Toast 占位 | - |
| P0-06 | 关于我们页面 | Gemini | TODO | 产品基础信息 | 个人中心可跳转；页面内容完整；不再是 Toast 占位 | - |

## 5. P1 RAG Readiness 任务

| ID | 任务 | Owner | 状态 | 依赖 | 验收标准 | 最后更新 |
|----|------|-------|------|------|----------|----------|
| RAG-01 | 打通 grammar bundle 的 sentences 传递 | Claude | TODO | 无 | `build_grammar_bundle(plan, sentences=sentences_data)` 或等价实现；测试覆盖 baseline 不变 | - |
| RAG-02 | 增加 `GRAMMAR_RAG_ENABLED=false` 配置 | Claude | TODO | 无 | settings 和 `.env.example` 有配置；默认关闭；未配置不影响启动 | - |
| RAG-03 | 限定只有 grammar 可走 RAG | Claude | TODO | RAG-02 | vocabulary/translation 不因 `few_shot_mode=rag` 接入 RAG；行为有测试 | - |
| RAG-04 | `grammar_rag_service` fallback 骨架 | Claude | TODO | RAG-01, RAG-02 | 空结果、异常、低置信度均回 baseline；记录 fallback reason | - |
| RAG-05 | 静态 grammar examples 合法性审计 | GLM | TODO | 无 | `grammar.yaml` 中 `output_fragment` 均可解析为 JSON；类型只含 `grammar_note` / `sentence_analysis` | - |
| RAG-06 | 生成第一版 grammar seed JSONL | GLM | TODO | RAG-05 | 生成本地 seed 文件，字段包含 example_id/output_type/variant/tags/signals/retrieval_text | - |
| RAG-07 | `grammar_retrieval_hints.py` 轻量规则 | GLM | TODO | RAG-06 | 覆盖句长、逗号、that/which/who、句首 V-ing/V-ed、插入语等信号；有单测 | - |
| RAG-08 | prompt/debug 暴露 selection mode | Claude | TODO | RAG-04 | debug 输出包含 selection_mode、example_count、fallback_reason 预留字段 | - |

## 6. P1 测试补强任务

| ID | 任务 | Owner | 状态 | 依赖 | 验收标准 | 最后更新 |
|----|------|-------|------|------|----------|----------|
| T-01 | Daily Reader workflow/pipeline 关键路径测试 | GLM | TODO | 现有 pipeline 稳定 | 覆盖生成、发布、查询、失败状态至少一条关键路径 | - |
| T-02 | 用户资产 records/vocabulary/favorites 测试 | GLM | TODO | 现有服务接口 | 覆盖 upsert、list、delete、ID 语义和幂等行为 | - |
| T-03 | 反馈路由/服务测试 | GLM | TODO | 无 | 覆盖提交、列表、删除或状态更新关键路径 | - |
| T-04 | 额度/积分流水测试 | GLM | TODO | 无 | 覆盖 quota check、扣减/发放、ledger 查询关键路径 | - |

## 7. P2 暂缓任务

| ID | 任务 | 状态 | 暂缓原因 |
|----|------|------|----------|
| D-01 | vocab-display-overhaul | DEFERRED | 生词本改造影响面大，不是当前上线阻断项 |
| D-02 | 外部 Zilliz/Bailian RAG 正式接入 | DEFERRED | 需先完成 RAG Readiness Gate 和 seed/fallback |
| D-03 | 埋点 SDK 正式替换 | DEFERRED | 当前占位实现可支撑调用点稳定，正式 SDK 可上线前另排 |
| D-04 | Academic 深度优化 | DEFERRED | 先完成 API 闭环诊断，避免影响 learning 主链路 |

## 8. Academic 当前处理策略

Academic 拓扑已经有实现基础，但 API 闭环仍有 501/422 风险。本轮只做以下处理：

| ID | 任务 | Owner | 状态 | 验收标准 | 最后更新 |
|----|------|-------|------|----------|----------|
| A-01 | Academic API 闭环诊断报告 | GLM | TODO | 明确 `/analyze` 与 `/analysis-tasks` 对 academic 的实际失败点和最小修复路径 | - |
| A-02 | 前端 Academic 入口保护 | Gemini | TODO | 如果入口存在，隐藏或降级说明，避免用户触发 501/422 | - |

## 9. 进展记录

按时间倒序追加。格式：

```text
YYYY-MM-DD HH:mm | Agent | Task ID | 状态 | 摘要 | 验证 | 风险/下一步
```

记录：

- 2026-04-28 00:00 | Codex | INIT | TODO | 创建本轮临时进度跟踪文档 | 未运行代码测试 | 等待各 agent 按任务领取并更新

## 10. 删除条件

满足以下条件后删除本文档：

1. M1 MVP 上线候选完成。
2. M2 RAG Readiness Gate 完成。
3. M3 中本轮决定补的测试任务完成或明确转入正式 backlog。
4. 仍有长期价值的结论已经回写到正式文档：
   - `docs/architecture/ARCHITECTURE.md`
   - `docs/architecture/grammar-rag-design.md`
   - `docs/operations/model-configuration-usage.md`
   - `docs/README.md`

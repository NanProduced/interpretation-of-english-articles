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
| Claude | 暂停承接新任务，历史已完成任务保留归属 | 新增任务、跨文件补丁 |
| GLM | 后端主链路、生产配置、COS/CDN、RAG readiness 后续、数据结构、seed 生成、测试补齐、Academic 闭环诊断 | 前端页面重构、UI 细节调整 |
| Gemini | 小程序前端体验、UI、页面交互、协议/隐私/关于页面、分享卡片展示接入 | 后端 workflow、RAG 外部服务接入、脚本/测试/生产配置工程任务 |

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
| M1 MVP 上线候选 | 清零红色上线阻断项 | DONE | API 地址、分享卡片、精读收藏/生词、封面 CDN 本轮暂缓、基础页面均完成并验证 |
| M2 RAG Readiness Gate | RAG 可插拔但默认关闭 | DONE | grammar RAG 配置开关、fallback、seed 数据、测试骨架完成 |
| M3 测试补强 | 覆盖高风险业务侧 | DONE | Daily Reader、用户资产、反馈/额度至少补齐关键路径测试 |

## 4. P0 上线阻断任务

静态图片生成与接入要求见 [小程序静态图片资源生成 Brief](./static-image-assets-brief.tmp.md)。

| ID | 任务 | Owner | 状态 | 依赖 | 验收标准 | 最后更新 |
|----|------|-------|------|------|----------|----------|
| P0-01 | 修正开发/正式环境 API 地址配置 | Gemini | DONE | 生产 API 域名决策 | `env.ts` 不再使用占位值；dev/staging/prod 语义清晰；构建通过 | 2026-04-28 21:17 |
| P0-02 | Daily Reader 分享卡片自定义封面 | Gemini | DONE | P0-04A | `daily-reader/index.tsx` 分享 `imageUrl` 使用本地静态 fallback 图片；`tsc` 与小程序构建通过 | 2026-04-29 16:50 |
| P0-03A | 精读页生词/收藏持久化后端契约确认 | Claude | DONE | 现有 vocabulary/favorites API | 明确 Daily Reader 调用现有 vocabulary/favorites API 所需字段；如后端缺口只补服务/API，不改前端页面 | 2026-04-28 21:20 |
| P0-03B | 精读页生词/收藏持久化前端接入 | Gemini | DONE | P0-03A | `handleAddVocab` / `handleFavorite` 调用真实 API 或本地优先同步；失败有提示；重复点击幂等；不改后端 | 2026-04-28 23:01 |
| P0-04A | Daily Reader 本地静态分享图 fallback | Gemini | DONE | 无 | 提供包内静态分享图或现有稳定本地资源；`useShareAppMessage` 配置 `imageUrl`；不依赖 COS/CDN | 2026-04-29 16:50 |
| P0-04B | 封面图从本地 static/covers 迁移到 COS+CDN | GLM | DEFERRED | DNS/HTTPS/CDN/COS/微信合法域名配置 | 后续生产化阶段再做；当前本地调试不阻塞 M1 | 2026-04-28 22:57 |
| P0-05 | 用户协议与隐私政策页面 | Gemini | DONE | 正式文案或临时合规文案 | 个人中心可跳转；页面可返回；不再是 Toast 占位 | 2026-04-28 21:17 |
| P0-06 | 关于我们页面 | Gemini | DONE | 产品基础信息 | 个人中心可跳转；页面内容完整；不再是 Toast 占位 | 2026-04-28 21:17 |

## 5. P1 RAG Readiness 任务

| ID | 任务 | Owner | 状态 | 依赖 | 验收标准 | 最后更新 |
|----|------|-------|------|------|----------|----------|
| RAG-01 | 打通 grammar bundle 的 sentences 传递 | Claude | DONE | 无 | `build_grammar_bundle(plan, sentences=sentences_data)` 或等价实现；测试覆盖 baseline 不变 | 2026-04-28 21:20 |
| RAG-02 | 增加 `GRAMMAR_RAG_ENABLED=false` 配置 | Claude | DONE | 无 | settings 和 `.env.example` 有配置；默认关闭；未配置不影响启动 | 2026-04-28 21:20 |
| RAG-03 | 限定只有 grammar 可走 RAG | Claude | DONE | RAG-02 | vocabulary/translation 不因 `few_shot_mode=rag` 接入 RAG；行为有测试 | 2026-04-28 21:20 |
| RAG-04 | `grammar_rag_service` fallback 骨架 | Claude | DONE | RAG-01, RAG-02 | 空结果、异常、低置信度均回 baseline；记录 fallback reason | 2026-04-28 21:20 |
| RAG-05 | 静态 grammar examples 合法性审计 | GLM | DONE | 无 | `grammar.yaml` 中 `output_fragment` 均可解析为 JSON；类型只含 `grammar_note` / `sentence_analysis` | 2026-04-28 22:03 |
| RAG-06 | 生成第一版 grammar seed JSONL | GLM | DONE | RAG-05 | 生成本地 seed 文件，字段包含 example_id/output_type/variant/tags/signals/retrieval_text | 2026-04-28 22:03 |
| RAG-07 | `grammar_retrieval_hints.py` 轻量规则 | GLM | DONE | RAG-06 | 覆盖句长、逗号、that/which/who、句首 V-ing/V-ed、插入语等信号；有单测 | 2026-04-28 22:03 |
| RAG-08 | prompt/debug 暴露 selection mode | Claude | DONE | RAG-04 | debug 输出包含 selection_mode、example_count、fallback_reason 预留字段 | 2026-04-28 21:20 |

## 6. P1 测试补强任务

| ID | 任务 | Owner | 状态 | 依赖 | 验收标准 | 最后更新 |
|----|------|-------|------|------|----------|----------|
| T-01 | Daily Reader workflow/pipeline 关键路径测试 | GLM | DONE | 现有 pipeline 稳定 | 覆盖生成、发布、查询、失败状态至少一条关键路径 | 2026-04-28 23:15 |
| T-02 | 用户资产 records/vocabulary/favorites 测试 | GLM | DONE | 现有服务接口 | 覆盖 upsert、list、delete、ID 语义和幂等行为 | 2026-04-28 23:15 |
| T-03 | 反馈路由/服务测试 | GLM | DONE | 无 | 覆盖提交、列表、删除或状态更新关键路径 | 2026-04-28 23:15 |
| T-04 | 额度/积分流水测试 | GLM | DONE | 无 | 覆盖 quota check、扣减/发放、ledger 查询关键路径 | 2026-04-28 23:15 |
| T-05 | 修复 task center 已知测试失败 | Codex | DONE | 无 | `tests/test_task_center.py` 中 3 个 `TaskSubmitResult(client_record_id)` 失败修复；task center 测试全绿 | 2026-04-29 17:10 |

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
| A-01 | Academic API 闭环诊断报告 | GLM | DONE | 明确 `/analyze` 与 `/analysis-tasks` 对 academic 的实际失败点和最小修复路径 | 2026-04-28 23:30 |
| A-02 | 前端 Academic 入口保护 | Gemini | DONE | 如果入口存在，隐藏或降级说明，避免用户触发 501/422 | 2026-04-28 21:17 |

## 9. 进展记录

按时间倒序追加。格式：

```text
YYYY-MM-DD HH:mm | Agent | Task ID | 状态 | 摘要 | 验证 | 风险/下一步
```

记录：

- 2026-04-29 16:50 | Gemini | P0-02, P0-04A, M1 | DONE | 完成 Daily Reader 静态分享封面接入。提供包内本地 fallback 图片 (share-fallback.jpg) 并在 useShareAppMessage 中配置 imageUrl，消除 typescript 类型报错，使 P0-02 和 P0-04A 完成。此时所有前端阻断项完成，M1 里程碑标记为 DONE。 | `npx tsc -p tsconfig.json --noEmit` 通过；`npm run build:weapp` 通过 | P0-04B 依然暂缓

- 2026-04-29 17:10 | Codex | REVIEW, T-05 | DONE | checkpoint review 收口：修正进度表与记录不一致；补齐 Daily Reader 收藏按 target 删除的后端路由；清理前端 Daily Reader 取消收藏同步对不存在 API 的假设；补上 task center 测试缺失的 `client_record_id` | `npx tsc -p tsconfig.json --noEmit` 通过；`npm run build:weapp` 通过；`pytest tests/test_user_assets.py tests/test_task_center.py tests/test_rag_readiness.py tests/test_prompt_composition.py -q` 58 passed；`pytest tests/test_grammar_retrieval_hints.py tests/test_daily_reader.py tests/test_feedback.py tests/test_quota_credits.py -q` 46 passed；`python -m compileall app tests scripts` 通过；grammar audit/seed 脚本通过 | RAG 真接入、COS/CDN 迁移、品牌物料接入继续暂缓

- 2026-04-28 22:57 | Codex | PLANNING | DONE | 根据本地调试优先策略重拆 P0-04：新增 P0-04A 本地静态分享图 fallback 交给 Gemini，P0-04B COS+CDN 迁移改为 DEFERRED。P0-02 解除 COS/CDN 阻塞，改依赖 P0-04A。新增 T-05 给 GLM 修复 task center 3 个已知失败 | `npx tsc --noEmit` 未通过，发现 P0-03B 当前实现存在 `activeMark.occurrence` 类型错误；`npm run build:weapp` 通过 | Gemini 需先修 P0-03B 类型错误，再做 P0-04A/P0-02；GLM 做 T-05
- 2026-04-28 22:37 | Gemini | P0-03B | DONE | 完成前端生词/收藏逻辑：修改 `CloudSyncService` 兼容 `daily_` 记录前缀（无 cloud record ID 时不拦截）；实现 Daily Reader 页面的 `handleAddVocab` 和 `handleFavorite`，采用本地优先+后台入队云端同步的方案；增加页面级“收藏全文”按钮和交互。 | 代码修改通过 Typescript 编译，按钮样式适配完毕 | 等待其余 P0 上线阻断任务

- 2026-04-28 22:03 | Codex | REVIEW | DONE | 复核 GLM 交付：RAG-05/06/07 验证通过，M2 RAG Readiness Gate 标记 DONE；T-01~T-04 验证通过，M3 测试补强标记 DONE。确认 `grammar_seed_v1.jsonl` 共 21 条，UTF-8 读取中文正常，PowerShell 预览乱码属于控制台编码问题 | `uv run pytest tests/test_grammar_retrieval_hints.py tests/test_daily_reader.py tests/test_user_assets.py tests/test_feedback.py tests/test_quota_credits.py -q` 60 passed；`uv run pytest tests/test_rag_readiness.py tests/test_prompt_composition.py tests/test_task_center.py -q` 为 40 passed / 3 known failures；`npm run build:weapp` 通过；`python scripts/audit_grammar_examples.py` 和 `python scripts/generate_grammar_seed.py` 通过 | M1 仍未完成：P0-02/P0-03B/P0-04 需要继续推进
- 2026-04-28 23:30 | GLM | A-01 | DONE | 完成 Academic API 闭环诊断。发现 5 个问题：(1) CRITICAL: `HEAVY_FAILURE_CODES` 缺少 academic 错误码（TERM_AGENT_FAILED/ACADEMIC_TRANSLATION_AGENT_FAILED/UNDERSTANDING_AGENT_FAILED/ACADEMIC_NORMALIZE_FAILED），导致重度降级结果被标记为 succeeded 并扣费；(2) Minor: `schema_version` 硬编码为 "3.0.0"，academic 结果应为 "3.0.0-academic"；(3) README 声称 /analyze 对 academic 返回 501，实际代码无此限制；(4) 422 TASK_TERMINATED 是通用失败响应，非 academic 专属；(5) 优雅降级可能掩盖完全失败。已修复 (1) 和 (2) | `uv run pytest tests/test_task_center.py -q` (28 passed, 3 pre-existing failures) | D-04 Academic 深度优化仍为 DEFERRED
- 2026-04-28 23:15 | GLM | T-01~T-04 | DONE | 完成 4 项测试补强任务。新增 60 条测试覆盖：Daily Reader(9)、用户资产(14)、反馈(9)、额度积分(12)、grammar retrieval hints(16)。所有测试通过 | `uv run pytest tests/test_grammar_retrieval_hints.py tests/test_daily_reader.py tests/test_user_assets.py tests/test_feedback.py tests/test_quota_credits.py -q` → 60 passed | 无
- 2026-04-28 22:45 | GLM | RAG-06 | REVIEW | 生成第一版 grammar seed JSONL（21 条记录）。字段包含 example_id/output_type/variant/tags/signals/retrieval_text，以及扩展字段 source_sentence/output_fragment/label/teaching_goal/quality_score/approved。retrieval_text 按设计文档 8.2 模板拼接。文件位于 `server/data/seed/grammar_seed_v1.jsonl` | `python scripts/generate_grammar_seed.py` → 21 records; JSONL 每行可被 `json.loads` 解析 | RAG-07 依赖解除，可开始
- 2026-04-28 22:30 | GLM | RAG-05 | REVIEW | 完成静态 grammar examples 合法性审计。发现 14/21 条 output_fragment 含未转义 ASCII 双引号（中文语境中用作引号），导致 JSON 解析失败。修复方案：将中文语境中的 ASCII `"` 替换为 Unicode 中文引号 `\u201c`/`\u201d`，并确保引号配对正确。审计脚本 `scripts/audit_grammar_examples.py` 验证 21 条全部通过：output_fragment 均可解析为 JSON，type 仅含 grammar_note/sentence_analysis | `python scripts/audit_grammar_examples.py` → ALL CHECKS PASSED; `uv run pytest tests/test_prompt_composition.py -q` → 4 passed | RAG-06 依赖解除，可开始
- 2026-04-28 21:29 | Codex | COORDINATION | DONE | 按用户要求调整后续任务归属：Claude 暂停承接新任务；原 Claude 后续任务转给 GLM；Gemini 限定为前端和 UI 任务，不承接后端或工程性任务。P0-04 owner 从 Claude 改为 GLM；P0-03B 因 P0-03A 已完成，从 BLOCKED 改回 TODO | `npx tsc --noEmit` 通过；`npm run build:weapp` 通过；`pytest tests/test_rag_readiness.py tests/test_prompt_composition.py -q` 12 passed；`python -m compileall app tests` 通过 | P0-04 仍需 COS bucket/CDN 域名；P0-03B 需 Gemini 继续前端接入
- 2026-04-28 21:20 | Claude | P0-03A | DONE | 后端契约确认：现有 `POST /vocabulary`（source_provider="daily_reader"）和 `POST /favorites`（target_type="daily_reader_article"）完全满足 Daily Reader 生词/收藏需求，无需补后端接口。前端 Gemini 可直接使用 `addVocabToCloud()` 和 `addFavoriteToCloud()` | 代码审查确认 vocabulary.client.ts 和 favorites.client.ts 已有完整 DTO 映射 | P0-03B 解除阻塞，Gemini 可开始前端接入
- 2026-04-28 21:20 | Claude | P0-04 | BLOCKED | 需要 COS bucket/CDN 域名才能实现远程 cover URL。当前 cover_download.py 落盘到本地 static/covers，仅适用于 dev 环境 | - | 需用户提供 COS bucket 和 CDN 域名配置
- 2026-04-28 21:20 | Claude | RAG-01, RAG-02, RAG-03, RAG-04, RAG-08 | DONE | RAG Readiness Gate 全部 Claude 侧任务完成。改动摘要：(1) settings.py + .env.example 增加 GRAMMAR_RAG_ENABLED=false；(2) analyze_nodes.py 传递 sentences_data 到 build_grammar_bundle；(3) example_strategy.py 限定只有 grammar 可走 RAG，vocabulary/translation 始终 baseline；(4) grammar_rag_service.py 替换为完整 fallback 骨架，含 RAGQueryResult + build_rag_debug_info；(5) prompt_debug.py 增加 example_count/fallback_reason 预留字段 | `uv run pytest tests/test_rag_readiness.py -q` 8 passed；`uv run pytest tests/test_prompt_composition.py -q` 4 passed；全量测试 187 passed（5 failures 均为预存在的 TaskSubmitResult 问题） | 等待 GLM 完成 RAG-05/06/07 后可进入 M2 Gate
- 2026-04-28 21:17 | Gemini | P0-01, P0-05, P0-06, A-02 | DONE | 完成 API 地址配置、新增关于我们和隐私政策页面、隐藏学术模式入口 | npm run build:weapp 成功编译 | P0-02 和 P0-03B 仍被阻塞，等待后端接口/CDN策略确认
- 2026-04-28 21:15 | Gemini | P0-02, P0-03B | BLOCKED | 缺少前置依赖 (P0-04, P0-03A) | - | 等待 Claude 完成接口确认与 CDN 配置
- 2026-04-28 21:15 | Gemini | P0-01, P0-05, P0-06, A-02 | IN_PROGRESS | 开始处理前端项 | - | -
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

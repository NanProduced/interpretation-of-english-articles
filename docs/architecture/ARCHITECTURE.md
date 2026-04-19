# Claread 透读架构决策记录

> 本文档记录已收敛的架构决策，作为后续开发的设计依据。
> 历史变更记录见 git commit。

## 1. 技术栈选型结论

| 决策项 | 结论 | 废弃替代方案 |
|--------|------|-------------|
| 业务数据库 | PostgreSQL | SQLite（已废弃，不适合多设备同步） |
| 词典数据库 | TECD3 离线解析后导入 PostgreSQL | 磁盘 JSON 文件缓存（已废弃） |
| 缓存方案 | L1 进程内内存缓存 + PostgreSQL 真源 | Redis（第二阶段可选，不作为首发阻塞） |
| 运行时词典 | Tecd3Provider 查询 PostgreSQL | 第三方在线词典 API（已废弃） |

**为什么不保留 SQLite**：
- 嵌入式文件型，不适合多设备同步
- 与 PostgreSQL 双存储造成备份/迁移/监控分裂

**为什么不先上 Redis**：
- 登录、云端资产、TECD3 导入优先级更高
- 单一实例部署时 L1 内存缓存足够

## 2. 数据模型设计原则

### 2.1 双平面分离

| 平面 | 表 | 职责 |
|------|-----|------|
| 执行控制平面 | `analysis_tasks` | 排队、幂等、并发控制、失败重试、额度结算 |
| 用户资产平面 | `analysis_records` | 历史回看、收藏、生词本引用、结果快照 |

**为什么分离**：
- 任务执行态和结果展示态生命周期不同
- 分离后"处理中可回看"，不会混成难维护的大表

### 2.2 分析记录原则

- 回看默认读取快照，不在历史页自动重跑 `/analyze`
- "重新分析"是显式操作
- `render_scene_json` 使用 JSONB 存储

### 2.3 核心业务表

- `users` / `user_sessions`
- `analysis_tasks` / `analysis_task_events`
- `analysis_records` / `analysis_results` / `analysis_audit_logs`
- `user_credit_accounts` / `user_credit_ledger`
- `favorite_records` / `vocabulary_book`
- `dict_entries` / `dict_lookup_targets` / `dict_redirects`

词典表保护规则：

- `dict_entries` / `dict_lookup_targets` / `dict_redirects` 视为高成本真源表
- 非特殊情况，禁止删除表、清空表、重建表
- 如必须重建，前提是已经确认离线重导链路可用，且包含 `exam_tag` 等成熟数据恢复方案

### 2.4 生词本去重规则

- 优先按 `lemma` 去重
- lemma 为空时回退到 `word`

## 3. 认证与登录

### 3.1 微信登录流程

```
wx.login() → code → POST /auth/wechat/login → code2Session → session_token
```

### 3.2 登录策略

- **匿名可用**：不阻塞首次使用
- **登录增强**：跨设备同步、长期保存、恢复个人资产
- **触发时机**：提交分析前（强校验扣积分）、首次收藏/生词本、进入"我的"页主动登录

### 3.3 认证架构

- 小程序端负责拿 code，后端负责换取 openid/session_key 并签发业务 session
- 前端通过统一请求头 `Authorization: Bearer ...` 注入身份态
- 不允许前端临时拼接多种认证方式

## 4. 积分与配额模型

### 4.1 计费规则

- 加权 token 模型：`input_tokens * 1 + output_tokens * 5`
- 每日 1000 积分
- 奖励积分（bonus_points）单独计算，不与每日额度合并

### 4.2 扣减时机

- 提交前校验是否有可用额度
- **任务成功后再真正扣减**
- 失败任务不扣减（如引入预占额度，失败时必须自动冲正）

### 4.3 展示口径

- 默认展示"今日剩余积分"
- 奖励额度单独展示

## 5. 异步任务中心

### 5.1 核心接口

- `POST /analysis-tasks` - 提交任务
- `GET /analysis-tasks/{task_id}` - 查询单个任务
- `GET /analysis-tasks/current` - 获取当前活跃任务
- `GET /records?include_processing=true` - 历史记录含处理中

### 5.2 混合协同语义

- 默认"提交任务并在单次请求内等待结果（40s 超时）"
- 超时后返回 `task_id + cloud_record_id + client_record_id`，前端轮询 `GET /analysis-tasks/{task_id}`
- 历史页直接读取 `cloud_record_id` 对应的云端记录
- 前端使用 `client_record_id` 做本地回看主键，`cloud_record_id` 做云端 API 操作

### 5.2.1 任务接口字段语义

任务接口响应中的 ID 字段：

| 字段 | 类型 | 语义 | 状态 |
|------|------|------|------|
| `task_id` | UUID | 任务主键 | 当前 |
| `record_id` | UUID | 云端 analysis_records.id | **已弃用**，用 `cloud_record_id` 替代 |
| `cloud_record_id` | UUID | 云端 analysis_records.id | 新增 |
| `client_record_id` | string | 前端生成的稳定记录主键 | 新增 |

### 5.3 幂等控制

| 字段 | 用途 |
|------|------|
| `idempotency_key` | 解决同一次点击重发 |
| `request_fingerprint` | 内容相同但前端误生成新 key 时的二次校验 |

### 5.4 单用户单任务约束

- `UNIQUE (user_id, idempotency_key)`
- `UNIQUE (user_id) WHERE status IN ('queued', 'running', 'finalizing')`
- 已有活跃任务时返回 `409 ACTIVE_TASK_EXISTS`

### 5.5 任务状态机

```
queued → running → finalizing → succeeded / failed / cancelled / expired
```

## 6. 词典查询策略

### 6.1 查询顺序

1. normalize query（trim + lowercase）
2. alias 映射（`u.s.` → `us`）
3. exact word hit
4. lemma fallback（使用 LemmInflect 还原词形）
5. redirect / disambiguation

### 6.2 phrase_gloss 处理

- phrase_gloss **不走** `/dict` 主查询路径
- 由 workflow / vocabulary agent 直接提供可渲染的 glossary

### 6.3 缓存策略

- L1 TTL：24h
- 查询 key：`provider + normalized_query`
- `not_found` 结果也允许短 TTL 缓存

## 7. 前端状态管理

### 7.1 页面状态映射

| 后端信号 | 页面状态 | 用户表现 |
|----------|----------|----------|
| 有可渲染结果且无明显异常 | `normal` | 正常渲染 |
| 有结果但部分深度讲解缺失 | `degraded_light` | 顶部轻提示 banner |
| 有结果但内容完整度明显不足 | `degraded_heavy` | 降级提示 + 重新分析入口 |
| 请求成功但无有效内容 | `empty` | 空状态页 + 修改重试 |
| 非网络型服务失败 | `failed` | 错误状态页 + 重试 |
| 请求超时 | `timeout` | 超时状态页 + 重试 |
| 网络异常 | `network_fail` | 网络错误页 + 重试 |

### 7.2 Store 状态机

```
idle → loading → polling → success / empty / error
```

### 7.3 类型边界

- `client/src/types/api/` = 后端 DTO (snake_case)
- `client/src/types/view/` = 前端 VM (camelCase)
- 转换只在 `services/api/adapters/` 一处

### 7.4 用户资产 ID 契约

前端统一使用以下 ID 语义，禁止混用：

| 前端字段 | 后端字段 | 含义 | 用途 |
|----------|----------|------|------|
| `clientRecordId` | `client_record_id` | 前端生成的稳定记录主键 | 页面路由、本地 storage、历史回看、本地资产引用 |
| `cloudRecordId` | `cloud_record_id` / `id` | 云端 analysis_records.id (UUID) | 后端写操作、外键引用、删除记录、收藏、生词关联 |
| `taskId` | `task_id` | 分析任务主键 | 任务状态查询、轮询 |

兼容策略：

- 允许在局部组件内部保留 `recordId` 变量名，但必须明确等价于 `clientRecordId`
- 不允许把云端 UUID 写入任何本应表达 `clientRecordId` 的字段
- 迁移期间保留兼容字段（如 `record_id`），但新代码必须优先使用明确命名

### 7.5 离线优先同步策略

当前结论：采用"离线优先 mutation queue"方案。

原则：

- 所有用户操作先写本地 storage
- 每次 mutation 写入持久化 Sync Queue（Taro storage）
- 后台 flush 将 mutation 合并到云端
- 云端成功后更新本地同步状态
- 同步失败不回滚用户可见本地结果，只标记待同步或失败

Sync Queue 数据结构：

- `opId`: 操作唯一标识
- `entityType`: `'record' | 'favorite' | 'vocab'`
- `entityId`: 实体 ID
- `action`: 操作类型（如 `SYNC_RECORD`, `ADD_FAVORITE`, `UPSERT_VOCAB` 等）
- `payload`: 操作参数
- `status`: `'pending' | 'running' | 'failed' | 'done'`
- `retryCount`: 重试次数（最多 5 次，指数退避）

触发时机：

- App 启动后
- 登录成功后
- `onShow` 切前台时
- 用户操作入队后立即触发

本地 ID 映射层：

- 持久化存储 `clientRecordId → cloudRecordId` 映射
- 写入时机：提交分析任务成功、同步记录成功、云端记录/生词/收藏回流时
- 用途：生词同步 resolve cloud id、收藏同步 resolve cloud id、历史记录补齐映射

### 7.6 Vocabulary 接口字段语义

生词本接口响应中的来源记录 ID 字段：

| 字段 | 类型 | 语义 | 状态 |
|------|------|------|------|
| `analysis_record_id` | UUID | 来源记录云端 ID | **已弃用**，用 `source_cloud_record_id` 替代 |
| `client_record_id` | string | 来源记录前端主键 | **已弃用**，用 `source_client_record_id` 替代 |
| `source_cloud_record_id` | UUID | 来源记录云端 ID | 新增 |
| `source_client_record_id` | string | 来源记录前端主键 | 新增 |

前端 adapter 要求：

- 只允许用 `source_client_record_id` 或兼容期的 `client_record_id` 回填 `sourceClientRecordId`
- 不允许再把 `analysis_record_id` 用作 `sourceClientRecordId`

## 8. 实施原则

### 8.1 禁止的做法

- 让 history 页点击后重新调用 `/analyze` 代替结果回看
- 收藏时整份复制 `render_scene` 到另一套结构
- 用散落的 `Taro.setStorageSync` key 拼接出多套不一致的数据源
- 把本地 storage 视为正式真源

### 8.2 文档维护规则

- 已实现内容在主文档中写"当前结论"
- 新能力延伸补到主文档，不新增平行文档
- 开发记录不在架构文档中

## 9. 关联文档

- `mini-program-integration-and-ux-design.md` - 用户主链路与产品设计
- `daily-reader-module-design.md` - 每日精读独立设计
- `tecd3-local-dictionary-integration.md` - TECD3 词典接入细则
- `server/db/migrations/0001_initial_schema.sql` - 数据库 DDL

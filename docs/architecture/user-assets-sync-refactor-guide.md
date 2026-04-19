# 用户资产层重构开发指引

> 文档定位：提供给实现 agent 的详细开发指引，用于完成 Claread 透读用户资产层重构。  
> 目标范围：统一 ID 契约、修复生词回看原文 bug、将当前即发即弃同步升级为离线优先的持久化同步机制，并收敛前后端用户资产架构。  
> 非目标：不重写分析 workflow，不推倒现有前后端整体架构，不引入复杂双向协作合并。

## 1. 背景

当前用户资产层存在两类核心问题，而且应在同一轮重构中统一解决：

1. `client_record_id` 与云端 `analysis_records.id` UUID 语义混用，导致跨页面引用不稳定。
2. 收藏、生词、掌握状态等云端同步仍以 best-effort 为主，弱网或离线场景下本地状态与云端容易脱节。

这两个问题并不是孤立 bug，而是同一个架构缺口的不同表现：

- ID 契约没有冻结
- 页面层直接混用 storage、API 和同步逻辑
- 没有持久化的 Sync Queue
- 本地资产模型没有完整表达同步状态

## 2. 当前代码状态确认

本指引基于当前仓库状态编写，开发前应以当前代码为准，不要基于旧方案臆测。

### 2.1 已确认现状

- 工作树当前干净，无未提交更改。
- `CloudSyncService` 已存在一个内存级 `enqueueSync()`，可做同 key 串行，但应用重启后队列会丢失，不属于真正离线同步。
- `vocabulary.client.ts` 仍存在错误兜底逻辑：

```ts
recordId: dto.client_record_id || dto.analysis_record_id || ''
```

这会把云端 UUID 错误塞进本应表示 `client_record_id` 的字段。

- `VocabEntry.recordId` 当前定义语义是来源文章 `client_record_id`。
- 任务接口 `/analysis-tasks` 仍使用宽泛的 `record_id` 字段，但实际承载的是云端 UUID。
- 设计文档已提出 `sync_state`，但当前本地模型尚未完整落地。

### 2.2 当前问题直接表现

- 生词本点击“回看全文”时，部分条目会错误提示“原文已删除”，即使历史记录实际存在。
- 弱网或离线时，收藏、生词新增、掌握状态切换可能只改了本地，未能可靠同步到云端。
- 已登录页面存在“云端优先覆盖本地”的倾向，本地 pending 变更可能被旧快照覆盖。

## 3. 本次重构目标

### 3.1 必须达成

- 统一记录 ID 契约，彻底消除 `client_record_id` 与云端 UUID 混用。
- 修复“生词本回看原文失败但历史记录存在”的 bug。
- 将收藏、生词、掌握状态、记录同步升级为本地优先、持久化排队、后台 flush 的机制。
- 页面层不再直接组合 `storage + api + cloudSync`。
- 为后续 `notes / feedback` 接入同一套资产框架预留扩展位。

### 3.2 不在本次处理

- 不重构分析 workflow 节点与模型编排。
- 不引入 CRDT、操作日志回放、复杂多端协作合并。
- 不做每日精读模块改造。
- 不引入 Redis、远端消息队列等新的基础设施。

## 4. 核心架构决策

## 4.1 冻结 ID 契约

从本次重构开始，项目内统一使用以下语义：

- `clientRecordId`
  - 含义：前端生成的稳定记录主键
  - 用途：页面路由、本地 storage、历史回看、本地资产引用

- `cloudRecordId`
  - 含义：云端 `analysis_records.id` UUID
  - 用途：后端写操作、外键引用、删除记录、收藏、生词关联

- `taskId`
  - 含义：分析任务主键

禁止继续在跨层协议中使用宽泛 `recordId` 同时表示两种语义。

### 4.1.1 兼容策略

- 允许在局部组件内部保留 `recordId` 变量名，但必须明确等价于 `clientRecordId`。
- 不允许把云端 UUID 写入任何本应表达 `clientRecordId` 的字段。
- 迁移期间可以保留兼容字段，但新代码必须优先使用明确命名。

## 4.2 用户资产层边界

本次建立明确的“用户资产层”，将以下逻辑从页面层收口：

- 记录、本地生词、收藏的读写
- 本地与云端的 ID 映射
- pending 操作的同步状态
- 云端 flush 与重试

建议前端目录拆分如下：

- `client/src/domain/assets/`
  - 放领域模型、Repository、Use Case
- `client/src/services/sync/`
  - 放 Sync Queue、flush、retry、触发器
- `client/src/services/storage/`
  - 只负责底层存储，不承载业务规则
- `client/src/services/api/`
  - 只负责远端 DTO 与请求
- `client/src/stores/`
  - 只承载页面状态，不直接定义资产同步规则

## 4.3 离线优先 + 持久化 Sync Queue

本次采用“离线优先 mutation queue”方案，不做重型双向同步平台。

原则：

- 所有用户操作先写本地
- 每次 mutation 写入持久化 Sync Queue
- 后台 flush 将 mutation 合并到云端
- 云端成功后更新本地同步状态
- 同步失败不回滚用户可见本地结果，只标记待同步或失败

## 5. 本地数据模型设计

## 5.1 Analysis Record

建议在现有 `AnalysisRecord` 基础上扩展：

- `clientRecordId: string`
- `cloudRecordId?: string`
- `syncState: 'local_only' | 'syncing' | 'synced' | 'sync_failed'`
- `lastSyncAttemptAt?: number`
- `lastSyncedAt?: number`
- `lastSyncError?: string | null`
- `tombstone?: boolean`

兼容策略：

- 迁移期可以保留旧字段 `recordId`
- 但必须明确 `recordId === clientRecordId`
- 禁止再把 UUID 写入这个字段

## 5.2 Vocab Entry

建议把当前 `recordId` / `cloudRecordId` 扩展并显式化：

- `sourceClientRecordId: string`
- `sourceCloudRecordId?: string`
- `syncState`
- `pendingOp?: 'create' | 'update' | 'delete' | null`
- `lastSyncError?: string | null`
- `tombstone?: boolean`

兼容期可保留：

- `recordId`
- `cloudRecordId`

但要求：

- `recordId === sourceClientRecordId`
- `cloudRecordId === sourceCloudRecordId`

并且 adapter 不允许再用 `analysis_record_id` 兜底回填 `recordId`。

## 5.3 Favorite Record

建议扩展为：

- `targetClientRecordId: string`
- `targetCloudRecordId?: string`
- `createdAt: number`
- `syncState`
- `pendingOp?: 'add' | 'remove' | null`
- `tombstone?: boolean`

## 5.4 Sync Queue Item

新增本地持久化队列项：

- `opId: string`
- `entityType: 'record' | 'favorite' | 'vocab'`
- `entityId: string`
- `action: string`
- `payload: Record<string, unknown>`
- `dependsOn?: string[]`
- `status: 'pending' | 'running' | 'failed' | 'done'`
- `retryCount: number`
- `nextRetryAt?: number`
- `lastError?: string | null`
- `createdAt: number`
- `updatedAt: number`

## 6. 后端接口契约调整

本次允许做增量收敛，不要求一次性 breaking change，但新增字段必须尽快补齐。

## 6.1 Analysis Tasks

当前 `record_id` 实际表示云端 UUID，必须去歧义。

调整目标：

- 保留 `record_id` 兼容一段时间
- 新增 `cloud_record_id`
- 新增 `client_record_id`

涉及：

- `server/app/schemas/tasks.py`
- `server/app/api/routes/tasks.py`
- `server/app/services/analysis/task_service.py`
- `client/src/services/api/client.ts`

前端迁移目标：

- 新代码优先读取 `cloud_record_id`
- 若返回 `client_record_id`，用于本地映射修复与回看链路
- 禁止再把 `record_id` 直接视作页面回看主键

## 6.2 Vocabulary

调整目标：

- 补明确字段：
  - `source_client_record_id`
  - `source_cloud_record_id`
- 兼容期保留旧字段：
  - `client_record_id`
  - `analysis_record_id`

前端 adapter 要求：

- 只允许用 `source_client_record_id` 或兼容期的 `client_record_id` 回填 `sourceClientRecordId`
- 不允许再把 `analysis_record_id` 用作 `sourceClientRecordId`

## 6.3 Favorites

本次不强制重做删除接口，但需在实现中保留演进空间。

后续目标：

- 删除应按 `target_type + target_key`
- 当前兼容保留 `DELETE /favorites/{analysis_record_id}`

## 7. 前端实施步骤

## 7.1 Step 1：冻结 ID 语义并修复当前 bug

目标：

- 先修复“生词回看原文失败”
- 阻止 UUID 污染回看主键字段

具体要求：

- 修改 `client/src/services/api/vocabulary.client.ts`
- 去掉错误兜底：

```ts
recordId: dto.client_record_id || dto.analysis_record_id || ''
```

- 只允许 `sourceClientRecordId` 来自 `client_record_id`
- 如果云端返回没有 `client_record_id`：
  - 保留 `sourceCloudRecordId`
  - 不要把它塞进 `recordId`
  - UI 上“回看全文”按钮可隐藏或降级

验收：

- 现有 bug 可稳定修复
- 不再出现把 UUID 传给 `loadRecord(by-client-id)` 的链路

## 7.2 Step 2：建立本地 ID 映射层

新增本地映射存储，例如：

- `record_identity_map`
- 内容：`clientRecordId -> cloudRecordId`

写入时机：

- 提交分析任务成功
- `syncRecord` 成功
- `fetchCloudRecordByClientId` 成功
- 云端生词或收藏回流且拿到双 ID 时

用途：

- 生词同步 resolve cloud id
- 收藏同步 resolve cloud id
- 历史记录补齐映射
- 数据迁移修复旧数据

要求：

- `resolveCloudId()` 优先读持久化映射
- 网络查询只作为补救

## 7.3 Step 3：持久化 Sync Queue 落地

新增：

- `client/src/services/sync/queue.ts`
- `client/src/services/sync/flush.ts`
- `client/src/services/sync/triggers.ts`

最小实现要求：

- 队列持久化存入 `Taro` storage
- App 启动、登录成功、onShow、手动触发时 flush
- 全局只允许一个 flush worker
- 同 entity mutation 按顺序执行
- 失败后指数退避

初版允许：

- 全局串行 flush
- 不做复杂并行

但必须：

- 持久化
- 重启后不丢队列

## 7.4 Step 4：收藏链路改造

当前结果页收藏逻辑要从“本地改 + 直接请求 + 失败回滚”改成：

- 本地更新 favorite 状态
- 写入 queue：`ADD_FAVORITE` 或 `REMOVE_FAVORITE`
- UI 立即生效
- 不在页面层做云端失败回滚
- 本地 favorite 记录标记 `pendingOp`

验收：

- 离线时收藏/取消收藏不丢
- 重启后仍会继续同步
- 最终状态与用户最后一次操作一致

## 7.5 Step 5：生词链路改造

改造范围：

- 结果页 `onAddVocab`
- 生词页删除
- 生词页掌握状态切换

要求：

- 新增生词先写本地，再 enqueue `UPSERT_VOCAB`
- 删除生词先标记 tombstone，再 enqueue `DELETE_VOCAB`
- 掌握状态切换先改本地，再 enqueue `UPDATE_VOCAB_MASTERY`

注意：

- 当前 `CloudSyncService.syncVocab` 中“同步成功后替换本地临时 id”的逻辑需要迁移到 Repository 层，不要继续由同步服务隐式修改本地 storage

## 7.6 Step 6：记录同步改造

要求：

- `saveRecordToCloud()` 成功后，必须回填本地 `cloudRecordId`
- 同时写入 `record_identity_map`
- 若存在依赖该 record 的 pending favorite/vocab 队列项，可立即解除依赖

## 7.7 Step 7：页面读取改造

目标：

- 页面不再“云端优先覆盖本地”
- 页面视图来自 Repository 聚合

建议实现：

- `HistoryRepository.listRecords()`
- `VocabularyRepository.listEntries()`

返回值应是：

- 云端快照
- 本地 pending mutation
- merge 后最终视图

简化版允许：

- 已登录仍先拉云端
- 但拉回后必须 merge 本地 pending mutation
- 禁止直接 `setRecords(cloudItems)` 覆盖本地状态

## 7.8 Step 8：本地数据迁移

需要执行一次本地迁移，修复旧数据：

- 识别 `VocabEntry.recordId` 中明显是 UUID 的值
- 尝试通过以下方式修复为正确 `clientRecordId`：
  - `sourceCloudRecordId`
  - 本地 `record_identity_map`
  - 云端 `/records/{cloudRecordId}` 或 `/records/by-client-id`
- 修复失败的：
  - 保留 `sourceCloudRecordId`
  - 不显示“回看全文”
- 给旧资产补 `syncState`

迁移要求：

- 幂等
- 可重复执行
- 单条坏数据不影响整体迁移

## 8. 后端实施步骤

## 8.1 Step A：任务接口补清晰字段

修改：

- `TaskSubmitResponse`
- `TaskStatusResponse`
- `ActiveTaskResponse`

新增：

- `cloud_record_id`
- `client_record_id`

兼容：

- 保留 `record_id`
- 标注 deprecated

## 8.2 Step B：Vocabulary Response 补 source ids

新增或重命名：

- `source_client_record_id`
- `source_cloud_record_id`

兼容：

- 旧字段先保留
- 前端新 adapter 优先读新字段

## 8.3 Step C：保留按 cloud id 取记录能力用于迁移与修复

要求：

- 前端页面主链路仍然只认 `clientRecordId`
- 数据迁移或 Repository 内部可谨慎使用 `GET /records/{cloudRecordId}`
- 不允许在页面正常回看链路中默认依赖 cloud id fallback

## 9. 建议修改文件范围

### 9.1 前端高优先级

- `client/src/types/view/analysis-record.vm.ts`
- `client/src/types/view/vocabulary.vm.ts`
- `client/src/types/view/favorites.vm.ts`
- `client/src/services/api/client.ts`
- `client/src/services/api/records.client.ts`
- `client/src/services/api/favorites.client.ts`
- `client/src/services/api/vocabulary.client.ts`
- `client/src/services/cloudSync.service.ts`
- `client/src/services/storage/index.ts`
- `client/src/services/sync/*` 新增
- `client/src/domain/assets/*` 新增
- `client/src/pages/result/index.tsx`
- `client/src/pages/vocab/index.tsx`
- `client/src/pages/history/index.tsx`
- `client/src/components/VocabDetailView/index.tsx`
- `client/src/stores/article.ts`

### 9.2 后端高优先级

- `server/app/schemas/tasks.py`
- `server/app/api/routes/tasks.py`
- `server/app/services/analysis/task_service.py`
- `server/app/schemas/user_assets/vocabulary.py`
- `server/app/services/user_assets/vocabulary.py`
- `server/app/api/routes/favorites.py` 视实现范围调整

## 10. 验收标准

### 10.1 功能验收

- 生词本任一条目点击“回看全文”，只要历史记录存在，就能稳定跳转。
- 若只有云端 UUID 没有 client id，不再误报“记录不存在或已删除”。
- 离线状态下：
  - 收藏可新增/取消
  - 生词可新增/删除
  - 掌握状态可切换
  - 应用重启后操作不丢
- 网络恢复后，队列自动 flush，最终云端状态与本地最后操作一致。

### 10.2 架构验收

- 页面层不再直接混用 `storage + api + cloudSync`
- ID 语义在类型、DTO、VM、页面跳转中清晰一致
- `CloudSyncService` 不再承担隐式数据修补职责
- 同步状态可观测，能表达 pending / failed / synced

### 10.3 测试验收建议

- 单测：
  - adapter 对 ID 字段的转换
  - queue reducer / retry / dependency
  - repository merge logic
- 集成：
  - 提交解析 -> 加生词 -> 进入生词本 -> 回看全文
  - 离线收藏 -> 重启 -> 恢复网络 -> 自动同步
  - 游客期新增资产 -> 登录后补同步
- 回归：
  - 历史记录页
  - 生词页
  - 结果页收藏与生词
  - active task 恢复链路

## 11. 文档更新要求

本次开发完成后，至少更新以下文档：

### 11.1 `docs/architecture/ARCHITECTURE.md`

需要更新：

- `analysis-tasks` 接口字段说明，避免继续笼统写 `record_id`
- 增加“用户资产 ID 契约”一节
- 增加“离线优先同步策略”一节

### 11.2 `docs/architecture/mini-program-integration-and-ux-design.md`

需要更新：

- 7.4 内容资产字段边界
- 8.4 运行时状态分层
- 8.6.1 本地缓存策略

要求把 `sync_state`、队列与 ID 映射设计写成当前结论，而不是模糊预留。

### 11.3 `client/README.md`

建议补：

- 用户资产层目录说明
- `services/sync` 与 `domain/assets` 的职责

### 11.4 `server/README.md`

建议补：

- `analysis-tasks` 响应字段语义
- `vocabulary` 返回字段中的 source ids 说明

## 12. Code Review 重点

后续 review 时重点检查：

- 是否仍存在把云端 UUID 写进前端回看主键字段的地方
- 是否仍存在页面层直接调用 `storage + api + cloudSync` 的绕过路径
- 队列是否真正持久化，而不是仅内存串行
- 删除操作是否仍然在失败时回滚本地 UI
- 本地与云端 `lemma` 去重语义是否统一
- 兼容逻辑是否被限制在 adapter / repository 边界，而不是散落全项目
- 接口新增字段是否做成向后兼容
- 文档是否同步更新且与实现一致

## 13. 建议开发顺序

按以下顺序推进：

1. 补接口字段与前端类型
2. 修正 `VocabEntry` ID 语义并修复现有 bug
3. 建立本地 ID 映射层
4. 建立持久化 Sync Queue
5. 改造收藏链路
6. 改造生词链路
7. 改造记录同步回填
8. 改造历史与生词页读取合并逻辑
9. 做本地数据迁移
10. 更新文档

## 14. 实施原则

- 保留当前分析 workflow 主链路，不做大范围无关重构。
- 优先重构用户资产层，不在本次把所有页面 Store 一并重写。
- 先修正语义，再引入队列；不要在错误 ID 语义上叠加更多同步逻辑。
- 页面体验应始终以“用户最后一次本地操作”为准，云端是最终一致性目标，而不是页面即时真源。

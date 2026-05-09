# 前后端对齐问题修复进度 (TEMP)

> 本文档为临时跟踪文件，所有问题修复完成后删除。

---

## P0 — 严重问题

### P0-1：每日精读收藏同步必定失败 ✅ 已修复

- **文件**: `client/src/services/cloudSync.service.ts` → `executeAddFavorite()` / `executeRemoveFavorite()`
- **原因**: 用 `clientRecordId.startsWith('daily_')` 判断是否为每日精读收藏，但 article.id 是标准 UUID
- **修复**: 改为通过 `targetType === 'daily_reader_article'` 判断，`syncFavorite()` 新增 `targetType` 参数
- **联动修改**: `packageB/daily-reader/index.tsx` 传入 `targetType: 'daily_reader_article'`

### P0-2：每日精读生词同步必定失败 ✅ 已修复

- **文件**: `client/src/services/cloudSync.service.ts` → `executeUpsertVocab()`
- **原因**: 同 P0-1
- **修复**: 改为通过 `sourceType === 'daily_reader_article'` 判断，`syncVocab()` 新增 `sourceType` 参数
- **联动修改**: `packageB/daily-reader/index.tsx` 传入 `sourceType: 'daily_reader_article'`

### P0-3：阅读目标配置同步发送了错误的 goal 格式 ✅ 已修复

- **文件**: `client/src/stores/config.ts` → `syncToCloud()`
- **原因**: 直接发送前端 UI goal `'daily'`，后端期望 `'daily_reading'`
- **修复**: 使用 `READING_CONFIG_MAP[purpose]?.serverGoal` 转换后再发送

---

## P1 — 高优先级

### P1-1：分析任务 422 失败响应未正确处理 ✅ 已修复

- **文件**: `client/src/stores/article.ts` → `analyze()` catch 块
- **修复**: 新增 422 状态码专门处理，提取 `failure_code` 和 `failure_message` 展示给用户

### P1-2：首页精读推荐未使用专用 today 接口 ✅ 已修复

- **文件**: `client/src/stores/daily-reader.ts` → `fetchLatest()`
- **修复**: 改用 `fetchTodayArticles()` 获取今日推荐文章

### P1-3：分享结果页其他用户无法查看 ⏳ 需设计

- **文件**: `client/src/pages/result/index.tsx` → `useShareAppMessage()`
- **原因**: 分享路径使用 recordId，但 `GET /records/by-client-id/{id}` 只能查自己的记录
- **状态**: 需设计公开分享机制（share token / 公开快照）

### P1-4：`currentAbortFlag` 模块级变量存在竞态 ✅ 已修复

- **文件**: `client/src/stores/article.ts`
- **修复**: 将 `currentAbortFlag` 替换为 `_pollSessionId` 递增计数器机制。每次 `analyze()`/`recoverActiveTask()` 递增 sessionId，轮询循环检查 sessionId 是否与自己的一致。`reset()` 递增 sessionId 使旧循环自动退出。

---

## P2 — 中优先级

### P2-1：`recoverActiveTask` 重复请求 `fetchCloudRecord` ✅ 已修复

- **文件**: `client/src/stores/article.ts` → `recoverActiveTask()`
- **修复**: 合并两次 `fetchCloudRecord` 调用为一次，先获取记录再校验 targetRecordId

### P2-2：`wait_timeout_seconds` 前端硬编码 40 秒 ✅ 已修复

- **文件**: `client/src/stores/article.ts`
- **修复**: 从 40 秒改为 60 秒

### P2-3：生词掌握状态前端二值 vs 后端五值 ⏳ 需 UI 设计

- **原因**: 前端只有"已掌握/未掌握"，后端支持 new/learning/review/mastered/archived
- **状态**: 需 UI 设计支持更多状态

### P2-4：模式切换重新分析时 `extended` 始终为 false ✅ 已修复

- **文件**: `client/src/pages/result/hooks/useResultActions.ts` → `handleModeSelect()`
- **修复**: 从 `requestParams.extended` 读取，而非硬编码 false

### P2-5：每日精读缺少"一键进入解读流程" ❌ 已关闭

- **状态**: 经评审确认关闭。每日精读页面已包含完整解析（高亮词、释义、概要、精读分析、导读、讨论题），无需再进入 Result 页分析流程，否则等于重复分析

### P2-6：分享卡片为静态图片 ⏳ 需设计

- **状态**: 需设计动态分享卡片生成方案

### P2-7：`LOADING_TIMEOUT` 常量定义但从未使用 ✅ 已修复

- **文件**: `client/src/config/api.config.ts`
- **修复**: 删除死代码

---

## P3 — 低优先级

### P3-1：匿名用户记录不会同步到云端 ⏳ 需设计

- **原因**: CloudSyncService 有 syncAllFavorites/syncAllVocab，但没有 syncAllRecords

### P3-2：`cumulative_article_count` 可能过时 ❌ 已关闭

- **状态**: 经评审确认关闭。前端 profile 页已优先使用 `recordResult.total`（`GET /records` 真实记录数），`cumulativeArticleCount` 仅作为 fallback，不影响用户体验

### P3-3：`page_state_json` 解析方式脆弱 ✅ 已修复

- **文件**: `client/src/services/api/records.client.ts` → `dtoToVm()`
- **原因**: 三层 `as` 断言链无运行时校验，且 `analysis_status` 覆盖逻辑导致 `page_state_json` 大多时候无效
- **修复**: 优先使用 `analysis_status`（后端权威字段），`page_state_json` 仅在 `analysis_status` 为终态时作为补充，并增加 `VALID_PAGE_STATES` 白名单校验

### P3-4：`record_id` 废弃字段仍作为 fallback ✅ 已修复

- **文件**: `client/src/stores/article.ts`
- **修复**: 移除所有 `|| res.record_id` / `|| current.task.record_id` fallback，统一使用 `cloud_record_id`

### P3-5：反馈删除返回 204 无 body ✅ 已修复

- **文件**: `client/src/services/api/client.ts` → `request()`
- **修复**: 在状态码判断中新增 204 显式处理，直接返回 `undefined as T`，避免空 body 反序列化问题

---

## 修复日志

| 日期 | 问题 | 操作 |
|------|------|------|
| 2026-05-05 | P0-1/P0-2 | CloudSyncService: `daily_` 前缀判断改为 `targetType`/`sourceType` 参数 |
| 2026-05-05 | P0-3 | config.ts syncToCloud: 使用 READING_CONFIG_MAP 转换 goal |
| 2026-05-05 | P1-1 | article.ts: 新增 422 状态码专门处理 |
| 2026-05-05 | P1-2 | daily-reader.ts: fetchLatest 改用 fetchTodayArticles |
| 2026-05-05 | P1-4 | article.ts: currentAbortFlag 替换为 _pollSessionId |
| 2026-05-05 | P2-1 | article.ts: recoverActiveTask 合并重复 fetchCloudRecord |
| 2026-05-05 | P2-2 | article.ts: wait_timeout_seconds 40→60 |
| 2026-05-05 | P2-4 | useResultActions.ts: extended 从 requestParams 读取 |
| 2026-05-05 | P2-7 | api.config.ts: 删除 LOADING_TIMEOUT 死代码 |
| 2026-05-09 | P2-5 | 评审关闭：每日精读已有完整解析，无需再进入分析流程 |
| 2026-05-09 | P3-5 | client.ts: 新增 204 状态码显式处理，返回 undefined |
| 2026-05-09 | P3-2 | 评审关闭：profile 已优先使用 recordResult.total，cumulativeArticleCount 仅 fallback |
| 2026-05-09 | P3-3 | records.client.ts: page_state_json 改为白名单校验，优先使用 analysis_status |
| 2026-05-05 | P3-4 | article.ts: 移除 record_id deprecated fallback |

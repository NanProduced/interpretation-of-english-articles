# 前端说明

这里是 Claread透读 的微信小程序前端工作区，当前基于 `Taro + React + TypeScript + Sass + Zustand` 开发。

## 当前主要页面

- 首页
- 文章输入页
- 解读结果页
- 历史记录页
- 我的页面

## 用户资产层

### ID 契约

前端统一使用以下 ID 语义：

- `clientRecordId`（代码中常简写为 `recordId`）：前端生成的稳定记录主键，用于页面路由、本地 storage、历史回看
- `cloudRecordId`（代码中常简写为 `cloudId`）：云端 `analysis_records.id` UUID，用于 API 操作
- `taskId`：分析任务主键

禁止把云端 UUID 写入本应表达 `clientRecordId` 的字段。

### 目录结构

- `services/storage/` — 底层本地存储，包含 record_identity_map 和 sync_queue 的持久化
- `services/cloudSync.service.ts` — 离线优先同步服务，持久化 Sync Queue + 后台 flush
- `services/migration.ts` — 本地数据迁移，修复旧 UUID 污染数据
- `services/api/` — 远端 DTO 与请求
- `stores/` — 页面状态

### 同步策略

所有用户资产 mutation 采用"本地优先 + 持久化队列 + 后台 flush"模式：

1. 用户操作先写本地 storage
2. 写入 Sync Queue（持久化到 Taro storage）
3. 后台 flush 将 mutation 合并到云端
4. 云端成功后更新本地同步状态
5. 同步失败不回滚本地结果，只标记待同步

## 图标渲染经验

### 结论

微信小程序里，自定义图标优先使用：

- `background-image: url(data:image/svg+xml,...)`
- 组件内部将设计 token 映射为真实颜色值后，再生成 SVG

不建议使用：

- `mask-image` / `-webkit-mask-image`
- 直接把 `var(--token)` 塞进 SVG data URI

### 这次遇到的问题

底部 `TabBar`、导航栏和输入框按钮图标一度出现两类异常：

- 图标完全不显示
- 图标变成黑色或灰色方块

根因有两个：

1. SVG data URI 中不能稳定解析外层 CSS 变量  
例如把 `stroke="var(--color-ink)"` 直接写进 SVG，微信小程序里不会按预期生效。

2. CSS mask 方案在微信小程序里不稳定  
把图标改成 `maskImage/WebkitMaskImage` 后，遮罩失效时就会退化成纯色矩形块。

### 当前稳定做法

图标组件位于：

- [LucideIcon](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/LucideIcon/index.tsx)

当前策略：

1. 外部组件仍然可以传 `var(--color-ink)`、`var(--text-muted)` 这类设计 token
2. `LucideIcon` 内部先把 token 解析成真实颜色值
3. 再用该颜色生成 SVG data URI
4. 最终通过 `background-image` 渲染图标

### 后续约定

- 新增图标时，优先补充 `LucideIcon` 的 `SVG_PATHS`
- 新增颜色 token 时，如需给图标使用，要同步补充 `LucideIcon` 内部的 `COLOR_TOKENS`
- 不要再把图标渲染改回 CSS mask 方案，除非经过微信开发者工具和真机双端验证

# 小程序静态图片资源生成 Brief

> 临时设计交付文档。用于指导本轮本地调试和 MVP 阶段的静态图片生成与接入。  
> 图片由外部生成工具产出后交给前端接入。本文完成使命后可删除，长期品牌规范另行沉淀。

## 1. 当前结论

当前不做 COS/CDN 动态封面流程。  
本轮优先使用包内静态图片，满足本地调试、分享卡片和基础品牌露出。

优先级：

1. ~~Daily Reader 分享卡片图~~ ✅ 已完成（7 张，已接入）
2. ~~Claread 通用分享图~~ ✅ 已完成（1 张，已接入）
3. ~~本地 Logo 图~~ ✅ 已完成（1 张，已接入）
4. ~~Daily Reader 默认封面图~~ ✅ 已完成（1 张，已接入）

**所有 P0 优先级图片资源已完成！**

暂不生成：

- 每篇文章动态封面
- 结果页 loading/error/empty 插画
- 图标图片
- 带大量固定文字的营销图

## 2. 文件放置建议

生成后建议放到：

```text
client/src/assets/share/daily-reader-share.png
client/src/assets/share/app-share.png
client/src/assets/brand/claread-logo.png
client/src/assets/brand/claread-logo@2x.png
client/src/assets/covers/daily-reader-default.png
```

如果 Taro 小程序构建对 `src/assets` 引用不稳定，前端可调整到项目现有可打包静态资源目录，但文件名语义应保持一致。

## 3. 必须生成

### 3.1 Daily Reader 分享卡片图 ✅ DONE

用途：

- `useShareAppMessage().imageUrl`
- 清理 `P0-02` / `P0-04A`

实际文件（7 张，按文章 ID 哈希轮换）：

```text
client/src/assets/share/daily-reader-01.png  (Typography Art - Claread)
client/src/assets/share/daily-reader-02.png  (Typography Art - Claread)
client/src/assets/share/daily-reader-03.png  (Typography Art - Claread)
client/src/assets/share/daily-reader-04.png  (Typography Art - Claread)
client/src/assets/share/daily-reader-05.png  (Aperture Paper / Wave)
client/src/assets/share/daily-reader-06.png  (Aperture Paper variant)
client/src/assets/share/daily-reader-07.png  (Floating cards / UI layers)
```

尺寸：1000×800，比例 5:4

接入方式：`pickShareImage(article.id)` 按文章 ID 哈希确定性选取，同一篇文章分享给不同人显示同一张图；无文章时 fallback 用 `SHARE_IMAGES[0]`。

代码位置：[client/src/packageB/daily-reader/index.tsx](../../client/src/packageB/daily-reader/index.tsx)

## 4. 建议生成

### 4.1 Claread 通用分享图 ✅ DONE

用途：

- 首页分享
- 无文章上下文时的 fallback 分享图
- 后续结果页分享 fallback

实际文件：

```text
client/src/assets/share/app-share.png  (抽象波纹 / 点线 / 光圈 Logo)
```

尺寸：1000×800，比例 5:4

接入位置：[client/src/pages/result/index.tsx](../../client/src/pages/result/index.tsx) — `useShareAppMessage()` 已接入 `imageUrl: appShare`

风格说明：抽象波纹 + 点线 + 中央光圈 Logo，青蓝色系，科技感，与 Daily Reader 分享卡（Typography 大字）完全区分。

### 4.2 本地 Logo 图 ✅ DONE

用途：

- 登录引导弹窗
- 本地调试时减少远程 COS 图片依赖
- 后续品牌统一入口

实际文件：

```text
client/src/assets/brand/claread-logo.png  (光圈图标 - 白底黑圈 + 蓝色扇形)
```

尺寸：512×512（源文件 1024×1024 已压缩）

比例：1:1

接入位置：[client/src/components/LoginGuideModal/index.tsx](../../client/src/components/LoginGuideModal/index.tsx) — 已替换远程 COS URL

说明：光圈图标（aperture symbol），黑色圆环 + 白色叶片 + 蓝色扇形点缀。SVG 源文件待补。

### 4.3 Daily Reader 默认封面图 ✅ DONE

用途：

- Daily Reader 文章无 `coverImageUrl` 时的视觉 fallback
- 文章列表卡片 fallback
- 精读详情页 header fallback

实际文件：

```text
client/src/assets/covers/daily-reader-default.png
```

尺寸：1200×675，比例 16:9（横版）

接入位置：
- [client/src/components/DailyReaderHeader/index.tsx](../../client/src/components/DailyReaderHeader/index.tsx) — 文章详情页 header
- [client/src/pages/home/index.tsx](../../client/src/pages/home/index.tsx) — 首页文章卡片
- [client/src/packageB/daily-reader-archive/index.tsx](../../client/src/packageB/daily-reader-archive/index.tsx) — 文章列表页

风格说明：16:9 横版构图，暖白底 + 淡青蓝色块 + 便签卡片 + 黄色高亮 + 光圈 Logo，杂志封面感，和分享卡/通用分享图完全区分。

设计方向：

- 更像文章封面，不是分享海报
- 干净纸页
- 高亮英文行
- 抽象边注
- 轻微纸张质感

## 5. 微信平台约束（官方规范）

> 来源：[微信小程序 Page.onShareAppMessage 官方文档](https://developers.weixin.qq.com/miniprogram/dev/reference/api/Page.html#onShareAppMessage-Object-object)

### 5.0 分享图片展示位置

分享卡片图在**微信聊天列表中以缩略卡形式展示**，并非全屏海报。
用户看到的是：左侧缩略图 + 右侧标题文字（来自 `title` 字段）。
图片本身只承担**氛围/品牌识别**作用，不需要承载任何可读信息。

### 5.1 尺寸与比例

| 项目 | 约束 | 说明 |
|------|------|------|
| **显示比例** | **5:4（硬性）** | 非此比例会被裁切或拉伸 |
| **推荐分辨率** | 500×400px（显示） / 1000×800px（2x 高清输出） | |
| **文件大小** | **≤ 300KB** | 超大图影响加载速度和用户流量 |
| **格式** | JPG 或 PNG | |

### 5.2 安全区域

- 核心视觉元素必须**居中放置**
- 不同设备/场景可能裁切图片边缘
- 重要内容避免放在四角或边缘

### 5.3 分享标题

- `title` 字段最高 **28 个汉字**，超出部分显示 `...`
- 当前实现：`{article.title} — Claread 每日精读`
- 英文文章标题通常较短，但需留意超长标题截断情况

### 5.4 朋友圈 vs 好友分享

| 分享目标 | 图片比例 | 说明 |
|----------|---------|------|
| 好友 / 群聊 (`onShareAppMessage`) | **5:4** | 本文档所有分享图均为此比例 |
| 朋友圈 (`onShareTimeline`) | **1:1** | 如需支持朋友圈分享，需单独准备方图 |

### 5.5 默认行为

若不设置 `imageUrl`，微信自动截取页面顶部 **750rpx × 600rpx** 区域作为分享图。
当前代码已设置 `shareFallback`，不会触发默认截图。

## 6. 设计约束

### 6.1 字体和文字

生成图片中尽量不要出现可读文字。  
分享标题、文章标题、品牌文字由小程序 UI 或分享卡片 `title` 字段承载。

原因：

- AI 生成文字容易变形
- 小程序不同场景会裁切图片
- 后续文案变更不应重做图片

### 6.2 风格

推荐：

- 安静
- 克制
- 阅读工具感
- 清晰纸张层次
- 轻量高亮
- 少量抽象注释卡片

避免：

- 营销海报
- 过度渐变
- 装饰性光斑
- 卡通人物
- 大量 UI mockup
- 复杂英文段落
- 深色厚重背景

### 6.3 色彩

推荐色彩方向：

```text
warm off-white
charcoal ink
muted teal
soft amber
small accent blue
```

避免单一蓝紫、深蓝、棕橙、奶油色过度主导。

## 7. 前端接入规则

给 Gemini 的接入边界：

1. 只改前端资源引用和 UI。
2. 不改后端。
3. 不改 RAG。
4. 不改 API DTO / VM 契约。
5. 不改 `cloudSync` 核心同步语义。
6. 接入后必须跑：

```bash
npx tsc --noEmit
npm run build:weapp
```

Daily Reader 分享图优先接入：

```text
client/src/assets/share/daily-reader-share.png
```

用于：

```text
useShareAppMessage().imageUrl
```

如果引入静态资源导致 Taro 小程序构建路径问题，前端应使用项目现有稳定的静态资源引用方式处理，但不得回退到远程 COS 依赖。

## 8. 验收标准

### 8.1 Daily Reader 分享卡片图

- `useShareAppMessage` 返回 `imageUrl`
- 无文章时也有 fallback 分享图
- 文件大小 ≤ 300KB
- `npx tsc --noEmit` 通过
- `npm run build:weapp` 通过

### 8.2 通用分享图

- 首页或无上下文分享可复用
- 不影响 Daily Reader 分享图

### 8.3 本地 Logo 图

- 登录引导弹窗可使用本地 logo
- 远程 COS logo 不再是本地调试必需依赖

### 8.4 默认封面图

- Daily Reader 无封面时可作为 fallback
- 不阻塞已有 `coverTheme` 渐变 fallback


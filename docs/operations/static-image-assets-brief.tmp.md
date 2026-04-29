# 小程序静态图片资源生成 Brief

> 临时设计交付文档。用于指导本轮本地调试和 MVP 阶段的静态图片生成与接入。  
> 图片由外部生成工具产出后交给前端接入。本文完成使命后可删除，长期品牌规范另行沉淀。

## 1. 当前结论

当前不做 COS/CDN 动态封面流程。  
本轮优先使用包内静态图片，满足本地调试、分享卡片和基础品牌露出。

优先级：

1. Daily Reader 分享卡片图
2. Claread 通用分享图
3. 本地 Logo 图
4. Daily Reader 默认封面图

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

### 3.1 Daily Reader 分享卡片图

用途：

- `useShareAppMessage().imageUrl`
- 清理 `P0-02` / `P0-04A`

建议文件：

```text
client/src/assets/share/daily-reader-share.png
```

尺寸：

```text
1000 x 800
```

比例：

```text
5:4
```

设计方向：

- 英文精读
- 安静、可信、学习工具感
- 打开的英文文章页面
- 柔和高亮句子
- 少量抽象注释卡片
- 不要大量可读文字

避免：

- 明显中文字
- 可读英文长句
- 手机模型
- UI 按钮
- 复杂人物
- 营销海报感
- 过强渐变和装饰性光斑

Prompt：

```text
Create a polished WeChat mini program share card image for an English reading app called Claread.
Aspect ratio 5:4, 1000x800.
A calm modern study scene: an open English article page with subtle highlighted sentences, small annotation cards, soft daylight, clean editorial layout.
Premium but restrained, warm white paper, ink black text lines, muted teal and amber highlights.
No readable text, no Chinese characters, no UI buttons, no phone mockup, no logos unless abstract.
Leave safe empty space near the top-left and center for the platform title overlay.
High clarity, minimal, elegant, app product illustration, not cartoonish.
```

## 4. 建议生成

### 4.1 Claread 通用分享图

用途：

- 首页分享
- 无文章上下文时的 fallback 分享图
- 后续结果页分享 fallback

建议文件：

```text
client/src/assets/share/app-share.png
```

尺寸：

```text
1000 x 800
```

比例：

```text
5:4
```

设计方向：

- 英文阅读解读工具
- 文章页面 + 高亮 + 词汇/语法解释抽象卡片
- 更通用，不绑定 Daily Reader

Prompt：

```text
Create a 5:4 share image, 1000x800, for a clean AI-assisted English reading tool.
Show a refined reading workspace: English article pages, gentle annotation marks, vocabulary cards, grammar note snippets represented as abstract blocks, soft neutral background.
Use a sophisticated palette: warm off-white, charcoal ink, muted teal, soft amber, a small accent blue.
No readable text, no distorted letters, no people, no clutter, no decorative blobs.
Professional, calm, trustworthy, educational technology aesthetic.
```

### 4.2 本地 Logo 图

用途：

- 登录引导弹窗
- 本地调试时减少远程 COS 图片依赖
- 后续品牌统一入口

建议文件：

```text
client/src/assets/brand/claread-logo.png
client/src/assets/brand/claread-logo@2x.png
```

尺寸：

```text
512 x 512
1024 x 1024
```

比例：

```text
1:1
```

设计方向：

- 字母 C
- 书页
- 阅读高亮线
- 简洁图标
- 小尺寸可识别

Prompt：

```text
Create a square app logo for "Claread", an English reading comprehension mini program.
1024x1024.
Minimal symbol combining a letter C, an open book page, and a subtle reading highlight mark.
Flat vector-like style, clean edges, high recognizability at small size.
Palette: charcoal, warm white, muted teal, small amber accent.
No small text, no complex details, no mockup, no background scene.
```

### 4.3 Daily Reader 默认封面图

用途：

- Daily Reader 文章无 `coverImageUrl` 时的视觉 fallback
- 文章列表卡片 fallback
- 精读详情页 header fallback

建议文件：

```text
client/src/assets/covers/daily-reader-default.png
```

尺寸：

```text
1200 x 675
```

比例：

```text
16:9
```

设计方向：

- 更像文章封面，不是分享海报
- 干净纸页
- 高亮英文行
- 抽象边注
- 轻微纸张质感

Prompt：

```text
Create a 16:9 editorial cover image, 1200x675, for a daily English reading article feature.
A close-up of a clean article page with soft highlighted English lines, margin notes as abstract cards, calm morning light, refined paper texture.
No readable text, no people, no UI buttons.
Elegant, quiet, premium reading experience.
Colors: warm white, charcoal, muted teal, pale amber.
```

## 5. 设计约束

### 5.1 字体和文字

生成图片中尽量不要出现可读文字。  
分享标题、文章标题、品牌文字由小程序 UI 或分享卡片 `title` 字段承载。

原因：

- AI 生成文字容易变形
- 小程序不同场景会裁切图片
- 后续文案变更不应重做图片

### 5.2 风格

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

### 5.3 色彩

推荐色彩方向：

```text
warm off-white
charcoal ink
muted teal
soft amber
small accent blue
```

避免单一蓝紫、深蓝、棕橙、奶油色过度主导。

## 6. 前端接入规则

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

## 7. 验收标准

### 7.1 Daily Reader 分享卡片图

- `useShareAppMessage` 返回 `imageUrl`
- 无文章时也有 fallback 分享图
- `npx tsc --noEmit` 通过
- `npm run build:weapp` 通过

### 7.2 通用分享图

- 首页或无上下文分享可复用
- 不影响 Daily Reader 分享图

### 7.3 本地 Logo 图

- 登录引导弹窗可使用本地 logo
- 远程 COS logo 不再是本地调试必需依赖

### 7.4 默认封面图

- Daily Reader 无封面时可作为 fallback
- 不阻塞已有 `coverTheme` 渐变 fallback


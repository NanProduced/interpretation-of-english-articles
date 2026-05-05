# Claread 静态图片资源清单、审计与 UI/UX 物料路线图

> 日期：2026-05-04  
> 状态：作为静态图片、插画、动效与分享物料的唯一维护文档。  
> 目的：记录当前资源、暴露体积/引用风险，并规划后续 UI/UX 优化所需物料。

## 结论

当前 MVP 品牌物料已经基本齐全，但资源体系仍偏“展示资产”，还没有形成可支持产品体验升级的完整视觉物料库。

最需要优先处理的是：

1. **压缩/重导出现有大图**：当前 Daily Reader 默认封面和分享图体积明显过大。
2. **补齐状态插画与加载动效物料**：解析加载、错误、空状态、历史为空、生词本为空都需要统一风格。
3. **建立阅读/笔记场景专属素材**：纸张、标注、文章卡、笔记层这类视觉语言应服务核心阅读体验。
4. **准备分享与传播物料升级版**：需要 1:1 朋友圈图、轻量 5:4 分享图、未来公众号/运营封面。

## 资源目录总览

| 目录 | 当前内容 | 用途 | 审计结论 |
|------|----------|------|----------|
| `client/src/assets/brand/` | 7 个 PNG | 品牌标识系统 | 源资产齐全，但 UI 场景需要轻量版 |
| `client/src/assets/covers/` | 1 个 PNG | Daily Reader 默认封面 | 体积过大，需要重导出 |
| `client/src/assets/images/share/` | 8 个 PNG | 分享卡片图 | 体积过大，需要重导出 |
| `client/src/assets/animations/` | 临时 TS 动画数据 | 解析加载页 Lottie 接入验证 | 等最终 Lottie JSON 替换 |
| `client/src/assets/illustrations/` | 1 个 JPG + 6 个 PNG | 状态插画/兜底图 | Batch 1 源图已准备，接入前需 Squoosh 压缩 |
| `docs/uiux/loading-animation/` | 概念图、关键帧、brief | 解析加载页动效制作包 | 已准备，可交给 Lottie 制作 |

## 当前真实资源盘点

### Brand

| 文件 | 尺寸 | 体积 | 观察 |
|------|------|------|------|
| `app-icon.png` | 1024×1024 | 375KB | 平台上传用，不应在小程序 UI 中直接引用 |
| `claread-logo.png` | 1254×1254 | 760KB | 登录弹窗正在引用，体积过大，建议生成轻量 UI 版 |
| `claread-icon-fullcolor.png` | 759×759 | 351KB | 适合做源资产，不适合直接小尺寸 UI 引用 |
| `claread-primary-fullcolor.png` | 1254×378 | 291KB | 可用于关于页/品牌页，日常 UI 应做轻量版 |
| `claread-secondary-bilingual.png` | 1195×310 | 257KB | 适合首页/分享品牌区，但仍可压缩 |
| `claread-horizontal-bilingual.png` | 1195×310 | 257KB | 同上 |
| `claread-primary-reversed.png` | 1254×378 | 9.5KB | 体积优秀，可保留 |

#### Brand 使用建议

| 文件 | 建议使用场景 |
|------|--------------|
| `app-icon.png` | 微信公众平台上传，不进入常规 UI |
| `claread-logo.png` | 作为源图保留，登录弹窗应替换为轻量 UI 版 |
| `claread-icon-fullcolor.png` | Logo mark 源资产、动效制作参考 |
| `claread-primary-fullcolor.png` | 启动页、关于页面、品牌展示 |
| `claread-secondary-bilingual.png` | 首页标题区、分享卡片品牌区 |
| `claread-horizontal-bilingual.png` | 页面 Header、横幅广告 |
| `claread-primary-reversed.png` | 深色背景、反白展示 |

SVG 源文件位置：

```text
.temp/Claread Logo物料/Claread_Logo_Kit_SVG/
├── 01_Primary_Lockup/
├── 03_Icon_Mark/
└── 05_Horizontal/
```

### Covers

| 文件 | 尺寸 | 体积 | 观察 |
|------|------|------|------|
| `daily-reader-default.png` | 1672×941 | 2232KB | 远超建议上限，应生成 1200×675 和 600×338 两档压缩版 |

#### Cover 使用场景

- 文章无 `coverImageUrl` 时的视觉 fallback
- 首页 Daily Reader 卡片
- 每日精读详情页 header fallback
- 历史/归档页文章封面 fallback

### Share

| 文件 | 尺寸 | 体积 | 观察 |
|------|------|------|------|
| `app-share.png` | 1448×1086 | 1706KB | 应重导出为 1000×800，≤300KB |
| `daily-reader-01.png` | 1402×1122 | 2048KB | 应重导出为 1000×800，≤300KB |
| `daily-reader-02.png` | 1402×1122 | 1715KB | 同上 |
| `daily-reader-03.png` | 1402×1122 | 1838KB | 同上 |
| `daily-reader-04.png` | 1402×1122 | 1820KB | 同上 |
| `daily-reader-05.png` | 1402×1122 | 1755KB | 同上 |
| `daily-reader-06.png` | 1402×1122 | 1661KB | 同上 |
| `daily-reader-07.png` | 1402×1122 | 1716KB | 同上 |

#### 微信分享规格

| 场景 | 比例 | 建议尺寸 | 体积目标 |
|------|------|----------|----------|
| 好友/群聊分享 | 5:4 | 1000×800 | ≤300KB |
| 朋友圈分享 | 1:1 | 1000×1000 | ≤300KB |
| 公众号封面 | 约 2.35:1 | 900×383 | 不进小程序包，建议 CDN/文档目录 |

当前 5:4 分享图构图可保留，但需要按上表重导出轻量版。

## 当前代码引用情况

实际被代码直接引用的图片主要是：

- 登录弹窗：`assets/brand/claread-logo.png`
- Daily Reader 默认封面：`assets/covers/daily-reader-default.png`
- Daily Reader 分享图：`assets/images/share/daily-reader-01..07.png`
- 结果页通用分享图：`assets/images/share/app-share.png`

这意味着当前最影响包体和性能的是 **默认封面 + 分享图 + 登录 Logo**。

## 命名与目录规范

### 推荐目录

```text
client/src/assets/
├── animations/       # Lottie JSON / 动效数据
├── brand/            # Logo、轻量 UI 品牌图
├── covers/           # 文章封面 fallback
├── illustrations/    # 状态插画、空状态、onboarding
├── images/share/     # 小程序分享图
└── textures/         # 纸纹、标注参考等低体积纹理
```

### 命名格式

```text
{模块}-{用途}-{变体}.{ext}
```

示例：

```text
state-error-network.png
empty-history.png
share-timeline-default.png
annotation-highlighter-swatch.png
brand-icon-ui@2x.png
```

### 文件大小目标

| 类型 | 建议上限 |
|------|----------|
| 小 UI 图标/徽章 | ≤20KB |
| Logo UI 版 | ≤30-80KB |
| 状态插画 | ≤80KB |
| 封面 fallback | ≤200KB，列表用缩略版 ≤80KB |
| 微信分享图 | ≤300KB |
| Lottie JSON | 目标 ≤80KB，上限 ≤150KB |

## 需要准备的物料

### P0 - 先做，直接影响重构质量

#### 1. 解析加载页 Lottie 与兜底图

目录建议：

```text
client/src/assets/animations/
client/src/assets/illustrations/
```

交付：

| 文件 | 规格 | 用途 |
|------|------|------|
| `claread-analysis-loading.json` | Lottie，240/320 画布，≤80KB | 解析加载页主动画 |
| `loading-analysis-fallback.jpg` | 640×640，22KB | Lottie 失败兜底，已准备；后续可用 Squoosh 重新压缩源图 |

已准备参考包：

```text
docs/uiux/loading-animation/
```

已入项目资源：

```text
client/src/assets/illustrations/loading-analysis-fallback.jpg
client/src/assets/illustrations/state-empty.png
client/src/assets/illustrations/state-error-network.png
client/src/assets/illustrations/state-error-timeout.png
client/src/assets/illustrations/state-no-credit.png
client/src/assets/illustrations/empty-history.png
client/src/assets/illustrations/empty-vocab.png
```

#### 2. 结果页状态插画

当前 `ResultIllustrations` 还是内联线条 SVG，风格偏临时。建议统一生成一组轻量插画。

| 文件 | 规格 | 风格 |
|------|------|------|
| `state-empty.png` | 源图 1254×1254，1.36MB；上线前用 Squoosh 压缩 | 空白纸页 + 光圈弱水印，已准备 |
| `state-error-network.png` | 源图 1254×1254，1.10MB；上线前用 Squoosh 压缩 | 断开的纸页/弱网络线，已准备 |
| `state-error-timeout.png` | 源图 1254×1254，1.12MB；上线前用 Squoosh 压缩 | 纸页 + 轻量时间标记，已准备 |
| `state-no-credit.png` | 源图 1254×1254，1.14MB；上线前用 Squoosh 压缩 | 纸页 + 额度票券意象，已准备 |

优先考虑 SVG/Lottie；PNG 只做兜底。

#### 3. 轻量品牌 UI 版本

不要在小尺寸 UI 中直接使用 700KB 级别 Logo。

| 文件 | 规格 | 用途 |
|------|------|------|
| `brand-icon-ui.png` | 192×192，透明底，≤30KB | 登录弹窗、空状态、loading |
| `brand-icon-ui@2x.png` | 384×384，透明底，≤50KB | 高清屏 |
| `brand-lockup-bilingual-ui.png` | 宽 480，高自适应，≤80KB | 首页/关于页 |
| `brand-watermark.png` | 256×256，低对比透明底，≤30KB | 阅读页水印/纸张背景 |

#### 4. 阅读与标注视觉物料

这些不一定都要做成 PNG，优先 SVG/CSS/Lottie，但要先准备视觉参考。

| 文件/概念 | 用途 |
|-----------|------|
| `paper-texture-subtle.png` | 极轻纸纹，可选，避免大图铺底 |
| `annotation-highlighter-swatch.png` | 高亮笔触质感参考 |
| `annotation-pencil-underline.png` | 铅笔/细线下划线参考 |
| `annotation-grammar-bracket.png` | 长难句/语法结构括号参考 |
| `annotation-note-marker.png` | 边注入口/AI 解释 marker 参考 |
| `annotation-saved-corner.png` | 已收藏词尾角标参考 |
| `note-card-layer.png` | 笔记卡片/边注层视觉参考 |

注意：实际阅读页标注建议用 CSS/SVG 绘制，避免大量图片纹理影响性能。

#### 5. Claread Annotation System 视觉参考

批注系统是后续阅读页重构的核心资产，不应仅依赖普通 `span` 背景色。

建议建立以下视觉语言：

| 批注类型 | 视觉方向 | 实现建议 |
|----------|----------|----------|
| 词汇高亮 | 低饱和半透明荧光笔，边缘轻微手写感 | CSS background / SVG path |
| 短语高亮 | 淡紫或淡黄高亮，透明度更低 | CSS background |
| 语法下划线 | 铅笔线、细波浪线、轻虚线 | CSS border / SVG stroke |
| 句法结构 | 轻括号、边线、连接线 | SVG/CSS |
| 已收藏词 | 词尾小折角、点痕、书签角标 | CSS pseudo-element |
| AI 边注入口 | 段落旁轻量 marker，点开后展开 | icon/CSS shape |

AI 生成的图片主要作为风格参考，最终交互层应尽量用 CSS/SVG/Canvas 实现，保证换行、点击和性能。

### P1 - UI/UX 重构时补齐

#### 6. 空状态插画套件

| 文件 | 场景 |
|------|------|
| `empty-history.png` | 历史记录为空，源图 1254×1254，1.49MB，已准备 |
| `empty-vocab.png` | 生词本为空，源图 1254×1254，0.89MB，已准备 |
| `empty-feedback.png` | 暂无反馈记录 |
| `empty-daily-reader.png` | 每日精读暂无内容 |

风格：暖白纸张、轻线条、少量品牌蓝、可带淡紫高亮。

#### 7. Onboarding 插画

当前产品定位是“阅读+笔记”， onboarding 应强调核心价值，而不是功能说明堆砌。

| 文件 | 主题 |
|------|------|
| `onboarding-read.png` | 带文章来，进入沉浸阅读 |
| `onboarding-annotate.png` | 重点词句自动标注 |
| `onboarding-notes.png` | 生词和笔记沉淀 |

规格：`900×900` 或 `1000×800`，根据页面布局选择。建议不放主包，或只保留压缩版。

#### 8. Daily Reader 分类封面 fallback

当前只有一个默认封面，后续首页和每日精读列表会显得重复。

建议生成 6 张 16:9 fallback：

| 文件 | 类别 |
|------|------|
| `cover-science.png` | 科学/宇宙/自然 |
| `cover-business.png` | 商业/经济 |
| `cover-tech.png` | 科技/AI |
| `cover-world.png` | 国际/社会 |
| `cover-culture.png` | 文化/人物 |
| `cover-exam.png` | 考试/学习 |

规格：`1200×675` 源文件，项目内使用压缩版 `600×338`。

#### 9. 成就与积分视觉

当前“我的页”里成就和额度偏 UI 文字化。可以准备小而精的视觉符号。

| 文件 | 用途 |
|------|------|
| `achievement-reader-lv1.png` | 阅读成就徽章 |
| `achievement-reader-lv2.png` | 高阶成就 |
| `credit-ticket.png` | 额度/积分视觉 |

建议小尺寸透明 PNG 或 SVG，`128×128`，≤20KB。

### P2 - 分享和增长物料

#### 10. 朋友圈 1:1 分享图

当前缺少 `onShareTimeline` 需要的 1:1 图。

| 文件 | 规格 |
|------|------|
| `share-timeline-default.png` | 1000×1000，≤300KB |
| `share-timeline-reader.png` | 1000×1000，≤300KB |
| `share-timeline-notes.png` | 1000×1000，≤300KB |

#### 11. 重导出 5:4 分享图

现有分享图构图可保留，但必须重导出轻量版：

```text
1000×800 px
≤300KB
路径保持不变或迁移到 assets/share/
```

#### 12. 公众号/运营封面

不建议放进小程序包内，建议放 CDN 或 docs/marketing。

| 文件 | 规格 |
|------|------|
| `wechat-article-cover.png` | 900×383 |
| `launch-poster-a.png` | 1080×1440 |
| `feature-banner-reading.png` | 1200×628 |

## 生成批次建议

### Batch 1：加载与状态体验

已生成源图：

```text
loading-analysis-fallback.jpg
state-empty.png
state-error-network.png
state-error-timeout.png
state-no-credit.png
empty-history.png
empty-vocab.png
```

这批是后续重构最容易立刻用上的状态体验物料。除 `loading-analysis-fallback.jpg` 已是轻量 JPG 外，其余 PNG 保留高质量源图，接入前统一用 Squoosh 压缩。

### Batch 2：阅读与笔记语言

再生成：

```text
paper-texture-subtle.png
annotation-highlighter-swatch.png
annotation-pencil-underline.png
annotation-grammar-bracket.png
annotation-note-marker.png
annotation-saved-corner.png
note-card-layer.png
brand-watermark.png
```

这批主要用于确定阅读页和批注系统的视觉语言。

### Batch 3：封面与分享系统

最后处理：

```text
cover-science.png
cover-business.png
cover-tech.png
cover-world.png
cover-culture.png
cover-exam.png
share-timeline-default.png
share-timeline-reader.png
share-timeline-notes.png
```

这批图量较大，建议先定统一模板，再批量生成。

## 统一生成风格

建议所有新物料遵循：

- 暖白纸感背景：`#FAF9F9`
- 主墨色：`#121212`
- 品牌蓝：沿用 Logo 蓝，只做点睛
- 辅助高亮：低饱和淡紫 `#B8A8FF`
- 视觉关键词：纸张、阅读、笔记、标注、光圈、安静解析
- 禁止：3D 卡通、霓虹发光、大面积渐变、复杂人物插画、过度拟物

## 推荐下一步

开始生成 **Batch 2：阅读与笔记语言**。这批将用于定义 Claread 批注系统，包括高亮笔触、铅笔下划线、语法括号、边注 marker、收藏角标和笔记卡片层。

## 维护流程

新增或替换资源时：

1. 生成/导出图片或 SVG。
2. 放入对应目录，遵守命名规范。
3. 在本文件“当前真实资源盘点”或“需要准备的物料”中更新状态。
4. 如资源进入小程序包，记录尺寸和体积。
5. 代码接入后运行 `npm run build:weapp` 验证。
6. 大图进入项目之前先压缩；运营图和营销图优先放 CDN 或 docs，不进小程序包。

## 相关文档

- [解析加载页动效包](./loading-animation/README.md)
- [项目 UI/UX 设计规范](../../.impeccable.md)
- [Logo SVG 源文件](../../.temp/Claread%20Logo%E7%89%A9%E6%96%99/Claread_Logo_Kit_SVG/)

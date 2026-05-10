# Claread 静态图片资源清单、审计与 UI/UX 物料路线图

> 日期：2026-05-08  
> 状态：作为静态图片、插画、动效与分享物料的唯一维护文档。  
> 目的：记录当前资源、暴露体积/引用风险，并规划后续 UI/UX 优化所需物料。
> 最近更新：2026-05-08 完成图片压缩替换，包体从 ~18MB 降至 1.51MB。

## 结论

当前 MVP 品牌物料已经基本齐全，图片资源已完成压缩优化，包体已控制在微信小程序主包限制内。

已完成：

1. ~~**压缩/重导出现有大图**~~：✅ Daily Reader 默认封面、分享图、Logo、状态插画已全部 Squoosh 压缩并替换为 JPG，原图已删除。

仍需后续处理：

2. **补齐状态插画与加载动效物料**：解析加载 Lottie、错误、空状态、历史为空、生词本为空都需要统一风格。
3. **建立阅读/笔记场景专属素材**：纸张、标注、文章卡、笔记层这类视觉语言应服务核心阅读体验。
4. **准备分享与传播物料升级版**：需要 1:1 朋友圈图、未来公众号/运营封面。

## 资源目录总览

| 目录 | 当前内容 | 用途 | 审计结论 |
|------|----------|------|----------|
| `client/src/assets/brand/` | 6 个 PNG + 1 个 JPG | 品牌标识系统 | Logo 已压缩为 JPG，其余源资产保留 |
| `client/src/assets/covers/` | 1 个 JPG | Daily Reader 默认封面 | ✅ 已压缩，47.74KB |
| `client/src/assets/images/share/` | 8 个 JPG | 分享卡片图 | ✅ 已压缩，均 ≤65KB |
| `client/src/assets/animations/` | 临时 TS 动画数据 | 解析加载页 Lottie 接入验证 | 等最终 Lottie JSON 替换 |
| `client/src/assets/illustrations/` | 2 个 JPG + 1 个 PNG + 5 个 JPG（未引用） | 状态插画/兜底图 | ✅ 已压缩，已引用的 empty-feedback.jpg 仅 15KB |
| `docs/uiux/loading-animation/` | 概念图、关键帧、brief | 解析加载页动效制作包 | 已准备，可交给 Lottie 制作 |

## 当前真实资源盘点

### Brand

| 文件 | 尺寸 | 体积 | 观察 |
|------|------|------|------|
| `app-icon.png` | 1024×1024 | 98KB | 平台上传用，不应在小程序 UI 中直接引用 |
| `claread-logo.jpg` | — | 39KB | ✅ 登录弹窗引用，已压缩替换原 760KB PNG |
| `claread-icon-fullcolor.png` | 759×759 | 87KB | 适合做源资产，不适合直接小尺寸 UI 引用 |
| `claread-primary-fullcolor.png` | 1254×378 | 291KB | 可用于关于页/品牌页，日常 UI 应做轻量版 |
| `claread-secondary-bilingual.png` | 1195×310 | 257KB | 适合首页/分享品牌区，但仍可压缩 |
| `claread-horizontal-bilingual.png` | 1195×310 | 257KB | 同上 |
| `claread-primary-reversed.png` | 1254×378 | 9.5KB | 体积优秀，可保留 |

#### Brand 使用建议

| 文件 | 建议使用场景 |
|------|--------------|
| `app-icon.png` | 微信公众平台上传，不进入常规 UI |
| `claread-logo.jpg` | 登录弹窗（已替换原 PNG） |
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
| `daily-reader-default.jpg` | — | 47.74KB | ✅ 已压缩替换原 2232KB PNG |

#### Cover 使用场景

- 文章无 `coverImageUrl` 时的视觉 fallback
- 首页 Daily Reader 卡片
- 每日精读详情页 header fallback
- 历史/归档页文章封面 fallback

### Share

| 文件 | 尺寸 | 体积 | 观察 |
|------|------|------|------|
| `app-share.jpg` | — | 45.34KB | ✅ 已压缩替换原 1706KB PNG |
| `daily-reader-01.jpg` | — | 62.05KB | ✅ 已压缩替换原 2048KB PNG |
| `daily-reader-02.jpg` | — | 39.57KB | ✅ 已压缩替换原 1715KB PNG |
| `daily-reader-03.jpg` | — | 46.02KB | ✅ 已压缩替换原 1838KB PNG |
| `daily-reader-04.jpg` | — | 41.42KB | ✅ 已压缩替换原 1820KB PNG |
| `daily-reader-05.jpg` | — | 38.87KB | ✅ 已压缩替换原 1755KB PNG |
| `daily-reader-06.jpg` | — | 39.66KB | ✅ 已压缩替换原 1661KB PNG |
| `daily-reader-07.jpg` | — | 37.24KB | ✅ 已压缩替换原 1716KB PNG |

#### 微信分享规格

| 场景 | 比例 | 建议尺寸 | 体积目标 |
|------|------|----------|----------|
| 好友/群聊分享 | 5:4 | 1000×800 | ≤300KB |
| 朋友圈分享 | 1:1 | 1000×1000 | ≤300KB |
| 公众号封面 | 约 2.35:1 | 900×383 | 不进小程序包，建议 CDN/文档目录 |

当前 5:4 分享图已全部压缩为 JPG，体积均 ≤65KB，远低于 300KB 目标。

## 当前代码引用情况

实际被代码直接引用的图片（2026-05-08 更新）：

- 登录弹窗：`assets/brand/claread-logo.jpg`（原 PNG 已删除）
- Daily Reader 默认封面：`assets/covers/daily-reader-default.jpg`（原 PNG 已删除）
- Daily Reader 分享图：`assets/images/share/daily-reader-01..07.jpg`（原 PNG 已删除）
- 结果页通用分享图：`assets/images/share/app-share.jpg`（原 PNG 已删除）
- 反馈页空状态：`assets/illustrations/empty-feedback.jpg`（原 PNG 已删除）
- 首页空状态：`assets/illustrations/empty-daily-reader.png`（体积 27KB，无需压缩）

未引用但已压缩备用的插画（JPG）：
- `assets/illustrations/empty-history.jpg`、`empty-vocab.jpg`
- `assets/illustrations/state-empty.jpg`、`state-error-network.jpg`、`state-error-timeout.jpg`、`state-no-credit.jpg`

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
client/src/assets/illustrations/state-empty.jpg
client/src/assets/illustrations/state-error-network.jpg
client/src/assets/illustrations/state-error-timeout.jpg
client/src/assets/illustrations/state-no-credit.jpg
client/src/assets/illustrations/empty-history.jpg
client/src/assets/illustrations/empty-vocab.jpg
client/src/assets/illustrations/empty-feedback.jpg
client/src/assets/illustrations/empty-daily-reader.png
```

#### 2. 结果页状态插画

当前 `ResultIllustrations` 还是内联线条 SVG，风格偏临时。建议统一生成一组轻量插画。

| 文件 | 体积 | 状态 |
|------|------|------|
| `state-empty.jpg` | 13.24KB | ✅ 已压缩，待代码接入 |
| `state-error-network.jpg` | 24.29KB | ✅ 已压缩，待代码接入 |
| `state-error-timeout.jpg` | 21.98KB | ✅ 已压缩，待代码接入 |
| `state-no-credit.jpg` | 29.06KB | ✅ 已压缩，待代码接入 |

优先考虑 SVG/Lottie；JPG 只做兜底。

#### 3. 轻量品牌 UI 版本

✅ `claread-logo.jpg`（39KB）已替代原 760KB PNG 用于登录弹窗。

仍需准备的：

| 文件 | 规格 | 用途 |
|------|------|------|
| `brand-icon-ui.png` | 192×192，透明底，≤30KB | 空状态、loading |
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

| 文件 | 体积 | 状态 |
|------|------|------|
| `empty-history.jpg` | 24.08KB | ✅ 已压缩，待代码接入 |
| `empty-vocab.jpg` | 22.81KB | ✅ 已压缩，待代码接入 |
| `empty-feedback.jpg` | 15.11KB | ✅ 已压缩，已代码接入 |
| `empty-daily-reader.png` | 27.37KB | ✅ 已代码接入，体积达标 |

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

#### 11. ~~重导出 5:4 分享图~~

✅ 已完成。现有分享图已全部 Squoosh 压缩为 JPG，体积均 ≤65KB：

```text
1000×800 px (Squoosh resize)
≤65KB (远低于 300KB 目标)
格式：JPG (MozJPEG)
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

✅ 已完成压缩替换（2026-05-08）：

```text
loading-analysis-fallback.jpg     22.36KB  (原已合格)
state-empty.jpg                   13.24KB  (原 PNG 1391KB)
state-error-network.jpg           24.29KB  (原 PNG 1131KB)
state-error-timeout.jpg           21.98KB  (原 PNG 1147KB)
state-no-credit.jpg               29.06KB  (原 PNG 1168KB)
empty-history.jpg                 24.08KB  (原 PNG 1527KB)
empty-vocab.jpg                   22.81KB  (原 PNG 908KB)
empty-feedback.jpg                15.11KB  (原 PNG 1377KB)
empty-daily-reader.png            27.37KB  (原已合格，保持 PNG)
```

所有原图 PNG 已删除，代码 import 路径已更新为 `.jpg`。

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

## 上线前分包配置待办

> 以下问题在本地调试阶段不影响功能，但上线前必须处理。
> 分析日期：2026-05-10

### 当前构建产物体积

| 包 | 体积 | 上限 | 状态 |
|---|---|---|---|
| 主包（含 assets） | 2389.6 KB | 2048 KB | ❌ 超限 |
| 主包（CDN 上线后预估） | ~1752 KB | 2048 KB | ✅ 安全，余量 ~296KB |
| PackageA | 417.9 KB | 2048 KB | ✅ |
| PackageB | 169.4 KB | 2048 KB | ✅ |
| PackageC | 104.2 KB | 2048 KB | ✅ |
| 总计 | 4092.5 KB | 20480 KB | ✅ |

### 待办清单

#### P0：添加 `preloadRule` 分包预下载配置

- **文件**: `client/src/app.config.ts`
- **问题**: 当前未配置 `preloadRule`，用户从主包跳转分包页面时需等待分包下载，微信开发者工具会报异步分包 warning
- **方案**: 在 `app.config.ts` 中添加预下载规则，首页预下载 packageA + packageB，结果页预下载 packageA
- **参考**: [微信官方文档 - 分包预下载](https://developers.weixin.qq.com/miniprogram/dev/framework/subpackages/preload.html)
- **限制**: 同一分包的页面共享 2MB 预下载额度

#### P1：`packOptions.ignore` 排除 `.map` 文件

- **文件**: `client/project.config.json`
- **问题**: `packOptions.ignore` 为空，构建产物中 5 个 `.map` 文件（共 ~313KB）在开发预览时被计入包体积，导致体积报告偏大
- **方案**: 添加 `{ "type": "file", "value": ".map" }` 到 `packOptions.ignore`
- **注意**: `uploadWithSourceMap: true` 保证线上调试仍可用 source map，此处仅排除本地预览打包

#### P1：开启 `lazyloadPlaceholderEnable`

- **文件**: `client/project.config.json`
- **问题**: 当前为 `false`，跨分包组件加载时无占位，可能出现白屏闪烁
- **方案**: 设为 `true`，配合 `preloadRule` 实现平滑加载
- **参考**: [微信官方文档 - 占位组件](https://developers.weixin.qq.com/miniprogram/dev/framework/custom-component/placeholder.html)

#### P2：生产构建关闭 source map

- **文件**: `client/config/index.ts`
- **问题**: 当前构建产物始终包含 `.map` 文件，生产环境不需要
- **方案**: `mini.enableSourceMap` 按环境变量控制，`build:weapp` 时关闭

#### P2：关注主包余量

- **现状**: CDN 上线后主包约 1752KB，距 2MB 上限仅余 ~296KB
- **风险**: `common.js`（395KB）和 `pages/result/index.js`（334KB）是最大贡献者，后续功能迭代可能再次逼近上限
- **预案**: 若主包再次超限，考虑将 `pages/result/` 拆为独立分包，或用 Taro `mini.addChunkPages` 精细拆分公共依赖

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

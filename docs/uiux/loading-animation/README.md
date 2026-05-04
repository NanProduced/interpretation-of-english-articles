# Claread 解析加载页动效包

> 创建日期：2026-05-04  
> 目标：为解析加载页制作一版轻量、可循环、可落地到微信小程序的 Lottie 动效。

## 方向选择

采用概念图中的 **A 方案**：光圈 Logo 聚合，文章骨架浮现，一道半透明高亮笔扫过文本线。

这个方向最贴合 Claread 的核心动作链：

```text
文章进入解析 → 结构出现 → 重点被标注 → 输出精读结果
```

Logo 只作为中心锚点，不做纯品牌空转动画。

## 文件说明

```text
docs/uiux/loading-animation/
├── loading-concepts-abcd.png              # 四宫格概念图，A 为推荐方向
├── README.md                              # 本说明
├── lottie-agent-brief.md                  # 给 Lottie 制作 agent 的执行 brief
├── assets/
│   └── claread-icon-fullcolor.svg         # 当前品牌图形标志源文件
└── keyframes/
    ├── 00-rest.svg                        # 静息状态
    ├── 01-logo-assemble.svg               # Logo 聚合/显现
    ├── 02-lines-emerge.svg                # 文章骨架线浮现
    ├── 03-highlight-sweep.svg             # 高亮笔划过
    ├── 04-settled-loop.svg                # 回到可循环的安静状态
    └── contact-sheet.svg                  # 关键帧总览
```

## 动效规格

- 输出格式：Lottie JSON
- 画布尺寸：`240x240` 或 `320x320`
- 时长：`2.8s`
- 帧率：`30fps`
- 循环：无缝 loop
- 体积目标：`30-80KB`，上限 `150KB`
- 小程序播放：`lottie-miniprogram`

## 运动节奏

| 时间 | 动作 |
|------|------|
| `0.00s - 0.45s` | 纸张底轻微浮现，Logo 从 96% opacity 到 100%，可有极轻 scale |
| `0.45s - 1.05s` | 文章骨架线从左到右淡入 |
| `1.05s - 1.85s` | 高亮笔扫过第二行，带轻微手写角度 |
| `1.85s - 2.45s` | 画面安静停留，状态文案切换 |
| `2.45s - 2.80s` | 整体回到初始强度，准备无缝循环 |

缓动建议：`cubic-bezier(0.16, 1, 0.3, 1)`。不要弹跳、旋转过度、粒子、发光。

## 颜色

- 页面背景：`#FAF9F9`
- 纸张：`#FFFFFF`，透明度 `0.76 - 0.86`
- 主墨色：`#121212`
- Logo 蓝色：沿用品牌 SVG
- 高亮笔：`#B8A8FF`，透明度 `0.22 - 0.34`
- 细线透明度：`0.04 - 0.12`

## 图层建议

关键帧 SVG 已按 Lottie 制作需要做了图层命名：

```text
ambient-hairlines      # 背景环境细线，低透明度慢速漂移即可
paper-stack            # 纸张主容器与背层，轻微 opacity/scale
logo-aperture          # 品牌光圈 Logo，中心锚点，不使用旧 C
article-lines          # 文章骨架线和高亮笔触
native-status-text     # 仅供画面参考，最终建议由小程序原生 UI 渲染
```

制作 Lottie 时优先还原 `paper-stack`、`logo-aperture`、`article-lines`、`highlighter stroke` 四个核心层。纸张纹理和细线是质感增强项，不应牺牲性能。

## 注意

- 不要再使用旧的字母 `C` 标识。
- Logo 应使用 `assets/claread-icon-fullcolor.svg` 或同等矢量源。
- 尽量用 Lottie shape layer，不要把每帧图片打包进 JSON。
- 如果工具必须栅格化，需控制总资源体积，并优先做静态兜底。

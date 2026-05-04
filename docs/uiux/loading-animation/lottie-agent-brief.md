# Lottie Agent Brief

请基于本目录素材，为 Claread 小程序“解析加载页”制作 Lottie 动画。

## 输入素材

- 概念图：`loading-concepts-abcd.png`
- 推荐方向：A 方案
- 品牌图形：`assets/claread-icon-fullcolor.svg`
- 关键帧参考：`keyframes/*.svg`

## 交付物

请输出：

```text
client/src/assets/animations/claread-analysis-loading.json
```

并可选输出预览：

```text
docs/uiux/loading-animation/preview/claread-analysis-loading.gif
docs/uiux/loading-animation/preview/claread-analysis-loading.mp4
```

## 动画内容

1. 暖白纸张容器轻微显现。
2. Claread 光圈 Logo 作为中心视觉，不使用字母 C。
3. 3-4 条文章骨架线从左到右淡入。
4. 一道低饱和淡紫高亮笔扫过第二行。
5. 状态文案可由小程序原生 UI 承担，Lottie 内不要放中文文字，避免字体和国际化问题。
6. 结尾回到接近初始状态，保证循环不跳。

## 视觉质量要求

- 画面应像“纸张正在被安静地读懂”，不是普通 loading spinner。
- Logo 可以有极轻的 scale/opacity 呼吸，但不要持续旋转。
- 文章骨架线淡入应有左右方向感，像排版逐步落位。
- 高亮笔触应略带手写曲线，不要做成机械直矩形。
- 蓝色只作为品牌段和细节回应，不能大面积铺色。
- 纸张背层、环境线、微弱纹理是高级感来源，但总复杂度要受控。

## 技术限制

- 目标运行环境：微信小程序 + `lottie-miniprogram`
- 避免 expression，小程序不支持。
- 避免复杂 mask、过多 path 点、位图序列帧、大面积 blur。
- Lottie JSON 体积优先控制在 `80KB` 内。
- Logo 如果无法稳定导入为 shape，可作为单个 SVG/PNG 资产，但需说明体积影响。

## 建议图层

```text
paper-container
paper-shadow-sheet
logo-aperture
article-line-1
article-line-2
article-line-3
highlighter-stroke
ambient-hairlines
```

## 小程序接入位置

当前工程已有 Lottie 播放组件：

```text
client/src/components/LottieAnimation/
```

当前加载页：

```text
client/src/components/ActiveLoading/
```

生成最终 JSON 后，将 `ActiveLoading` 中的临时 animation data 替换为最终 JSON 即可。

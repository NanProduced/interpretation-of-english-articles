# 前端说明

这里是 Claread透读 的微信小程序前端工作区，当前基于 `Taro + React + TypeScript + Sass + Zustand` 开发。

## 当前主要页面

- 首页
- 文章输入页
- 解读结果页
- 历史记录页
- 我的页面

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

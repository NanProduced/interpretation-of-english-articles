# Design

## Design Language

参考方向是“轻质纸张阅读器”，不是工具软件：

- 背景：warm paper、pure white、pale sage 三种低噪声阅读底。
- 文字：英文正文最高权重，译文次级，工具层再后置。
- 浮层：白色或轻纸色，圆角克制，阴影极轻，像纸页上浮起的小托盘。
- 图标：使用 lucide 风格线性图标，线宽统一，不用 emoji。
- 颜色：用户批注使用暖黄、浅蓝、柔绿三色，饱和度低；AI 标注继续使用当前语义下划线系统。

## Visual Separation

AI 标注：

- 来源于系统解析。
- 使用细下划线、语法卡、术语卡、句式卡。
- 视觉像“阅读助手的铅笔线”。

用户批注：

- 来源于用户主动选择。
- 使用淡色高亮、页边小标记、句后小纸条。
- 视觉像“私人读书笔记”。

两者不能共用同一高亮色。用户高亮默认用非常淡的 warm yellow，不能和译文同步高亮的黄色混淆；激活态可以稍微加深。

## Reading Settings Sheet

入口：

- 顶部更多菜单内：`阅读设置`
- 或阅读页底部轻量工具层中的 `Aa`

布局：

- bottom sheet，高度约 44%-52% 屏幕。
- 顶部为四个阅读模式 icon：阅读、护眼、收藏、更多。
- 设置区使用分组，不使用卡片嵌套。

控件：

- 字号：四档 segmented control，使用 `A` 大小变化表达。
- 行距、段距：三档 segmented control。
- 译文显示：隐藏 / 淡显 / 标准。
- 背景：三个圆形色块。
- 标注强度：克制 / 标准 / 明显。

## Selection Toolbar

首版不依赖系统拖选浮层，而采用 Claread 自定义长按工具栏：

- 用户长按英文句子、中文译文或段落。
- 句子进入淡蓝选中态。
- 上方或下方浮出小工具条。

工具条项目：

- 高亮
- 笔记
- 复制
- 收藏
- 反馈

如果选区是英文单词或短语，可以额外显示 `查词`。

## Note Sheet

用户点击“笔记”后：

- bottom sheet 高度约 42%-55%。
- 顶部显示选中文段，最多 3 行。
- 下方为笔记输入区域。
- 可选高亮颜色：暖黄 / 浅蓝 / 柔绿。
- 主按钮：保存笔记。
- 次按钮：仅高亮。

保存后：

- 正文中显示用户高亮。
- 句末显示轻量 note dot 或边注短线。
- 点击 note dot 打开笔记详情。

## Favorites

收藏不单独做大浮层：

- 工具栏点击收藏后即时完成。
- 已收藏句段在正文右侧或句末显示轻书签标记。
- 收藏列表复用现有历史/收藏页面，但需要支持 `sentence`、`paragraph` target type 的展示。

## Motion

- 工具栏出现：150-220ms opacity + translateY。
- 设置 sheet：使用已有 bottom sheet 进入节奏。
- 保存笔记：按钮轻微 scale/opacity，不使用跳动动画。
- 高亮落下：淡色背景 180ms fade-in。

## Reference Assets

本目录只收录外部参考图，不作为逐像素设计稿。实现时需要吸收其质感、层级、控件节奏，再转译为 Claread 的纸感阅读语言。

- [assets/reference-reading-app-1.webp](assets/reference-reading-app-1.webp)
  - 用于参考阅读器整体质感：浅纸色背景、书页边框、阅读设置 bottom sheet、浅蓝灰控制色。
  - 可借鉴设置抽屉的安静氛围，但不要照搬章节、滚动、亮度等完整电子书能力。
- [assets/reference-reading-app-2.webp](assets/reference-reading-app-2.webp)
  - 用于参考文本选择与悬浮工具栏：蓝色选区手柄、白色浮动工具条、图标分隔、底部阅读控制层。
  - Claread 首版先做长按句子/段落工具栏；任意拖选作为后续增强。
- [assets/reference-note-app-1.webp](assets/reference-note-app-1.webp)
  - 用于参考笔记/批注工具的表达：高亮、颜色选择、工具条、笔记编辑入口。
  - Claread 需要更克制，不做复杂富文本编辑器；首版只做高亮颜色、笔记、复制、收藏。

# Feedback UI And Interaction Spec

## Visual References

Use the approved PNG references before implementing any feedback UI:

- `assets/feedback-entry-reader.png`
- `assets/feedback-sheet-annotation.png`
- `assets/feedback-sheet-dictionary.png`
- `assets/feedback-app-page.png`
- `assets/feedback-my-feedback.png`
- `assets/feedback-interaction-flow.png`

These references are aligned to the reading annotation target viewport size and visual language. If code and old screenshots disagree, follow these approved assets and this spec.

## Surface Model

反馈系统只允许三类表面：

| Surface | 用途 | 规则 |
| --- | --- | --- |
| Inline entry | 阅读、标注、单词 sheet 中的轻量入口 | 不展开完整表单，只承载“有帮助 / 不准确 / 反馈”等动作 |
| Bottom sheet | 解析、标注、词典等上下文反馈 | 用户主动点击后出现，宽度跟 viewport 一致，避免窄侧栏 |
| Full page | 应用功能反馈、我的反馈 | 用于长文本、列表、筛选和状态查看 |

禁止使用小程序左侧窄抽屉承载反馈表单。当前截图里的左侧反馈面板宽度不足、遮挡层关系混乱，并且与词典 sheet 形成嵌套弹层，应在重构中移除。

## Entry Patterns

### Annotation Feedback Entry

标注卡片底部使用三按钮行：

- `有帮助`
- `不准确`
- `反馈`

行为：

| Action | Behavior |
| --- | --- |
| 有帮助 | 直接提交 `feedback_scope='annotation'`, `sentiment='positive'`, `feedback_type='helpful'` |
| 不准确 | 打开 annotation bottom sheet，并预选 `inaccurate` |
| 反馈 | 打开 annotation bottom sheet，不预选类型 |

按钮视觉：

- 高度 48rpx 到 56rpx。
- 使用 Lucide `thumbs-up`, `thumbs-down`, `message-square` 或项目 `LucideIcon` 中最接近的图标。
- 默认灰度，选中后只用轻微纸色底和文字加深，不使用强色块。

### Dictionary Feedback Entry

词典 full sheet 底部保留次级 `反馈` 按钮。点击后打开 dictionary bottom sheet。

词典反馈只收集负面问题：

- 释义错误
- 释义缺失
- 词性标注有误
- 音标有误
- 例句不当
- 其他问题

不要在 mini lookup slip 里塞完整反馈表单。mini slip 只保留快速动作，详细反馈必须进入 full sheet 或 bottom sheet。

### Article-End Feedback Entry

文章末尾反馈应是轻量收尾，不是大卡片表单。

默认布局：

1. 一条细分隔线。
2. 文案：`本次解读对你有帮助吗？`
3. 两个圆形 icon 按钮：有帮助、不准确。
4. 次级文字按钮：`写反馈`。

行为：

| Action | Behavior |
| --- | --- |
| 有帮助 | 直接提交 `analysis_result/thumbs_up` |
| 不准确 | 打开 bottom sheet，并预选一个通用负面入口 |
| 写反馈 | 打开 bottom sheet，允许选择负面类型并补充说明 |

### App Feedback Page

应用功能反馈使用独立页面，不应该和阅读 overlay 混用。

页面结构：

1. 标题区：`意见反馈`，副文案一句以内。
2. 分类 segmented/chip 区。
3. 描述 textarea，最小高度 220rpx。
4. 提交按钮。
5. 提交成功后的 inline success panel。
6. `我的反馈`入口。

分类：

- Bug 报告
- 功能建议
- 额度问题
- 输入页问题
- 体验问题
- 其他

提交按钮禁用时应在按钮上方或下方显示轻提示：

- 未选分类：`请选择反馈类型`
- 未填描述：`请补充问题描述`

不要只把按钮变灰。

## Bottom Sheet Anatomy

所有上下文反馈 bottom sheet 使用同一结构：

1. Drag handle。
2. Header：标题 + 关闭按钮。
3. Context summary：自动采集的上下文摘要，只展示 1 到 2 行。
4. Issue category：2 列或单列选项，按场景决定。
5. Optional note：补充说明。
6. Submit row：主按钮 + 次级取消。
7. Success state：提交后替换表单内容，而不是立刻关闭。

推荐文案：

| Scope | Title | Context Summary |
| --- | --- | --- |
| annotation | 反馈标注 | 显示标注标题或原句片段 |
| dictionary | 反馈词典 | 显示 word、phonetic、当前释义 |
| analysis_result | 反馈本次解读 | 显示文章标题或阅读目标 |

## Form Layout Rules

- Sheet 背景使用 `--reader-paper` 或接近暖纸色。
- Sheet 顶部圆角 32rpx 到 40rpx。
- 表单横向 padding 32rpx 到 40rpx。
- 选项按钮高度至少 72rpx。
- 选项文字 28rpx，行高 1.35 到 1.45。
- 不使用 emoji 作为正式图标。
- 不使用纯白大卡片堆叠。
- 不在 sheet 中再打开另一个 sheet。

## My Feedback

“我的反馈”不是简单列表，应展示用户能理解的处理状态。

列表项字段：

- 反馈场景：词典、标注、整篇解读、应用问题。
- 用户选择的问题类型。
- 内容摘要。
- 状态标签。
- 提交时间。
- 如有奖励，显示 `+N 积分`。
- 如有处理结果，显示一行团队回复。

状态文案：

| Status | User Label | Meaning |
| --- | --- | --- |
| pending | 已收到 | 还未评审 |
| triaged | 已进入处理 | 已分类或排期 |
| adopted | 已采纳 | 确认有效，可能发放奖励 |
| resolved | 已处理 | 问题已修复或内容已更新 |
| dismissed | 未采纳 | 暂不处理，需要给出简短原因 |

当前后端只有 `pending/adopted/resolved/dismissed`。短期前端按这四个状态映射，长期建议补 `triaged` 和用户可见 `resolution_note`。

## Success And Follow-Up

提交成功后不要只显示 toast。推荐成功态：

标题：`已收到反馈`

正文：

- 上下文反馈：`我们已记录这处内容。你可以在「我的反馈」查看处理状态。`
- 应用反馈：`感谢说明。处理结果会出现在「我的反馈」中。`

动作：

- `知道了`
- `查看我的反馈`

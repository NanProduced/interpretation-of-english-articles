# Feedback System Implementation Handoff

把这段交给干净会话中的 agent，用 plan mode 执行。

```text
你要重构 Claread 小程序反馈系统。先阅读：

1. PRODUCT.md
2. docs/uiux/feedback-system/README.md
3. docs/uiux/feedback-system/product-brief.md
4. docs/uiux/feedback-system/ui-interaction-spec.md
5. docs/uiux/feedback-system/workflow-and-data-spec.md
6. docs/uiux/feedback-system/current-implementation-audit.md
7. specs/feedback-system/README.md
8. specs/feedback-system/design.md

同时打开并对照这些已采纳设计图：

- docs/uiux/feedback-system/assets/feedback-entry-reader.png
- docs/uiux/feedback-system/assets/feedback-sheet-annotation.png
- docs/uiux/feedback-system/assets/feedback-sheet-dictionary.png
- docs/uiux/feedback-system/assets/feedback-app-page.png
- docs/uiux/feedback-system/assets/feedback-my-feedback.png
- docs/uiux/feedback-system/assets/feedback-interaction-flow.png

目标：

- 反馈不是临时弹窗，而是完整质量闭环。
- 阅读内反馈入口要轻，详细反馈统一使用 bottom sheet。
- 不再使用左侧窄反馈面板。
- 应用功能反馈使用独立页面。
- “有帮助”是一键提交；“不准确/反馈”才打开表单。
- 提交成功后显示内联成功态，并能去“我的反馈”。
- “我的反馈”要展示用户能理解的状态和奖励。
- 兼容现有 /feedback API，除非确有必要，不先改后端 schema。

请先做 codebase audit，不要直接改代码。输出：

1. 当前反馈组件和入口清单。
2. 哪些文件需要改。
3. 是否需要后端/API 小改动。
4. 分阶段实施计划。
5. 第一阶段要交付的最小可验证 UI。

设计约束：

- 小程序 Taro 3 + React。
- 使用 rpx。
- 使用项目现有 LucideIcon，不使用 emoji 或外部 SVG。
- 保持 Claread 的安静、纸感、阅读优先风格。
- 不引入微信订阅消息，不收集联系方式。
- 不把反馈表单做成客服系统。
```

## First Implementation Slice

建议第一阶段只做体验统一，不先扩后端：

1. 新建通用 `FeedbackSheet`。
2. `AnnotationFeedback` 和 `DictionaryFeedback` 复用 `FeedbackSheet`。
3. `FeedbackWidget` 从大卡片改为文章末尾轻量 feedback row。
4. App feedback page 去掉 emoji 和后台式大卡片，补足禁用说明和成功态。
5. My feedback page 优化状态文案，暂不显示不准确的总数。

## Acceptance Criteria

- 阅读中不出现左侧窄反馈面板。
- dictionary sheet 和 feedback sheet 不互相嵌套遮挡。
- annotation 卡片中 `有帮助` 可一键提交。
- `不准确` 可打开反馈 sheet 并预选问题。
- app feedback 未满足提交条件时有明确提示。
- 提交成功后不只依赖 toast。
- WeChat Mini Program build 通过。

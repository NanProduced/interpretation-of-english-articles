# Claread Feedback System

本目录是 Claread 反馈系统重构的 UI/UX 与产品闭环规范。它独立于阅读标注系统，原因是反馈不只是一个按钮或弹层，还包括问题分类、上下文采集、存储、团队评审、处理状态、奖励与用户可见的后续结果。

现有工程规格在 `specs/feedback-system/`，本目录负责补足体验设计与执行口径。后续 agent 做反馈系统时，应同时阅读这两个目录：

1. `docs/uiux/feedback-system/README.md`
2. `docs/uiux/feedback-system/product-brief.md`
3. `docs/uiux/feedback-system/ui-interaction-spec.md`
4. `docs/uiux/feedback-system/workflow-and-data-spec.md`
5. `docs/uiux/feedback-system/current-implementation-audit.md`
6. `docs/uiux/feedback-system/implementation-handoff.md`
7. `specs/feedback-system/README.md`
8. `specs/feedback-system/design.md`

## Scope

反馈系统覆盖四类入口：

| Scope | 用户入口 | 主要目的 |
| --- | --- | --- |
| `analysis_result` | 文章末尾整体反馈 | 判断本次解析质量是否有帮助 |
| `annotation` | 语法卡片、句子卡片、标注详情 | 定位具体标注是否有误或有用 |
| `dictionary` | 单词详情 sheet | 收集词典释义、音标、词性、例句问题 |
| `app` | 设置/个人页的意见反馈 | 收集非解析类 bug、建议、额度、体验问题 |

## Approved Assets

这些图片是当前采纳版本。后续 agent 不要使用早期草稿，也不要重新引入左侧窄抽屉样式。

| File | Purpose |
| --- | --- |
| `assets/feedback-entry-reader.png` | 阅读页内的轻量反馈入口，包括标注卡片反馈行和文章末尾反馈行 |
| `assets/feedback-sheet-annotation.png` | 标注反馈 bottom sheet，展示上下文摘要、问题选项、补充说明和提交动作 |
| `assets/feedback-sheet-dictionary.png` | 词典反馈 bottom sheet，展示单词上下文和词典问题分类 |
| `assets/feedback-app-page.png` | 应用功能反馈独立页，覆盖分类、描述、禁用提示和“我的反馈”入口 |
| `assets/feedback-my-feedback.png` | 用户侧反馈记录页，覆盖处理状态、团队回传和奖励积分 |
| `assets/feedback-interaction-flow.png` | 反馈系统交互闭环图 |

## Design Position

反馈是“安静的质量回路”，不是阅读页面的主功能。

- 默认状态下，反馈入口要轻，不打断阅读。
- 用户主动点击后，反馈表单要清晰、稳定、可撤回。
- 提交后必须给出明确状态，不只显示 toast。
- 用户应能在“我的反馈”里看到状态、处理结果和奖励。
- 团队应能根据反馈上下文完成评审与修正，而不是只收到一段孤立文本。

## Relationship With Reading Annotation

`docs/uiux/reading-annotation-system/` 只定义反馈入口在阅读、标注、单词卡片里的位置和视觉轻重。本目录定义完整反馈流程：

- 入口点击后打开什么界面。
- 不同场景用什么问题分类。
- 需要采集哪些上下文。
- 如何存储、去重、评审、奖励。
- 处理结果如何回到用户侧。

阅读标注实现时，不要在标注文档里重新设计反馈表单。应复用本目录的组件与流程规范。

## Non-Goals

- 不在本目录设计阅读设置抽屉。
- 不重新设计单词卡片与词典 sheet 的主体内容。
- 不引入微信订阅消息推送作为默认反馈通知。
- 不收集手机号、邮箱、微信号等联系方式。
- 不把反馈表单做成重型客服系统。

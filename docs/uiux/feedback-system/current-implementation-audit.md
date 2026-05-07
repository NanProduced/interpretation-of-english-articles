# Current Implementation Audit

本审计基于当前代码与小程序截图，重点不是判定代码是否能跑，而是评估它是否达到 Claread 的反馈体验标准。

## Existing Files

Frontend:

- `client/src/components/AnnotationFeedback/index.tsx`
- `client/src/components/AnnotationFeedback/index.scss`
- `client/src/components/DictionaryFeedback/index.tsx`
- `client/src/components/DictionaryFeedback/index.scss`
- `client/src/components/FeedbackWidget/index.tsx`
- `client/src/components/FeedbackWidget/index.scss`
- `client/src/packageC/feedback/index.tsx`
- `client/src/packageC/feedback/index.scss`
- `client/src/packageC/feedback/my-feedback.tsx`
- `client/src/packageC/feedback/my-feedback.scss`
- `client/src/services/api/feedback.client.ts`

Backend:

- `server/app/schemas/feedback.py`
- `server/app/services/feedback/service.py`
- `server/app/api/routes/feedback.py`
- `server/app/api/routes/internal_feedback.py`

Specs:

- `specs/feedback-system/`

## What Works

- 后端已有统一 `feedback` scope/type/sentiment 模型。
- 词典、标注、整篇解析、应用反馈四个场景已经被枚举。
- 前端已经有可提交的基础组件。
- “我的反馈”和内部状态 API 已有雏形。
- 采纳奖励和积分流水在工程规格里已有方向。

## Major UX Problems

### 1. Surface inconsistency

当前反馈同时出现为左侧窄面板、阅读底部卡片、独立页面和 sheet 叠层。用户无法形成稳定心智，agent 也很难把视觉调准。

Fix:

- 上下文反馈统一为 bottom sheet。
- 应用反馈统一为 full page。
- 阅读内只保留轻量入口。

### 2. Left drawer is wrong for mini program reading

截图里的左侧反馈面板宽度过窄，按钮和文字被挤压，并且覆盖在 dictionary sheet 之上，形成嵌套 overlay。它不像 Claread 的纸感阅读系统，更像临时调试面板。

Fix:

- 删除窄侧栏模式。
- 使用全宽底部 sheet，最多 80vh。
- 与 WordPopup sheet 不同时展开，必要时先收起词典 sheet 再打开反馈 sheet。

### 3. Positive and negative actions are mixed

`AnnotationFeedback` 当前把“正面反馈”和“问题反馈”放在同一个表单里。对用户来说，“有帮助”应该是一键动作，不应该进入完整表单。

Fix:

- `有帮助` 直接提交。
- `不准确` 打开表单并预选负面类型。
- `反馈` 打开表单让用户选择。

### 4. Disabled state has no explanation

多个截图里提交按钮只是灰掉，用户不知道还缺分类还是缺文本。

Fix:

- 禁用按钮附近显示缺失条件。
- app 反馈页必须选择分类并填写描述。
- annotation/dictionary 反馈只需选择类型，补充说明可选。

### 5. Success state is too weak

当前主要依赖 toast。toast 消失后，用户不知道反馈后续会怎样，也不知道“我的反馈”在哪里。

Fix:

- 表单提交后显示内联成功态。
- 提供 `知道了` 与 `查看我的反馈`。
- 如果后端 upsert 到已有记录，文案使用 `已更新你的反馈`。

### 6. My feedback count is inaccurate

`FeedbackPage` 使用 `fetchFeedbackList({ limit: 1 })` 后取 `res.items.length`，只能得到 0 或 1，不是总数。

Fix:

- 短期显示 `我的反馈` 不显示数量。
- 或后端 `GET /feedback/stats/me` 返回用户反馈总数。

### 7. My feedback lacks resolution detail

当前列表只有状态、内容、奖励。用户无法知道为什么被采纳、为什么关闭、是否已经修正。

Fix:

- 后续 API 加 `resolution_note`。
- 前端列表至少展示状态解释文案。

### 8. Visual language is too generic

页面使用 `#fff` 卡片、emoji 图标、圆角大卡片和普通后台表单风格，和 Claread 的纸感阅读系统不一致。

Fix:

- 使用 reader paper tokens。
- 用 LucideIcon 替代 emoji。
- 降低卡片感，强化表单节奏和信息层级。

## Engineering Gaps

- 前端组件重复：`AnnotationFeedback`、`DictionaryFeedback`、`FeedbackWidget` 都有相似选项、textarea、submit 状态。
- 建议抽象 `FeedbackSheet`、`FeedbackOptionList`、`FeedbackSuccessState`。
- `FeedbackSubmitResult` 不包含是否 upsert 更新的信息，无法区分首次提交和更新。
- `FeedbackListItem` 信息不足，无法做好“我的反馈”详情。
- 内部评审只有 API，没有 UI/流程规范。

## Recommended Refactor Order

1. 统一反馈表面：删除左侧窄面板，做 `FeedbackSheet`。
2. 统一数据枚举：前端选项从同一个 scope config 派生。
3. 改造 annotation/dictionary/article-end 入口行为。
4. 改造 app feedback page 的视觉和禁用说明。
5. 改造 success state 与“我的反馈”入口。
6. 修复“我的反馈”数量和状态文案。
7. 设计内部 review queue 和 `resolution_note` 后端扩展。


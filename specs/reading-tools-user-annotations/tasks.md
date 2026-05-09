# Tasks

## Phase 1: Reading Preferences

- [ ] 定义前端 `ReadingPreferences` 类型和默认值。
- [ ] 将阅读设置映射为 CSS 变量：字号、行距、译文透明度、背景。
- [ ] 新增 `ReadingSettingsSheet`。
- [ ] 在结果页顶部更多菜单或阅读工具入口接入设置 sheet。
- [ ] 通过 `/auth/profile` 保存用户阅读偏好。
- [ ] 初始化时从 session user settings/metadata 合并偏好。
- [ ] 验证设置变化不破坏单词弹窗、AI 标注、高亮同步。

## Phase 2: Sentence Action Toolbar

- [ ] 为句子、译文、段落增加长按事件。
- [ ] 构造句子/段落级 `SelectionContext`：record_id、paragraph_id、sentence_id、原文、译文、锚点类型。
- [ ] 新增 `ReadingSelectionToolbar`。
- [ ] 工具条使用固定底部浮层，不依赖文本选区 rect。
- [ ] 实现复制原文、复制译文、复制双语。
- [ ] 实现收藏句子/段落，复用 `/favorites`。
- [ ] 接入反馈入口，自动带上下文。
- [ ] 不接入查词/解释入口；单词查词继续使用点按单词。

## Phase 3: User Annotations Backend

- [ ] 新增 migration：`user_annotations`。
- [ ] 新增 `server/app/schemas/user_assets/annotations.py`。
- [ ] 新增 `server/app/services/user_assets/annotations.py`。
- [ ] 新增 `server/app/api/routes/user_annotations.py`。
- [ ] 注册 router。
- [ ] 增加测试：创建、列表、更新、软删除、用户隔离。

## Phase 4: User Annotations Frontend

- [ ] 新增 `userAnnotations.client.ts`。
- [ ] 新增本地 VM 类型：`UserAnnotationVm`。
- [ ] 新增 `UserNoteSheet`。
- [ ] 在正文中渲染句子/段落级用户高亮和 note dot。
- [ ] 支持编辑、删除笔记。
- [ ] 重新进入结果页时加载当前 record 的用户批注。
- [ ] 收藏状态与用户批注状态分离显示。

## Phase 5: Polish & QA

- [ ] 长按句子不会触发单词卡片误弹。
- [ ] 长按句子不产生任意文本范围选区或拖拽手柄。
- [ ] 点击 AI 标注不触发用户工具栏。
- [ ] 用户高亮不覆盖 AI 标注语义线。
- [ ] 译文隐藏后复制双语仍可从数据层取到译文。
- [ ] 字号/行距变化后词卡定位仍合理。
- [ ] 未登录状态下复制可用，收藏/笔记有清晰提示。
- [ ] `npm run build:weapp` 通过。

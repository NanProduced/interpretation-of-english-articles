# Tasks

## Phase 1: Reading Preferences

- [x] 定义前端 `ReadingPreferences` 类型和默认值。
- [x] 将阅读设置映射为 CSS 变量：字号、行距、译文透明度、背景。
- [x] 新增 `ReadingSettingsSheet`。
- [x] 在结果页顶部更多菜单或阅读工具入口接入设置 sheet。
- [x] 通过 `/auth/profile` 保存用户阅读偏好。
- [x] 初始化时从 session user settings/metadata 合并偏好。
- [x] 验证设置变化不破坏单词弹窗、AI 标注、高亮同步。

## Phase 2: Sentence Action Toolbar

- [x] 为英文句子和对应译文增加长按事件；译文长按锚定到当前句子。
- [x] 构造句子级 `SelectionContext`：record_id、paragraph_id、sentence_id、原文、译文、锚点类型。
- [x] 新增 `ReadingSelectionToolbar`。
- [x] 工具条使用固定底部浮层，不依赖文本选区 rect。
- [x] 实现复制原文、复制译文、复制双语。
- [x] 实现收藏句子，复用 `/favorites`。
- [x] 接入反馈入口，自动带上下文。
- [x] 不接入查词/解释入口；单词查词继续使用点按单词。

## Phase 3: User Annotations Backend

- [x] 新增 migration：`user_annotations`。
- [x] 新增 `server/app/schemas/user_assets/annotations.py`。
- [x] 新增 `server/app/services/user_assets/annotations.py`。
- [x] 新增 `server/app/api/routes/user_annotations.py`。
- [x] 注册 router。
- [x] 增加测试：创建、列表、更新、软删除、用户隔离。

## Phase 4: User Annotations Frontend

- [x] 新增 `userAnnotations.client.ts`。
- [x] 新增本地 VM 类型：`UserAnnotationVm`。
- [x] 新增 `UserNoteSheet`。
- [x] 在正文中渲染句子级用户高亮和 note dot。
- [x] 支持编辑、删除笔记。
- [x] 重新进入结果页时加载当前 record 的用户批注。
- [x] 收藏状态与用户批注状态分离显示。

## Phase 5: My Excerpts

- [x] 在“我的”页新增 `我的摘录` 入口。
- [x] 新增 `packageA/excerpts/index` 页面。
- [x] 按文章归组展示句子资产。
- [x] 同一句子的收藏、高亮、笔记合并展示。
- [x] 顶部提供全部 / 收藏 / 高亮 / 笔记 / 解析筛选。
- [x] 同一文章下按句子顺序正序排列，不按操作时间排序。
- [x] 在句子卡内展示完整语法/句析复习要点。

## Phase 6: Polish & QA

- [x] 长按句子不会触发单词卡片误弹。
- [x] 长按句子不产生任意文本范围选区或拖拽手柄。
- [x] 点击 AI 标注不触发用户工具栏。
- [x] 用户高亮不覆盖 AI 标注语义线。
- [x] 译文隐藏后复制双语仍可从数据层取到译文。
- [x] 字号/行距变化后词卡定位仍合理。
- [x] 未登录状态下复制可用，收藏/笔记有清晰提示。
- [x] `npm run build:weapp` 通过。
- [ ] 后端测试环境缺少 `datasette` 依赖，pytest 暂未作为本轮收尾验收依据。

## Deferred

- [ ] P2：从“我的摘录”跳回解析页后精确滚动定位到目标句，暂不纳入本轮。

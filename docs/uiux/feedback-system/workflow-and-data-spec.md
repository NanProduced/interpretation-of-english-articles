# Feedback Workflow And Data Spec

## Lifecycle

反馈生命周期应覆盖用户、系统、评审人员和回传结果：

1. Capture：用户从具体场景提交反馈。
2. Normalize：前端按 scope/type/sentiment 结构化提交。
3. Store：后端 upsert，保存上下文快照。
4. Triage：团队按 scope、类型、频次、严重度评审。
5. Act：修正词典、调整标注规则、修复 UI bug 或记录产品建议。
6. Resolve：更新反馈状态和处理说明。
7. Reward：采纳高价值反馈时发放积分。
8. Return：用户在“我的反馈”和积分明细看到结果。
9. Harvest：可用于 RAG 或规则改进的数据标记 `rag_harvested`。

## Status Model

现有后端状态：

| Status | Meaning | User-facing Label |
| --- | --- | --- |
| `pending` | 已提交，待评审 | 已收到 |
| `adopted` | 反馈有效，已采纳 | 已采纳 |
| `resolved` | 问题已处理 | 已处理 |
| `dismissed` | 不处理或无法复现 | 未采纳 |

建议后续扩展：

| Status | Why |
| --- | --- |
| `triaged` | 区分“收到”与“已看过并分类” |
| `duplicate` | 合并重复反馈，避免误判为关闭 |

建议新增用户可见字段：

| Field | Type | Purpose |
| --- | --- | --- |
| `resolution_note` | text | 给用户看的处理说明 |
| `resolved_at` | timestamp | 用户可见的处理完成时间 |
| `linked_issue_id` | text | 内部任务或内容修正记录 |

`admin_note` 只给内部看，不应直接展示给用户。

## Data Payload

前端提交时必须按场景带上下文。不要让用户手动描述系统已经知道的信息。

### Annotation Context

Required:

- `mark_id` or `sentence_entry_id`
- `annotation_type`
- `source_sentence`
- `translation`
- `reading_goal`
- `reading_variant`
- `mark_data` or `entry_data`

Useful:

- `paragraph_index`
- `sentence_index`
- `selected_text`
- `rendered_title`

### Dictionary Context

Required:

- `word`
- `phonetic`
- `current_meaning`
- `dict_source`
- `dict_entry_id`
- `context_sentence`
- `reading_variant`

Useful:

- `selected_text`
- `lookup_mode`: mini/full
- `exam_tags`
- `shown_exam_tags`
- `disambiguation_chosen`

### Analysis Result Context

Required:

- `analysis_record_id`
- `reading_goal`
- `reading_variant`

Useful:

- `source_text_length`
- `annotation_count`
- `translation_visible`
- `annotation_density`
- `user_facing_state`

### App Feedback Context

Required:

- `app_area`
- `app_version`
- `client_platform`

Useful:

- `route`
- `device_model`
- `system_info`
- `network_type`

## Review Queue

内部评审至少需要这些视图：

| Queue | Filter | Primary Reviewer Action |
| --- | --- | --- |
| 词典问题 | `scope=dictionary` | 修正词条、例句、音标或来源 |
| 标注问题 | `scope=annotation` | 判断规则/模型是否误标，沉淀正反例 |
| 整篇解析 | `scope=analysis_result` | 判断解析策略、难度、翻译质量 |
| 应用问题 | `scope=app` | 转产品/工程任务 |

每条反馈应显示：

- 用户选择的问题类型。
- 用户补充说明。
- 自动上下文。
- 同类反馈数量。
- 用户历史反馈质量参考。
- 当前状态。
- 内部处理备注。
- 用户可见处理说明。

## Reward Policy

奖励不是所有反馈都给，应鼓励高价值反馈：

| Case | Reward |
| --- | --- |
| 明确指出词典错误并被修正 | 可奖励 |
| 标注问题被确认并用于规则/样本优化 | 可奖励 |
| 普通 thumbs up | 不奖励 |
| 重复反馈 | 不重复奖励 |
| 无法复现或描述过少 | 不奖励 |

奖励应通过积分明细自然展示，不默认推送。用户可在“我的反馈”中看到 `已采纳 +N 积分`。

## User Return Loop

用户侧必须能看到三类结果：

1. 提交成功：立即反馈。
2. 状态变化：在“我的反馈”列表中可见。
3. 奖励到账：在“我的反馈”和积分明细中可见。

推荐用户可见处理文案：

| Backend Status | Example Copy |
| --- | --- |
| pending | 已收到，我们会结合上下文评审 |
| adopted | 已采纳，感谢帮助我们改进 |
| resolved | 已处理，相关内容会在后续结果中更新 |
| dismissed | 暂未采纳，可能是当前信息不足或暂不影响结果 |

## Current API Fit

当前 `POST /feedback`, `GET /feedback`, `DELETE /feedback/{id}` 已能支撑基础体验。缺口主要在：

- 列表项缺少 `target_id`、`annotation_type`、`analysis_record_id`、`context_json` 摘要。
- 没有用户可见的 `resolution_note`。
- 没有 `triaged` 状态。
- `GET /feedback` count 不能只用 `limit=1` 的 items 长度代表总数。
- 内部统计 API 已存在，但还不足以承担完整评审台。


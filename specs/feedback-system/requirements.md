# Requirements Document

## Introduction

本次开发为 Claread 透读小程序新增用户反馈系统，覆盖四个反馈场景：结果页整体反馈、批注级反馈、应用功能反馈、词典反馈。核心目标是收集用户反馈以优化小程序体验，同时为后续 RAG 开发积累优质标注数据（正例和反例）。配套新增积分明细页，让用户在小程序内部自然发现奖励到账信息，不通过微信推送打扰用户。

## Constraints

- 项目尚在开发阶段，未线上部署，不需要考虑数据迁移
- 不收集用户联系方式（手机号、邮箱等），符合微信小程序用户信息获取规范
- 不使用微信订阅消息推送反馈状态，保持工具类小程序的安静体验
- 不引入 AI 分类能力，初期按反馈入口硬编码问题分类枚举
- 管理后台后续用微信小程序云开发-云后台实现，本次仅预留管理字段和内部 API
- 词典反馈仅收集负面反馈（词典为静态数据，不需要 LLM 参与，无正例样本需求）

## Requirements

### Requirement 1 - 结果页整体反馈

**User Story:** 作为阅读完解析结果的用户，我希望能快速表达对整体解析质量的满意度或不满意原因，帮助团队发现质量问题。

#### Acceptance Criteria

1. While a user views a completed analysis result page, when the page renders the bottom action area, the Claread system shall display a thumbs-up / thumbs-down feedback widget.
2. While a user taps thumbs-up, when the system submits the feedback, the Claread system shall record a positive sentiment feedback with `feedback_scope='analysis_result'` and `feedback_type='thumbs_up'` without requiring additional input.
3. While a user taps thumbs-down, when the system shows the detail options, the Claread system shall present structured negative feedback options: translation_inaccurate, too_few_annotations, too_many_annotations, wrong_difficulty, other.
4. While a user selects a negative feedback type and optionally adds text, when the system submits, the Claread system shall record a negative sentiment feedback with the selected type and optional content.
5. While a user submits feedback for the same record with the same type, when the system processes the submission, the Claread system shall update the existing record (upsert) instead of creating a duplicate.

### Requirement 2 - 批注级反馈

**User Story:** 作为阅读解析结果的用户，当我发现某个标注有误或不准确时，我希望能直接对该标注提交反馈，帮助改进标注质量。

#### Acceptance Criteria

1. While a user long-presses an InlineMark annotation, when the system shows the action overlay, the Claread system shall include feedback options alongside existing actions.
2. While a user taps the feedback icon on an expanded AnalysisCard, when the system shows the feedback menu, the Claread system shall present structured feedback options for that specific annotation.
3. While a user submits annotation feedback, when the system records it, the Claread system shall capture the annotation's `target_id` (mark.id or sentence_entry.id), `annotation_type`, and a context snapshot in `context_json`.
4. While a user submits positive annotation feedback, when the system records it, the Claread system shall use `feedback_type='helpful'` with `sentiment='positive'`.
5. While a user submits negative annotation feedback, when the system shows options, the Claread system shall present: wrong_label, inaccurate, wrong_boundary, should_not_annotate, other.
6. While the context snapshot is captured, when the system stores it, the Claread system shall include: mark_id, mark_data, source_sentence, translation, reading_goal, reading_variant.

### Requirement 3 - 应用功能反馈

**User Story:** 作为使用小程序的用户，当遇到非解析类的 bug 或有功能建议时，我希望能通过个人设置页的入口提交反馈。

#### Acceptance Criteria

1. While a user opens the profile page, when the menu list renders, the Claread system shall display a "意见反馈" menu item.
2. While a user taps the feedback menu item, when the feedback page opens, the Claread system shall present a form with feedback category selection and a description text field.
3. While a user selects a feedback category, when the form renders, the Claread system shall offer: bug_report, feature_request, quota_issue, input_page_issue, ux_issue, other.
4. While a user submits app feedback, when the system records it, the Claread system shall store it with `feedback_scope='app'` and `sentiment='neutral'`.
5. While the feedback form is displayed, the Claread system shall NOT collect any contact information (phone number, email, WeChat ID, etc.) to comply with WeChat Mini Program privacy regulations.

### Requirement 4 - 词典反馈

**User Story:** 作为在结果页查词的用户，当发现词典释义有误或缺失时，我希望能直接在单词卡片中提交反馈，帮助改进词典数据质量。

#### Acceptance Criteria

1. While a user opens the WordPopup in full mode, when the footer actions render, the Claread system shall display a "反馈" button alongside "收藏" and "记入生词本".
2. While a user taps the feedback button, when the system shows feedback options, the Claread system shall present ONLY negative options: wrong_definition, missing_definition, wrong_pos, wrong_phonetic, bad_example, other.
3. While a user submits dictionary feedback, when the system records it, the Claread system shall enforce `sentiment='negative'` and reject any positive sentiment for this scope.
4. While the context snapshot is captured for dictionary feedback, when the system stores it, the Claread system shall include: word, phonetic, current_meaning, dict_source, dict_entry_id, context_sentence, disambiguation_chosen, reading_variant.

### Requirement 5 - 反馈奖励积分

**User Story:** 作为提交反馈的用户，当我的反馈被采纳时，我希望能获得奖励积分，激励我继续贡献高质量反馈。

#### Acceptance Criteria

1. While an admin marks a feedback as "adopted", when the system processes the status change, the Claread system shall grant bonus points to the feedback submitter via `grant_bonus_credits()` with `entry_type='feedback_reward'`.
2. While bonus points are granted for feedback, when the system writes the ledger, the Claread system shall record the points in the `bonus` bucket with a `feedback_reward` entry in `user_credit_ledger`.
3. While the feedback is adopted, when the system completes the reward, the Claread system shall NOT send any push notification or subscription message to the user (silent process).
4. While the feedback record is updated, when the reward is granted, the Claread system shall set `reward_points` and `reward_granted_at` on the feedback record.

### Requirement 6 - 积分明细页

**User Story:** 作为关心积分使用情况的用户，我希望能查看积分消耗详情和奖励到账记录，了解积分花在哪里、获得了什么类型的奖励。

#### Acceptance Criteria

1. While a user views the profile page, when the credit/quota section renders, the Claread system shall make the entire credit area tappable to navigate to the credit detail page.
2. While a user opens the credit detail page, when the page loads, the Claread system shall display a summary of current available credits (daily remaining + bonus) at the top.
3. While the credit detail page renders, when the system loads ledger entries, the Claread system shall display a chronological list of credit changes with: entry type icon, Chinese label, points change (color-coded), article title (for analysis_deduct), description, balance after, and timestamp.
4. While a ledger entry has `entry_type='feedback_reward'`, when the detail page renders it, the Claread system shall display it with a green color, a "反馈奖励" label, and a description like "你的反馈已被采纳，感谢贡献".
5. While the credit detail page reaches the bottom of the loaded entries, when the user scrolls further, the Claread system shall load more entries via cursor-based pagination.
6. While the user_credit_ledger is queried, when the API returns entries, the Claread system shall include a human-readable `description` field generated by the backend for each entry type.

### Requirement 7 - 我的反馈

**User Story:** 作为提交过反馈的用户，我希望能查看已提交反馈的处理状态，了解哪些反馈已被采纳。

#### Acceptance Criteria

1. While a user opens the app feedback page, when the page renders below the submission form, the Claread system shall display a "我的反馈" entry with the count of submitted feedbacks.
2. While a user taps "我的反馈", when the feedback list page opens, the Claread system shall display the user's submitted feedbacks in reverse chronological order with: feedback type, content preview, status (pending/adopted/resolved/dismissed), and submission date.
3. While a feedback has `status='adopted'` and `reward_points > 0`, when the list item renders, the Claread system shall display the reward points badge (e.g., "+50 积分").

### Requirement 8 - 数据设计原则

**User Story:** 作为后续需要使用反馈数据构建 RAG few-shot 样本的团队成员，我希望反馈数据的设计合理、灵活，便于按标注类型分桶提取正例和反例。

#### Acceptance Criteria

1. While the feedback table stores annotation-level feedback, when the data is queried for RAG training, the Claread system shall support filtering by `feedback_scope`, `annotation_type`, and `sentiment` to separate positive and negative examples.
2. While the context snapshot is stored, when the data is extracted later, the Claread system shall preserve sufficient context (mark data, source sentence, translation, reading goal) to construct complete few-shot examples without needing to join back to the original analysis record.
3. While feedback data accumulates, when the system tracks RAG data extraction, the Claread system shall use the `rag_harvested` flag to prevent duplicate extraction of the same feedback records.

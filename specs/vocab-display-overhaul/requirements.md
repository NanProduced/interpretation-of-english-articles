# Requirements Document

## Introduction

本次改造聚焦 Claread 生词本的显示、数据完整性和结果页联动标注，不开发复习系统。目标是让生词本成为"阅读后可回看、可定位、可持续扩展"的词汇沉淀层，而不是信息残缺的简单收藏夹。

## Constraints

- 项目尚在开发阶段，未线上部署，不需要考虑数据迁移，可随时清空数据库重建
- `dict_entries`、`dict_lookup_targets`、`dict_redirects` 三张词典表通过 MDX 脚本导入且已手动补充数据，处于稳定状态，本次不改不动，只做只读引用
- 已有 `GET /dict/entry?id={dict_entry_id}` 接口可直接复用，不需要新增 dict 相关端点

## Requirements

### Requirement 1 - 完整词条显示

**User Story:** 作为在结果页中收藏生词的用户，我希望生词本中的词条信息至少不弱于收藏当下的查词卡片，这样我再次打开生词本时仍然能获得完整的学习价值。

#### Acceptance Criteria

1. While a user saves a vocabulary entry from the result page, when the system persists the entry, the Claread system shall persist a stable dictionary entry reference (`dict_entry_id`) together with a complete-enough snapshot for fallback display.
2. While a vocabulary entry has a valid `dict_entry_id`, when the user opens the vocabulary detail view, the Claread system shall load and display dictionary meanings, phrases, and examples from the dictionary service (`GET /dict/entry`) instead of relying only on the saved short meaning.
3. While the dictionary service is temporarily unavailable, when the user opens the vocabulary detail view, the Claread system shall fall back to the saved snapshot without blocking the detail view.

### Requirement 2 - 语境优先查看

**User Story:** 作为收藏过单词的用户，我希望先回看当时收藏它的句子语境，再决定是否回到整篇解析页。

#### Acceptance Criteria

1. While a vocabulary entry has one or more saved source traces, when the user opens the detail view, the Claread system shall show independent source sentence context cards before offering article navigation.
2. While the source analysis record is still available, when the user chooses to view the original article, the Claread system shall navigate to the analysis result page and focus the saved sentence location.
3. While the source analysis record has been logically deleted or is otherwise unavailable, when the user chooses to view the original article, the Claread system shall not navigate and shall instead provide a clear unavailable message.
4. While a vocabulary entry has multiple source contexts, when the user views the detail page, the Claread system shall display the count of source contexts (e.g. "已收藏于 N 个语境") and allow horizontal swiping through context cards.

### Requirement 3 - 同词多形态归一

**User Story:** 作为阅读中会遇到同一词不同形态的用户，我希望生词本能把这些形态识别为同一词，而不是重复收藏成多条。

#### Acceptance Criteria

1. While a user saves a vocabulary entry whose dictionary result exposes a base word or lemma, when the Claread system stores the entry, the system shall use the normalized lemma as the primary identity key.
2. While a user saves the same lemma again from another article or another word form, when the Claread system stores the entry, the system shall merge it into the same vocabulary entry and append a new source trace instead of creating a duplicate entry.
3. While a merge happens due to lemma normalization, when the user saves a word, the Claread system shall provide clear feedback (e.g. "adopted 已添加到 adopt（第 2 个语境）") so the user understands the merge rather than being confused by a silent operation.
4. While a vocabulary entry has been merged from multiple word forms, when the user views the detail page, the Claread system shall display the collected surface forms alongside the lemma (e.g. "adopt · 收藏形态: adopted, adopting").

### Requirement 4 - 结果页联动标注

**User Story:** 作为已经积累过生词本的用户，我希望在新的解析结果页里快速看到哪些词是我已经收藏过的。

#### Acceptance Criteria

1. While a result page has finished rendering, when the page loads the user vocabulary overlay data, the Claread system shall fetch vocabulary matches via an extra API call instead of adding this work into the `/analyze` main workflow.
2. While a sentence contains words or phrases already present in the user vocabulary book, when the overlay data is applied, the Claread system shall render a visually distinct saved-vocabulary marker that does not conflict with existing annotation highlights.
3. While the user is not logged in, when the result page loads saved-vocabulary markers, the Claread system shall fall back to local vocabulary data without breaking normal result rendering.
4. While the saved-vocab overlay is rendered, the visual style shall use an independent visual layer (e.g. light rounded background + left accent bar) that is distinct from the existing `visualTone` annotation system, avoiding color overlap and underline confusion.

### Requirement 5 - 可扩展架构

**User Story:** 作为后续要继续增强学习路径能力的团队成员，我希望这次改造后的代码层结构清晰、职责分离，便于后续加入更复杂的学习分析能力。

#### Acceptance Criteria

1. While the Claread system evolves the vocabulary feature, when future learning intelligence fields are introduced, the system shall allow them to be added through structured vocabulary metadata without forcing a redesign of the current core flow.
2. While result rendering and vocabulary matching evolve independently, when either side changes, the Claread system shall keep `/analyze` and vocabulary overlay retrieval as separate responsibilities.

### Requirement 6 - 发音播放

**User Story:** 作为在生词本中复习单词的用户，我希望能听到单词的发音，帮助我建立听觉记忆。

#### Acceptance Criteria

1. While a vocabulary entry is displayed in the detail view, when the user taps the pronunciation button, the Claread system shall play the word's audio pronunciation obtained from the Free Dictionary API.
2. While the Free Dictionary API returns an audio URL for the word, when the system first fetches it, the Claread system shall cache the audio URL to `payload_json.audio_url` to avoid redundant API calls.
3. While the Free Dictionary API does not return an audio URL for a word (e.g. low-frequency words), when the detail view renders, the Claread system shall hide the pronunciation button instead of showing a disabled state.
4. While the pronunciation feature is only available in the vocabulary book detail view, when the user interacts with the result page word popup, the Claread system shall not show pronunciation functionality (to be added in a future iteration).

### Requirement 7 - 列表来源数量可视化

**User Story:** 作为浏览生词本的用户，我希望一眼看出哪些词在多篇文章中遇到过，帮助我判断学习优先级。

#### Acceptance Criteria

1. While a vocabulary entry has multiple source references, when the entry is displayed in the vocabulary list, the Claread system shall show a source count badge (e.g. "2 篇") to indicate how many distinct contexts the word was collected from.
2. While the vocabulary list is displayed, the Claread system shall show the most recent source sentence as a context preview line, with a "还有 N 个语境" indicator when additional contexts exist.

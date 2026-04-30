# Requirements Document

## Introduction

本次开发为 Claread 透读小程序新增"每日精读"模块，作为首页核心功能提供杂志式沉浸阅读体验。每日精读与主线用户输入解析是两条独立产品线：主线是"任务型"页面（帮用户拆解任意输入文章），每日精读是"消费型"页面（平台预筛选文章供用户消费阅读）。每日精读采用预生成模式，通过自动化 Pipeline 拉取外部英文文章 → 微信内容安全检测 → AI 筛选评分 → 专用 Workflow（含质量审核与优化）生成精读 payload → 入库发布，用户打开页面时直接拉取展示，不触发实时分析。整个过程无人工审核，全由 AI 完成，因此 Workflow 中包含质量审核和优化修正节点以确保输出质量。

## Constraints

- 每日精读页面不复用主线结果页布局，不复用 `/analyze` 主流程，不复用 `render_scene` payload
- 内容采用预生成模式，不在用户打开页面时实时运行 LLM 分析
- 文章来源通过自动化脚本定时拉取，不走人工编辑筛选
- 正文标注必须比主线克制，每段高亮不超过 3-5 个，重解析收口到文末
- 词典查询能力复用现有 `/dict` API，但交互边界与阅读目标一致（不跳转独立词典页）
- 版权合规：页面标注原文来源和链接，不直接展示原文全文作为可复制文本
- Guardian API 非商用免费（5000次/天），BBC/NPR RSS 免费，初期无需付费
- 封面图优先使用文章自带图，无图时用氛围渐变色，不引入 AI 生图
- 整个内容生产链路无人工审核，必须通过 AI 质量审核节点 + 微信内容安全检测双重保障
- 每日精读 Workflow 不追求速度，追求质量，每个 agent 节点可配置独立模型

## Requirements

### Requirement 1 - 文章自动拉取 Pipeline

**User Story:** 作为内容运营者，我希望能通过自动化脚本定时从外部英文媒体拉取候选文章，无需人工逐篇寻找和录入。

#### Acceptance Criteria

1. While the pipeline runs on a daily schedule, when it fetches articles from configured sources, the Claread system shall retrieve candidate articles from at least 3 sources: Guardian API (primary), BBC RSS (secondary), NPR RSS (supplementary).
2. While the pipeline fetches from Guardian API, when it queries the search endpoint, the Claread system shall use `wordcount=500-2000` parameter to filter articles in the optimal reading length range.
3. While the pipeline fetches from RSS sources (BBC, NPR), when it parses the feed, the Claread system shall extract title, link, description, publication date, and thumbnail image URL from each item.
4. While the pipeline processes RSS-sourced articles that lack full text, when it needs the article body, the Claread system shall use trafilatura to extract full text from the article URL.
5. While the pipeline discovers articles, when it checks for duplicates, the Claread system shall skip articles whose URL already exists in the database or whose title has >85% fuzzy match with recently published articles (within 30 days).

### Requirement 2 - 内容安全检测

**User Story:** 作为平台运营者，由于没有人工审核，我需要在解析文章前使用微信内容安全检测接口扫描文章内容，避免触碰小程序规范红线。

#### Acceptance Criteria

1. While the pipeline processes a candidate article after text extraction, when it performs content security check, the Claread system shall call WeChat `msgSecCheck` API (version 2) with the article title and text content.
2. While the content security check runs, when the API is called, the Claread system shall use `scene=3` (forum scenario) as the closest match for "platform publishing content for users to read".
3. While the content security check returns a result, when the `suggest` field is `risky` or `review`, the Claread system shall reject the article and not proceed to AI scoring or workflow processing.
4. While the content security check returns a result, when the `suggest` field is `pass`, the Claread system shall allow the article to proceed to AI scoring.
5. While the content security check API call fails or returns an unexpected result without a `suggest` field, the Claread system shall treat the article as unsafe (default to `suggest=review`) and reject it from proceeding to AI scoring.
5. While the pipeline stores article data, when it records the security check result, the Claread system shall store the full check result (trace_id, suggest, label, detail) in the `content_sec_check` JSONB field for audit trail.

### Requirement 3 - AI 筛选与评分

**User Story:** 作为内容运营者，我希望拉取的候选文章能经过 AI 筛选，只保留长度适中、话题有趣、适合精读的高质量文章。

#### Acceptance Criteria

1. While the pipeline evaluates a candidate article, when it checks the word count, the Claread system shall reject articles with fewer than 400 words or more than 2500 words.
2. While the pipeline evaluates a candidate article, when it runs AI scoring, the Claread system shall score the article on 4 dimensions: language_richness (vocabulary richness for English learning), topic_interest (general readability), structure_clarity (suitability for close reading), cultural_value (knowledge/cultural insight).
3. While the AI scoring completes, when the overall score is below 7.0 (out of 10), the Claread system shall reject the article.
4. While the AI scoring completes, when the article passes, the Claread system shall assign: CEFR difficulty level (B1/C1), estimated read time (words / 200), and suggested topic tags.
5. While the pipeline finishes, when multiple articles pass scoring, the Claread system shall select 2-3 top candidates ensuring source diversity (same source max 2 per day), topic diversity, and cover image availability, then execute workflow on each selected article.

### Requirement 4 - 来源多样化与封面图要求

**User Story:** 作为用户，我希望每天看到 2-3 篇不同来源、不同主题的精读文章，并且每篇文章都有封面图，让首页和阅读页更有杂志感。

#### Acceptance Criteria

1. While the pipeline selects articles for daily publishing, when it picks 2-3 candidates, the Claread system shall ensure articles come from at least 2 different sources (e.g., 1 Guardian + 1 BBC, or 1 Guardian + 1 BBC + 1 NPR).
2. While the pipeline selects articles, when it evaluates cover image availability, the Claread system shall prioritize articles with cover images; articles without cover images shall only be selected if no articles with covers are available.
3. While the pipeline selects articles, when it evaluates topic diversity, the Claread system shall avoid selecting 3 articles all from the same topic category (e.g., all technology).
4. While the pipeline publishes daily articles, when it sets the publish count, the Claread system shall publish 2-3 articles per day (max 3), preferring 3 when quality allows but never sacrificing quality for quantity.
5. While the pipeline runs on schedule, when it triggers execution, the Claread system shall execute at UTC+8 8:00-9:00 AM daily to align with user activity and ensure fresh content from all sources.

### Requirement 5 - 专用 Daily Reader Workflow（含质量审核与优化）

**User Story:** 作为产品团队，我希望每日精读使用专用的 LLM workflow，含质量审核和优化修正节点，确保无人工审核情况下的输出质量。每个 agent 节点应可配置独立模型，以在关键节点使用最强模型。

#### Acceptance Criteria

1. While the Daily Reader Workflow processes an article, when it runs, the Claread system shall execute the following nodes in sequence: Light Normalize → Vocab Highlight → Phrase/Context Gloss → Footer Analysis → Full Article Interpretation → Quality Review → (conditional) Refinement → Daily Reader Projection.
2. While the Vocab Highlight node runs, when it annotates the article, the Claread system shall limit highlights to no more than 3-5 per paragraph and focus on high-value vocabulary suitable for English learners.
3. While the Footer Analysis node runs, when it generates analysis, the Claread system shall produce: one-sentence summary, main thesis and author intent, article structure breakdown, key expressions, common misreading points, and discussion questions.
4. While the Full Article Interpretation node runs, when it generates the full analysis, the Claread system shall produce a coherent, lecture-style article interpretation (not a sentence-by-sentence breakdown).
5. While the Quality Review node runs, when it reviews all prior outputs, the Claread system shall evaluate 6 dimensions: highlight_accuracy, highlight_density, footer_completeness, footer_accuracy, interpretation_coherence, annotation_consistency.
6. While the Quality Review node finds issues, when issues are fixable, the Claread system shall route to the Refinement node; when no issues are found, the Claread system shall route directly to Daily Reader Projection.
7. While the Refinement node runs, when it applies fixes, the Claread system shall only fix the specific issues identified by Quality Review and shall execute at most one round of refinement (no re-review loop).
8. While the Refinement node determines the article is unsalvageable, when it returns `abort=True`, the Claread system shall mark the article as draft and the Pipeline shall attempt the next candidate.
9. While any LLM node runs, when it selects a model, the Claread system shall use the node-specific model route (daily_annotation for vocab/phrase nodes, daily_analysis for footer/interpretation nodes, daily_review for review/refinement nodes) allowing per-node model configuration.
10. While the Daily Reader Projection node runs, when it assembles the final payload, the Claread system shall output a `daily_reader` payload conforming to the defined schema (article, cover, body, highlights, footer_analysis).

### Requirement 6 - Daily Reader Payload 与数据入库

**User Story:** 作为开发者，我希望每日精读有独立的数据结构和存储，与主线 `render_scene` 完全隔离，保证内容版本稳定。

#### Acceptance Criteria

1. While the system stores a Daily Reader article, when it writes to the database, the Claread system shall use a dedicated `daily_readers` table with fields: id, title, subtitle, source, source_url, publish_date, difficulty, read_time_minutes, tags, cover_image_url, cover_theme, body_json, highlights_json, footer_analysis_json, content_sec_check, status, created_at, published_at.
2. While the system generates a Daily Reader ID, when it creates the record, the Claread system shall use the format `daily_{YYYY}_{MM}_{DD}_{NNN}` where NNN is a zero-padded sequence number.
3. While the system stores the payload, when it writes body/highlights/footer_analysis, the Claread system shall store them as JSONB columns for flexible querying.
4. While the system manages article lifecycle, when it transitions status, the Claread system shall support: draft → published → archived.
5. While the system publishes daily articles, when it sets articles as today's picks, the Claread system shall ensure at most 3 articles per day have `status='published'` and `publish_date=today`.

### Requirement 7 - Daily Reader API

**User Story:** 作为前端开发者，我希望能通过独立的 API 拉取每日精读内容，不依赖实时 `/analyze` 接口。

#### Acceptance Criteria

1. While a user opens the daily reader page, when the frontend requests today's articles, the Claread system shall provide `GET /daily-reader/today` returning a list of 2-3 published articles for the current date.
2. While a user views a specific article, when the frontend requests by ID, the Claread system shall provide `GET /daily-reader/{id}` returning the full payload.
3. While a user browses past articles, when the frontend requests a list, the Claread system shall provide `GET /daily-reader` returning a paginated list of published articles (newest first).
4. While the API returns article data, when the response includes cover image, the Claread system shall include `cover_image_url` and `cover_theme` fields, with at least one being non-null.
5. While the API returns article data, when the response includes the source, the Claread system shall include `source` (publication name) and `source_url` (original article link) fields.

### Requirement 8 - 每日精读页面

**User Story:** 作为英语学习者，我希望在首页看到每日精选的英文文章，点击进入后能像读杂志一样沉浸阅读，不被过多解释打断，同时在文末获得深度讲解。

#### Acceptance Criteria

1. While a user opens the daily reader page, when the page renders, the Claread system shall display a magazine-style layout with: header (title, subtitle, source, date, difficulty, read time, tags), reading body (clean text with minimal highlights), and footer analysis (summary, structure, key expressions, full analysis, discussion questions).
2. While a user reads the article body, when the text renders, the Claread system shall use comfortable typography (serif font for English, 1.6-1.8 line height, generous paragraph spacing) to create a magazine reading feel.
3. While a user taps a highlighted word in the body, when the system shows the mini card, the Claread system shall display word form, phonetic, and 1-2 core definitions without leaving the reading context.
4. While a user taps a non-highlighted word in the body, when the system shows the mini card, the Claread system shall trigger the existing `/dict` dictionary lookup and display the result in the same mini card format.
5. While a user taps the mini card again, when the system opens the bottom sheet, the Claread system shall show: for LLM-annotated words, glossary/context explanation first with dictionary as supplement; for regular words, full dictionary detail.
6. While a user scrolls to the footer analysis section, when the section renders, the Claread system shall display each analysis module with clear visual separation (icon + title), and the "Full Article Interpretation" module shall be collapsed by default.
7. While a user views the footer analysis, when the structure breakdown renders, the Claread system shall display it as a collapsible tree/indented list.
8. While a user views the footer analysis, when the key expressions render, the Claread system shall display them as tappable cards in a grid layout.
9. While a user views the footer analysis, when the section ends, the Claread system shall display a "Read original at {source} →" link pointing to `source_url`, allowing users to visit the original article.

### Requirement 9 - 首页入口

**User Story:** 作为用户，我希望在首页看到今日精读的推荐卡片，一眼判断是否值得阅读，点击直接进入阅读页面。

#### Acceptance Criteria

1. While a user views the home page, when the daily reader section renders, the Claread system shall display 2-3 magazine-cover-style cards (horizontal scroll or vertical stack), each showing: article title, source, difficulty badge, estimated read time, and cover image or themed gradient.
2. While the home page renders the daily reader card, when the card is visually distinct from the main input area, the Claread system shall use a different visual treatment (e.g., card with image/gradient background vs. plain input area) to establish "this is curated content" perception.
3. While a user taps the daily reader card, when the navigation triggers, the Claread system shall navigate directly to the daily reader page with the specific article ID (e.g., `pages/daily-reader/index?id={articleId}`) without intermediate pages.
4. While the home page loads, when no daily article is available for today, the Claread system shall gracefully hide the daily reader card or show a fallback state (e.g., "Today's article is being prepared").
5. While a user views the home page daily reader section, when the section header renders, the Claread system shall display a "更多 →" link navigating to the daily reader archive page.

### Requirement 10 - 阅读进度与往期入口

**User Story:** 作为用户，我希望知道今天是否已读过每日精读，并能在文末方便地找到往期文章。

#### Acceptance Criteria

1. While a user opens the daily reader page, when the page renders, the Claread system shall display a subtle reading progress indicator (scroll-based) at the top of the page.
2. While a user scrolls through the article, when the progress indicator updates, the Claread system shall reflect the current scroll position as a percentage of total content height.
3. While a user reaches the bottom of the daily reader page, when the footer analysis section completes, the Claread system shall display a "往期精选" entry linking to the archive page (`pages/daily-reader-archive/index`).
4. While a user views the archive page, when the page renders, the Claread system shall display published articles in reverse chronological order with: title, source, difficulty, read time, and cover thumbnail.

### Requirement 11 - 分享

**User Story:** 作为用户，我希望能将今日精读分享给朋友，吸引更多人使用小程序。

#### 实现策略

| 阶段 | 方案 | 状态 |
|------|------|------|
| **MVP（当前）** | 静态品牌图作为分享卡配图，通过 `useShareAppMessage().imageUrl` 指定 | ✅ 已实现 |
| **V2（未来）** | Canvas 动态绘制自定义卡片：含文章标题、关键引用、来源、小程序二维码，以文章主题色为背景 | 📋 TODO |

> 微信平台约束详见 [static-image-assets-brief.tmp.md §5](../../docs/operations/static-image-assets-brief.tmp.md)：
> 分享图比例 **5:4**（硬性），文件大小 ≤ 300KB，`title` 字段上限 **28 汉字**，
> 核心内容需居中（边缘可能被裁切）。朋友圈分享 (`onShareTimeline`) 需单独准备 **1:1** 方图。

#### Acceptance Criteria

1. While a user views the daily reader page, when the share action is triggered (via右上角「…」→「转发」), the Claread system shall return a share config object with: title set to `{article.title} — Claread 每日精读`, path pointing to the article detail page, and imageUrl pointing to a static brand image (`shareFallback`). (MVP: static image; V2: canvas-generated card per original AC1 spec)
2. While no article is loaded (e.g. home page share fallback), when the share action triggers, the Claread system shall return a share config with default title `'Claread 透读'` and the same static brand image.
3. While a user shares via WeChat, when the share message renders in chat list, the Claread system shall ensure the combined title text does not exceed WeChat's 28-character limit; excess characters will be truncated by the platform automatically.
4. (V2 Future) While the share card is dynamically generated, when the image renders, the Claread system shall use the article's cover theme color as the card background and include: article title, key quote, source, mini program QR code.

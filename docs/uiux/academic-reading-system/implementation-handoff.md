# Academic Reading UI Implementation Handoff

Use this brief when asking an implementation agent to build academic mode UI.

## Goal

Build a distinct academic result page for `schemaVersion === "3.0.0-academic"`.

Do not continue to render academic output through the same visual rhythm as exam grammar cards. Academic mode should feel like scholarly margin intelligence inside the Claread reader.

## Data Contract

Use existing `AcademicRenderSceneVm`:

- `title`
- `article.paragraphs`
- `article.sentences`
- `translations`
- `inlineMarks`
- `sentenceEntries`
- `contentSummary`
- `warnings`

Do not require backend schema changes for v1. If paragraph role UI is desired later, request projection support explicitly.

## Recommended Component Split

- `AcademicResultView`
- `AcademicResearchBrief`
- `AcademicParagraphBlock`
- `AcademicInlineMark`
- `AcademicNoteSlip`
- `AcademicTermSheet`

Reuse:

- `NavBar`
- `ReaderContextBar`
- `FeedbackSystem`
- shared reader tokens

Avoid:

- Reusing `AnalysisCard` for academic notes.
- Showing dashboard-like summary cards.
- Showing exam tags, vocabulary-save primary actions, or grammar labels.

## Visual References

Do not use generated design images as implementation references.

Use the written visual language:

- Calm paper reader.
- Scholarly margin intelligence.
- Low-chroma academic semantic colors.
- Thin marks and light note slips.
- English source text as the primary reading surface.
- Chinese translation and notes as secondary layers.

If a screenshot or generated mock conflicts with the written spec, follow the written spec.

## Acceptance Criteria

- English source text remains visually dominant.
- Research brief does not push reading below the fold.
- Terms look like academic concepts, not vocabulary drills.
- Logic notes explain argument movement, not grammar.
- Interpretation notes are rare and local.
- Translation is useful but visually secondary.
- Feedback entry exists but does not interrupt reading.

## Agent Prompt

Use this prompt in a clean implementation session:

```text
请根据 `docs/uiux/academic-reading-system/README.md`、`component-spec.md`、`implementation-handoff.md`，为 `schemaVersion === "3.0.0-academic"` 实现独立的 academic 结果页 UI。

关键要求：
- 不要继续把 academic 的 `term_note / logic_note / interpretation_note` 套进考试/语法卡片节奏。
- 不要依赖任何设计图或生成截图，按文档里的设计语言和 schema 边界实现。
- 使用现有 `AcademicRenderSceneVm` 数据：title、article、translations、inlineMarks、sentenceEntries、contentSummary、warnings。
- 英文原文是主视觉层；中文翻译、内容导读、术语/论证/解释便笺都是辅助层。
- 内容导读要轻，不要像 dashboard summary card，也不要把首段正文挤出首屏太远。
- term_note 是学术概念，不是生词本单词；logic_note 解释论证推进，不讲语法；interpretation_note 只作为必要时的局部解释。
- 尽量拆出 academic 专属组件，避免在 ParagraphBlock / AnalysisCard 内堆大量 academic 分支。
- 不要引入后端 schema 变更。无法用当前 VM 渲染的数据不要臆造。

完成后请提供微信开发者工具截图，并说明 academic VM 的哪些字段被消费、哪些能力因 schema 暂不支持而未做。
```

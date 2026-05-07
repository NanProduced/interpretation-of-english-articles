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

Use:

- `assets/target-viewport-academic-reader.png`
- `assets/target-viewport-academic-notes.png`
- `assets/target-viewport-academic-term-sheet.png`
- `assets/academic-component-spec-board.png`

Also compare against:

- `../reading-annotation-system/assets/target-viewport-reader-annotations.png`
- `../reading-annotation-system/assets/target-viewport-mini-lookup.png`
- `../reading-annotation-system/assets/component-spec-board.png`

## Acceptance Criteria

- English source text remains visually dominant.
- Research brief does not push reading below the fold.
- Terms look like academic concepts, not vocabulary drills.
- Logic notes explain argument movement, not grammar.
- Interpretation notes are rare and local.
- Translation is useful but visually secondary.
- Feedback entry exists but does not interrupt reading.


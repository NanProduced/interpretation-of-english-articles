# Agent Handoff: Reading Annotation System

Use this file as the starting point for Claude/Gemini implementation agents.

If this is a correction after a failed or visually misaligned implementation, read `agent-correction-brief.md` before coding.

## Mission

Implement the first production pass of Claread's premium reading annotation and word lookup UI.

The goal is not to rebuild the app. The goal is to upgrade the core reader annotation language and point-word lookup experience while staying compatible with the current workflow schema.

## Must Read

1. `.impeccable.md`
2. `docs/uiux/reading-annotation-system/README.md`
3. `docs/uiux/reading-annotation-system/implementation-mapping.md`
4. `docs/uiux/reading-annotation-system/word-lookup-and-vocabulary-ux.md`
5. `docs/uiux/reading-annotation-system/development-materials-checklist.md`

Visual references:

- `docs/uiux/reading-annotation-system/assets/product-direction-overview.png`
- `docs/uiux/reading-annotation-system/assets/reading-annotation-current-overview.png`
- `docs/uiux/reading-annotation-system/assets/reader-context-feedback-details.png`
- `docs/uiux/reading-annotation-system/assets/annotation-micro-rules.png`
- `docs/uiux/reading-annotation-system/assets/sentence-analysis-final-detail.png`

## Product Hierarchy

Always preserve this order:

1. Reading.
2. Notes and annotation.
3. English support.

If a UI choice helps English explanation but makes the article harder to read, choose the article.

## Implementation Scope

### In Scope

- Add reader/annotation SCSS tokens.
- Add `ReaderContextBar` for source type, reading goal, reading variant, and current mode.
- Implement `AnnotationGlyph`.
- Restyle `InlineMark`.
- Restyle `ClickableWord` saved vocabulary markers.
- Redesign `WordPopup` visual states:
  - mini lookup slip
  - full dictionary note sheet
  - AI phrase/context insight block
  - dictionary definitions/disambiguation
  - vocabulary save actions
- Add source-context excerpt in the full dictionary sheet.
- Add a small `LookupSaveState` helper.
- Add quiet feedback entry points for annotation details, word lookup, and article-end feedback.
- Add local fixtures or an internal preview path if useful for state coverage.

### Out Of Scope For First Pass

- Backend schema changes.
- Large reader architecture rewrite.
- Custom font shipping.
- Raster PNG icons for annotation glyphs.
- Decorative reader backgrounds.
- New onboarding or paywall work.
- Full vocabulary review system redesign.
- Full feedback backend redesign.

## Data Constraints

Use the existing render VM:

- `vocab_highlight`: single word, `glossary=null`, dictionary lookup first.
- `phrase_gloss`: phrase/expression, `glossary.zh`, `glossary.phraseType`, AI phrase meaning first.
- `context_gloss`: context meaning, `glossary.gloss`, `glossary.reason`, AI context insight first.
- `grammar_note`: inline underline plus sentence entry, inline mark is not clickable.
- `sentence_analysis`: sentence entry only; no default inline mark.

Do not invent backend fields in production code.

## Primary Frontend Files

Likely touchpoints:

- `client/src/components/InlineMark/index.tsx`
- `client/src/components/InlineMark/index.scss`
- `client/src/components/ClickableWord/index.tsx`
- `client/src/components/ClickableWord/index.scss`
- `client/src/components/WordPopup/index.tsx`
- `client/src/components/WordPopup/index.scss`
- `client/src/components/ParagraphBlock/index.tsx`
- `client/src/components/ParagraphBlock/index.scss`
- `client/src/components/AnalysisCard/index.tsx`
- `client/src/components/AnalysisCard/index.scss`
- `client/src/types/view/render-scene.vm.ts`
- `client/src/pages/result/hooks/useResultActions.ts`
- `client/src/pages/result/hooks/useResultEffects.ts`
- `client/src/services/storage/index.ts`

Recommended additions:

- `client/src/components/AnnotationGlyph/index.tsx`
- `client/src/components/AnnotationGlyph/index.scss`
- `client/src/components/WordPopup/lookupSaveState.ts`
- `client/src/dev-fixtures/readingAnnotationStates.ts`

## Visual Rules

- Use warm paper and deep ink.
- Keep annotation colors low opacity.
- Avoid thick purple blocks.
- Avoid heavy shadows.
- Avoid generic Lucide icons for core annotation types.
- Do not use old `C` brand mark.
- Mini lookup should be compact and anchored.
- Full lookup should feel like a paper note sheet, not a generic modal dictionary.
- `reading_goal` and `reading_variant` should be visible as quiet context metadata, not strong purple badges.
- Feedback actions should be secondary and non-interruptive.

## State Coverage

Before asking for review, cover:

- Plain word lookup loading.
- Plain word lookup entry result.
- `vocab_highlight` entry result.
- `phrase_gloss` with AI phrase meaning.
- `context_gloss` with reason.
- Dictionary disambiguation.
- No result or network failure.
- Not saved.
- Already saved here.
- Same lemma, new source context.
- Multiple source contexts.
- Mastered.
- Reader context bar with source, goal, variant, and mode.
- Annotation/detail feedback entry.
- Article-end feedback entry.

## Acceptance Criteria

- Reader remains readable if annotations are dense.
- Reader remains readable if annotations are hidden.
- Mini lookup does not obscure too much text.
- Full dictionary sheet feels premium and quiet.
- AI phrase/context insight is visibly distinct from plain dictionary lookup.
- Save state copy is clear and accurate.
- `sentence_analysis` has no permanent inline mark.
- `grammar_note` long titles do not break the layout.
- `reading_goal` / `reading_variant` are present without making the page feel like a cram-school app.
- Feedback entry points exist without interrupting reading.
- WeChat Mini Program build passes.

## Review Packet

When finished, provide:

- Changed file list.
- Screenshots for key states.
- Notes on any deviations from this handoff.
- Build/typecheck command and result.

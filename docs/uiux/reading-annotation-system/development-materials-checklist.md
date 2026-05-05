# Development Materials Checklist

> Status: next-step planning after approval of the current reading annotation and word lookup direction.

Primary direction references:

- `assets/product-direction-overview.png`
- `assets/reading-annotation-current-overview.png`

## What Is Already Enough For Development

The following UI pieces should be implemented with code, not raster images:

- Inline highlighter marks for `vocab_highlight` and `phrase_gloss`.
- Inline underline marks for `context_gloss` and `grammar_note`.
- Saved vocabulary folded-corner marker.
- Mini word lookup slip.
- Full dictionary note sheet.
- Grammar and sentence-analysis compact entries.
- Bottom-sheet controls, tabs, source sentence excerpts, and skeleton loading lines.

These are better as Taro components and SCSS tokens because they need to respond to text length, screen width, reading mode, and saved state.

## Assets To Prepare

### 1. `AnnotationGlyph` Component

Use code-rendered glyphs instead of PNGs.

Required glyph variants:

| Glyph | Use |
|---|---|
| `vocab` | Word lookup / high-value vocabulary |
| `phrase` | Phrase gloss / collocation / idiom |
| `context` | Context meaning underline |
| `grammar_note` | Grammar footnote entry |
| `sentence_analysis` | Sentence analysis entry |
| `saved_vocab` | Already saved vocabulary |
| `merged_note` | Multiple notes collapsed into one entry |

Recommended implementation:

- `client/src/components/AnnotationGlyph/index.tsx`
- `client/src/components/AnnotationGlyph/index.scss`
- Use small inline vector-like `View` shapes where possible.
- Keep strokes thin and rounded.
- Avoid importing a large icon library for these core branded marks.

### 2. State Fixtures

Create fixture data for local UI testing without repeatedly calling the workflow.

Recommended file:

- `client/src/dev-fixtures/readingAnnotationStates.ts`

Minimum cases:

- Plain word lookup loading.
- Plain word lookup entry result.
- `vocab_highlight` with dictionary result.
- `phrase_gloss` with `glossary.zh`.
- `context_gloss` with `glossary.gloss` and `glossary.reason`.
- Dictionary disambiguation result.
- Already saved word.
- Same lemma saved with a new source context.
- Mastered word.

### 3. SCSS Token Set

Add reader annotation tokens near the existing global variables.

Minimum tokens:

```scss
--reader-paper: #FAF9F6;
--reader-paper-deep: #F4F1EA;
--reader-ink: #111111;
--reader-muted: #7A7D86;
--annotation-vocab-bg: rgba(242, 196, 84, 0.28);
--annotation-phrase-bg: rgba(151, 126, 224, 0.18);
--annotation-context-line: rgba(76, 145, 194, 0.72);
--annotation-grammar-line: rgba(116, 102, 148, 0.62);
```

### 4. Word Lookup Components

Split `WordPopup` visually before splitting files if needed.

Target component boundaries:

- `WordLookupSlip`: mini anchored lookup.
- `DictionaryNoteSheet`: full bottom sheet.
- `ContextInsightBlock`: AI phrase/context explanation.
- `DictionaryDefinitionList`: meanings/phrases/examples/disambiguation.
- `VocabularySaveAction`: save state and action copy.
- `SourceContextExcerpt`: source sentence with active word softly marked.

### 5. Saved Vocabulary State Helper

Add a small helper that derives save state from current word context.

Recommended output:

```ts
type LookupSaveState =
  | 'not_saved'
  | 'same_lemma_new_context'
  | 'already_saved_here'
  | 'multiple_contexts'
  | 'mastered'
```

Use it to render:

- `记入生词本`
- `加入当前语境`
- `已记入`
- `已记入 · n个语境`
- `已掌握`

## Optional Visual Assets

Do not add more raster UI assets unless there is a specific need.

Acceptable future raster references:

- A final all-up product direction board for design review.
- A high-resolution App Store / product presentation mockup.
- Loading animation keyframes for Lottie handoff.

Not recommended:

- PNG icons for annotation marks.
- PNG backgrounds inside the reader.
- Decorative illustration assets for the result page.

## Recommended Implementation Order

1. Add annotation and reader SCSS tokens.
2. Implement `AnnotationGlyph`.
3. Restyle `InlineMark` and `ClickableWord` to the stationery language.
4. Refactor `WordPopup` into mini slip and dictionary note sheet states.
5. Add `LookupSaveState` helper and action copy.
6. Add source-context excerpt in the full sheet.
7. Add fixture-driven local preview for all word lookup states.
8. Run WeChat build and inspect on narrow/mobile viewport.

## Acceptance Checks

- Mini lookup never covers more than necessary.
- Full sheet feels like a note surface, not a generic modal.
- AI phrase/context insight is clearly different from plain dictionary lookup.
- Saved vocabulary state is obvious without being loud.
- Dense annotations still feel like marks on paper.
- No old `C` mark appears in any new loading or reading UI design.

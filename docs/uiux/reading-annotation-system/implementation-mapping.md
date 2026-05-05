# Implementation Mapping

This document maps the approved reading annotation visual direction to the current Claread workflow schema and Taro frontend implementation.

## Current Data Model

Backend public schema:

- `inline_marks`: inline anchors rendered inside article text.
- `sentence_entries`: sentence-level explanation entries rendered after a sentence or sentence group.
- `translations`: sentence-level Chinese translations.

Important types:

| Type | Inline mark? | Sentence entry? | Clickable? | Notes |
|---|---:|---:|---:|---|
| `vocab_highlight` | Yes | No | Yes | Single word, dictionary lookup |
| `phrase_gloss` | Yes | No | Yes | Multi-word or special phrase lookup |
| `context_gloss` | Yes | No | Yes | Context meaning, underline |
| `grammar_note` | Yes | Yes | Inline mark is not clickable | Can be single-span or multi-span, max 4 spans |
| `sentence_analysis` | No | Yes | Entry is expandable | Optional chunks are embedded in markdown-like content |

## Current Frontend Touchpoints

| File | Role |
|---|---|
| `client/src/components/ParagraphBlock/index.tsx` | Slices sentence text, applies inline marks, renders sentence entries |
| `client/src/components/ParagraphBlock/index.scss` | Paragraph, sentence, translation, grammar, sentence-analysis visual style |
| `client/src/components/InlineMark/index.tsx` | Renders clickable inline marks |
| `client/src/components/InlineMark/index.scss` | Inline mark visual tones |
| `client/src/components/AnalysisCard/index.tsx` | Renders grammar and sentence entry cards |
| `client/src/components/AnalysisCard/index.scss` | Entry collapsed/expanded styles |
| `client/src/components/ParagraphBlock/utils.ts` | Parses sentence analysis chunks and tokenizes sentence text |
| `client/src/components/WordPopup/index.tsx` | Mini word lookup and full dictionary sheet |
| `client/src/components/WordPopup/index.scss` | Word lookup visual style |
| `client/src/components/ClickableWord/index.tsx` | Generic point-word tap target and saved vocabulary marker |
| `client/src/pages/result/hooks/useResultActions.ts` | Opens lookup popup and saves vocabulary entries |
| `client/src/pages/result/hooks/useResultEffects.ts` | Loads saved vocabulary and cloud vocabulary highlights |
| `client/src/services/storage/index.ts` | Local vocabulary merge/save logic |

## Recommended Rendering Model

### 1. Inline Marks

Keep existing `InlineMark` for clickable marks:

- `vocab_highlight`
- `phrase_gloss`
- `context_gloss`
- `term_note`
- `logic_note`

Restyle these first:

- Remove heavy inset shadows.
- Reduce opacity.
- Preserve semantic colors during active state.
- Replace the crude saved marker with a small bookmark/fold mark.

### 1.1 Word Lookup

The existing `WordPopup` can remain the interaction owner, but it should be split visually into two conceptual components:

```text
WordLookupSlip
DictionaryNoteSheet
```

`WordLookupSlip` is the mini anchored card. It should:

- Prefer `glossary.zh` for `phrase_gloss`.
- Prefer `glossary.gloss` for `context_gloss`.
- Fall back to dictionary summary for `vocab_highlight` and plain word taps.
- Show a compact `多个义项` state for disambiguation.
- Use a skeleton line during dictionary loading.

`DictionaryNoteSheet` is the full bottom sheet. It should:

- Show AI phrase/context insight only when `glossary` exists.
- Keep dictionary meanings, phrases, and examples secondary but easy to access.
- Include current source sentence when `contextSentence` is available.
- Reflect save state: not saved, already saved, merged lemma, multiple contexts, mastered.

Implementation can start inside the current `WordPopup` file, then extract components after the states are stable.

### 2. Grammar Notes

`grammar_note` needs a dedicated rendering path because it is not clickable but still has structure.

Recommended component:

```text
GrammarInlineSpan
```

Inputs:

- mark id
- parent id for multi-span parts
- span text
- visual tone
- optional role from `MultiTextAnchor.parts.role`
- expanded state from the related `sentence_entry`

Default state:

- Thin purple-gray underline.
- No heavy background.
- Multi-span parts share the same visual language.

Expanded state:

- Slightly stronger underline.
- Optional tiny role label near each span.
- Keep word click behavior inside the span.

### 3. Grammar Sentence Entry

The current `AnalysisCard` feels too card-like for reading flow. For grammar entries:

Collapsed:

- Render as a compact notebook tab after the sentence or translation.
- Height should be close to one text line.
- Show icon, label, and chevron only.

Expanded:

- Inline note surface below the sentence.
- Show title and concise explanation.
- Use quiet dividers instead of colored side bars.

### 4. Sentence Analysis

`sentence_analysis` has no inline mark. Do not invent persistent inline marks.

Collapsed:

- Show a compact entry chip such as `长难句拆解`.
- It should sit after the sentence or sentence translation.
- Final collapsed copy should be `句式解析`; do not include chunk counts such as `4段`.

Expanded:

- Set `activeAnalysisId`.
- Use `renderTextWithAnalysis()` to temporarily chunk-highlight the sentence.
- Use muted fine underlines and translucent washes, not rainbow blocks.
- Show a compact chunk list below:
  - `1 主干`
  - `2 修饰`
  - `3 结果`

## Drop Cap

Add a drop cap for the first paragraph in immersive reading mode.

Avoid relying on CSS `::first-letter`; mini program compatibility is not worth the risk.

Recommended approach:

1. Detect first paragraph and first sentence at render time.
2. Split the first visible English letter into a separate `Text`.
3. Render it as `.drop-cap`.
4. Render the rest of the original sentence through the normal mark pipeline.

Important constraint: do not modify backend sentence text or anchor text. The split is display-only.

## Reader Customization

Recommended first version:

| Setting | Values | Implementation |
|---|---|---|
| Font size | small, medium, large | root reader class |
| Line height | compact, comfortable, loose | root reader class |
| Translation | on, off | hide/show translation layer |
| Annotation density | light, standard, full | filter visual tones by mode |
| Theme | warm paper, clean, night | root reader class and CSS vars |

Implementation is feasible in Taro mini program. Use a small store and page-level classes. Avoid shipping custom font files in the first pass unless package size is reviewed.

## Annotation Glyphs

Core annotation entries should use a dedicated `AnnotationGlyph` component instead of generic icons.

Suggested glyphs:

- `grammar_note`: two small nodes connected by a soft curve.
- `sentence_analysis`: three staggered sentence layers.
- `vocab`: small highlighter nib or short mark.
- `phrase`: two connected highlighter strokes.
- `context`: hairline underline with a small dot.
- `merged_note`: folded paper tab or stacked note corner.

State rules:

- default: muted ink gray
- active: subtle semantic tint
- disabled: 35% opacity

## Implementation Order

1. Restyle `InlineMark` to the stationery visual language.
2. Add `GrammarInlineSpan` rendering path for non-clickable grammar marks.
3. Redesign `AnalysisCard` collapsed state into compact in-flow entries.
4. Redesign grammar and sentence expanded states.
5. Add drop cap for the first immersive paragraph.
6. Add reader customization tray and persisted settings.

# Agent Correction Brief

> Use this when an implementation does not match the approved Claread reading annotation direction.

## Diagnosis

The current mismatch is not caused by Taro + React or WeChat Mini Program being unable to implement the intended UI.

Most of the approved direction is feasible in the current stack:

- Warm paper reader surface.
- Low-opacity highlighter marks.
- Fine pencil-like underlines.
- Compact in-flow grammar and sentence entries.
- Anchored mini word lookup slip.
- Bottom dictionary note sheet.
- Saved vocabulary folded-corner marker.
- Quiet reader context bar for `reading_goal` and `reading_variant`.
- Feedback entry points for annotation, dictionary, and whole-article quality.

The problem is implementation drift: the UI is still following the old app/component language instead of the new reading + notes design system.

## Current Implementation Red Flags

If the implementation resembles the current rejected screenshots, treat these as blockers:

1. **Strong exam-mode purple chip**
   - Problem: `reading_goal` / `variant` looks like a learning-app badge.
   - Fix: move it into a quiet reader context bar with source + mode + variant as metadata.

2. **Annotation entries still look like generic collapse cards**
   - Problem: grammar entries feel like regular UI accordion controls.
   - Fix: render them as compact paper-note tabs in the reading flow.

3. **Expanded grammar content is too plain and detached**
   - Problem: it becomes a generic text block below the paragraph.
   - Fix: it should read as a local note attached to the sentence, with title, concise explanation, optional feedback action, and quiet divider.

4. **Inline marks look like default CSS underlines**
   - Problem: they do not feel like stationery annotations.
   - Fix: use tokenized low-opacity washes and thin pencil lines. Avoid saturated purple and heavy borders.

5. **Reader shell is not part of the system**
   - Problem: top tabs, source/mode chips, progress, and reader controls are visually unrelated.
   - Fix: define a `ReaderContextBar` and reader control language.

6. **Feedback system is missing**
   - Problem: users cannot tell the app an explanation is wrong, unclear, or useful.
   - Fix: add feedback entry points at annotation/detail and article levels.

## Platform Feasibility

### Feasible In Taro + React Mini Program

- `View` / `Text` based custom glyphs.
- SCSS tokens for paper, ink, and annotation tones.
- `position: fixed` bottom sheets.
- Anchored mini card using tap coordinates.
- `ScrollView` content areas.
- Safe-area padding.
- Low-opacity backgrounds and border radii.
- Text truncation, `numberOfLines`, compact chips.
- Component-level state for expanded notes and active marks.

### Avoid Or Defer

- Exact cross-line freehand annotation paths.
- CSS pseudo-element dependent typography like `::first-letter` for drop caps.
- Large raster paper textures.
- Heavy blur/glass effects.
- Complex SVG filters or canvas drawing in the reader.
- Pixel-perfect reproduction of AI mockups.

The target is not pixel-perfect image matching. The target is product-language matching.

## Visual Source Of Truth

The current design references have been consolidated into one aligned component language. Do not reference archived images from earlier rounds.

### Production Component Styling

Use `assets/component-spec-board.png` and `component-spec.md` as the source of truth for production mobile UI surfaces:

- `ReaderContextBar`.
- Reader controls.
- Expanded grammar and sentence-analysis notes.
- Annotation feedback button rows.
- Mini word lookup slip.
- Full dictionary note sheet.
- Article-end feedback.
- Card radius, shadow, padding, dividers, and button hierarchy.

### Viewport Targets And State Rules

Use the three `assets/target-viewport-*.png` images for simulator screenshot matching, and use `assets/state-matrix-reference.png` plus `component-spec.md` for behavior:

- `target-viewport-reader-annotations.png`
- `target-viewport-mini-lookup.png`
- `target-viewport-dictionary-sheet.png`

- `grammar_note` collapsed tab overflow.
- Short title display as `语法 · {title}`.
- Long title collapse to `语法`.
- `sentence_analysis` collapsed copy as `句式解析`.
- No chunk count in collapsed entries, such as `句式解析 · 4段`.
- Temporary chunk rows and compact reading map after sentence-analysis expansion.
- `AnnotationGlyph` paper-glyph shape language.
- Note-tab max width, one-line truncation, and ellipsis behavior.

Use `assets/state-matrix-reference.png` for behavior and state coverage.

Use the supplemental SVG boards only for local component details: glyph construction, note-card anatomy, dense mark stacking, degraded lookup states, feedback selection.

If a local detail is not visible in screenshots, follow `component-spec.md` first, then `assets/component-spec-board.png`.

## Module Boundaries

Do not implement this as one giant "annotation system" change. Split the work into four UI modules.

Reader customization settings are not one of these modules. Font size, line height, theme, translation visibility, annotation density, defaults, and persistence need a separate design and business-logic package under `docs/uiux/reading-settings-system/`.

### 1. Reading Shell

Owns:

- Top reader navigation.
- `原文 / 精读` mode switch.
- Source type.
- `reading_goal`.
- `reading_variant`.
- Reader progress.
- Reader settings entry.

Required component:

```text
ReaderContextBar
```

Design rule:

- Source + mode + variant should read as quiet metadata, not as promotional or exam badges.
- Example copy:
  - `手动输入`
  - `考试备考`
  - `CET-4/6`
  - `精读`

### 2. Annotation System

Owns:

- `InlineMark`.
- `ClickableWord` saved marker.
- `AnnotationGlyph`.
- `grammar_note` compact and expanded entries.
- `sentence_analysis` compact and expanded entries.

Design rule:

- Marks are stationery.
- Entries are notebook slips.
- Expansion is local and reversible.

### 3. Word Lookup & Vocabulary

Owns:

- `WordLookupSlip`.
- `DictionaryNoteSheet`.
- `ContextInsightBlock`.
- `VocabularySaveAction`.
- `SourceContextExcerpt`.
- Saved vocabulary states.

Design rule:

- Lookup is a reading loupe.
- Dictionary detail is a note sheet.
- AI phrase/context insight comes before dictionary fallback only when `glossary` exists.

### 4. Feedback System

Owns:

- Annotation feedback.
- Dictionary feedback.
- Whole-article analysis feedback.
- Optional positive/negative quick reactions.

Required entry points:

| Scope | Entry | Placement |
|---|---|---|
| `grammar_note` | "反馈" or small feedback glyph | Expanded note footer |
| `sentence_analysis` | "反馈" or small feedback glyph | Expanded analysis footer |
| `WordLookupSlip` / `DictionaryNoteSheet` | Existing dictionary feedback | Full sheet footer or secondary action |
| Whole article | "本次解读对你有帮助吗？" | Article end, after primary actions |

Design rule:

- Feedback should be quiet and secondary.
- Do not interrupt reading.
- Avoid large modal feedback unless the user explicitly taps into it.

## First-Phase Refactor Scope

The next implementation agent should stop broad page redesign and deliver component states.

### Required Deliverables

1. `AnnotationGlyph`
   - `vocab`
   - `phrase`
   - `context`
   - `grammar_note`
   - `sentence_analysis`
   - `saved_vocab`
   - `feedback`

2. `ReaderContextBar`
   - source type
   - reading goal
   - reading variant
   - current mode
   - compact edit/switch affordance

3. Restyled `InlineMark`
   - `vocab_highlight`
   - `phrase_gloss`
   - `context_gloss`
   - active state
   - dense state

4. Restyled grammar entry
   - collapsed short title
   - collapsed long title
   - expanded note
   - expanded note with feedback entry

5. Restyled sentence analysis entry
   - collapsed `句式解析`
   - expanded temporary chunk state
   - feedback entry

6. `WordLookupSlip`
   - plain word loading
   - dictionary result
   - phrase gloss
   - context gloss
   - saved vocabulary state

7. `DictionaryNoteSheet`
   - AI context insight
   - dictionary definitions
   - source context excerpt
   - save action states
   - feedback action

## Required Screenshots For Review

Before asking for review, provide screenshots for:

1. Reader top area with `ReaderContextBar`.
2. Dense inline marks in a paragraph.
3. Collapsed grammar note with a short title.
4. Collapsed grammar note with a long title.
5. Expanded grammar note with feedback.
6. Collapsed sentence analysis.
7. Expanded sentence analysis with temporary chunks.
8. Mini word lookup slip.
9. Full dictionary note sheet.
10. Article-end feedback area.

Screenshots must be from the WeChat Mini Program simulator or a mobile-equivalent viewport, not only desktop browser mockups.

## Acceptance Criteria

- The page feels like reading first, not studying first.
- `reading_goal` and `reading_variant` are visible but quiet.
- Annotations do not look like generic web chips.
- Expanded notes feel attached to the text they explain.
- Feedback exists but does not interrupt reading.
- The UI works with long grammar titles.
- The UI works with dense annotations.
- The UI works without backend schema changes.
- The implementation does not reintroduce the retired old `C` mark.

## Suggested Prompt For Development Agent

```text
The current implementation does not match the approved Claread reading annotation direction.

Before coding, read:
- .impeccable.md
- docs/uiux/reading-annotation-system/README.md
- docs/uiux/reading-annotation-system/agent-correction-brief.md
- docs/uiux/reading-annotation-system/component-spec.md
- docs/uiux/reading-annotation-system/implementation-mapping.md
- docs/uiux/reading-annotation-system/development-materials-checklist.md

Do not continue broad page styling. First implement component-level states:
ReaderContextBar, AnnotationGlyph, InlineMark restyle, grammar note collapsed/expanded, sentence analysis collapsed/expanded, WordLookupSlip, DictionaryNoteSheet, and feedback entry points.

Do not change backend schema. Do not add raster UI icons. Do not use the old C mark.

Submit screenshots for the required review states listed in agent-correction-brief.md.
```

## Need More Detail Images?

No additional reference image is required for the current core correction pass. The aligned spec board, state matrix, and three target viewport screenshots are enough to implement and review the reader, annotation cards, mini lookup, dictionary sheet, save states, and feedback entry points.

Optional future detail sheets may still be useful for:

1. Reader settings tray: font size, line height, theme, annotation density, and translation visibility.
2. `AnnotationGlyph` construction detail: exact sizes, active states, and disabled states if the coded glyphs keep drifting.
3. Loading, empty, and error states if they become part of the next review cycle.

Current reference set:

- `assets/component-spec-board.png`
- `assets/state-matrix-reference.png`
- `assets/target-viewport-reader-annotations.png`
- `assets/target-viewport-mini-lookup.png`
- `assets/target-viewport-dictionary-sheet.png`
- `assets/annotation-glyph-detail.svg`
- `assets/annotation-note-card-detail.svg`
- `assets/annotation-edge-states-detail.svg`

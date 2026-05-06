# Claread Reading Annotation System

> Status: approved design direction, ready for development handoff.
> Scope: reader surface, inline annotations, sentence notes, word lookup, saved vocabulary, and reader controls.

This directory is the UI/UX handoff package for the Claread reading and annotation redesign. It should be treated as the source of truth for development agents working on this area.

## Start Here

For implementation agents:

1. Read the project-level design context: `.impeccable.md`.
2. Read this file.
3. If this is a new implementation, read `agent-handoff.md`.
4. If this is a correction after a failed implementation, read `agent-correction-brief.md` first.
5. Use `implementation-mapping.md` and `development-materials-checklist.md` while coding.
6. Use the images in `assets/` as direction references, not pixel-perfect specs.

## Product Positioning

Claread should read as:

1. A premium mobile reading product.
2. A calm note-taking and annotation product.
3. An English support tool.

The UI should not look like a cram-school English app, a generic dictionary app, or an AI dashboard. The reading surface is the hero. AI explanations should feel like quiet margin intelligence: available, precise, and easy to dismiss.

## Approved Assets

| File | Purpose | Status |
|---|---|---|
| `assets/component-spec-board.png` | Component-level dimensions, tokens, and Do / Don't rules. | Primary implementation spec |
| `assets/state-matrix-reference.png` | Required state matrix for reader, annotation, lookup, save, and feedback states. | Primary implementation spec |
| `assets/target-viewport-reader-annotations.png` | Target mobile viewport for reader annotations and expanded notes. | Primary screenshot reference |
| `assets/target-viewport-mini-lookup.png` | Target mobile viewport for mini word lookup slip. | Primary screenshot reference |
| `assets/target-viewport-dictionary-sheet.png` | Target mobile viewport for full dictionary note sheet. | Primary screenshot reference |
| `assets/annotation-glyph-detail.svg` | Detail board for custom `AnnotationGlyph` variants, sizing, and active/disabled states. | Supplemental detail reference |
| `assets/annotation-note-card-detail.svg` | Detail board for collapsed note tabs, expanded note cards, sentence-analysis cards, and feedback rows. | Supplemental detail reference |
| `assets/annotation-edge-states-detail.svg` | Detail board for dense annotation stacking, lookup loading/empty/error, and feedback selected states. | Supplemental detail reference |

Outdated early direction assets have been removed. Do not reintroduce old visual directions that conflict with the approved references above.

## Visual Reference Priority

The approved assets now use one aligned component language. Do not reference archived images from earlier rounds.

1. Use `assets/component-spec-board.png` as the production mobile component reference for:
   - `ReaderContextBar`
   - reader controls
   - annotation expanded notes
   - feedback button rows
   - mini word lookup slip
   - full dictionary note sheet
   - article-end feedback
   - card radius, shadow, spacing, and button hierarchy
2. Use `assets/component-spec-board.png` and `component-spec.md` for micro rules:
   - `grammar_note` collapsed tab overflow behavior
   - long grammar titles collapsing to `语法`
   - `sentence_analysis` collapsed copy as `句式解析`
   - not showing chunk counts in collapsed sentence-analysis entries
   - temporary sentence-analysis chunk rows after expansion
   - `AnnotationGlyph` shape language
   - note-tab max width and single-line ellipsis behavior
3. Use `assets/target-viewport-reader-annotations.png` for sentence-analysis interaction flow:
   - clean default reading state
   - no permanent inline mark
   - temporary chunk marks only while expanded
   - compact chunk list / reading map behavior
   Do not copy its older folded-corner card treatment if it conflicts with the production component style.
4. Use the supplemental SVG boards only for local component details: glyph construction, note-card anatomy, dense mark stacking, degraded lookup states, feedback selection.
5. When a detail is not visible in screenshots, follow `component-spec.md` first, then `assets/component-spec-board.png`. Do not copy archived card treatments, folded corners, or side annotation rails into the current reader page unless a later design explicitly asks for that rail.

## Documents

| File | Purpose |
|---|---|
| `agent-handoff.md` | One-page implementation handoff for Claude/Gemini agents. |
| `agent-correction-brief.md` | Correction brief for implementations that drift from the approved design direction. |
| `formal-design-brief.md` | Formal UI constraints for grammar note, sentence analysis, drop cap, reader customization, and word lookup. |
| `component-spec.md` | Concrete component specs, tokens, state requirements, and screenshot references for implementation. |
| `implementation-mapping.md` | Maps approved UI direction to current backend schema and frontend components. |
| `word-lookup-and-vocabulary-ux.md` | Design brief for point-word lookup, workflow vocabulary marks, phrase/context glosses, and saved vocabulary states. |
| `development-materials-checklist.md` | Implementation-oriented checklist for components, tokens, fixtures, and optional assets. |

## Core Direction

- Paper first: warm off-white reading surface, not pure white.
- Annotation as stationery: highlights, underlines, folded notes, and compact entries should feel like reading tools, not UI chips.
- Progressive disclosure: weak inline signals by default, local explanation on tap, deeper detail only on expansion.
- Low color noise: semantic colors exist, but muted and low opacity.
- Brand restraint: use the Claread aperture/shutter Logo quietly; never use the retired old `C` loading mark.
- Implementation practicality: core UI should be Taro components and SCSS tokens, not raster UI assets.

## Schema Compatibility

The design must respect the current workflow output:

| Workflow output | Existing frontend capability | Design rule |
|---|---|---|
| `vocab_highlight` | `inline_mark`, background, clickable | Warm yellow highlighter, single-word emphasis |
| `phrase_gloss` | `inline_mark`, background, clickable | Muted lavender phrase sweep, AI phrase meaning first |
| `context_gloss` | `inline_mark`, underline, clickable | Fine blue pencil underline, context meaning first |
| `grammar_note` | `inline_mark` underline, non-clickable, plus `sentence_entry` | Fine purple-gray structural marks, compact footnote entry |
| `sentence_analysis` | `sentence_entry` only, optional chunks parsed from content | No default inline mark; expand to temporary chunk marking |
| `translations` | sentence-level translation | Secondary text layer, user-toggleable |

## Approved Decisions

- Product order is reading + notes + English support.
- `grammar_note` collapsed tabs may show `语法 · {title}` only when the title is short.
- Long grammar titles collapse to `语法`; the full title appears inside the expanded footnote.
- `sentence_analysis` collapsed entry copy is always `句式解析`; do not expose chunk count as `x段`.
- `sentence_analysis` chunks are temporary; they appear only while expanded and disappear when collapsed.
- Annotation icons should use a custom `AnnotationGlyph` system instead of generic Lucide-style icons.
- Point-word lookup should become `WordLookupSlip` plus `DictionaryNoteSheet`.
- `vocab_highlight`, `phrase_gloss`, and `context_gloss` need distinct mini/full lookup states because their schema payloads differ.
- Saved vocabulary must distinguish `记入生词本`, `加入当前语境`, `已记入`, `已记入 · n个语境`, and `已掌握`.
- `reading_goal` and `reading_variant` belong in a quiet `ReaderContextBar`, not a strong exam-style badge.
- Feedback is a separate UI layer with entry points inside annotation detail, word lookup, and article-end states.
- `assets/component-spec-board.png` and `component-spec.md` are the references for context bar and feedback implementation.
- Reader settings are out of scope for this package. Treat font size, line height, theme, translation visibility, annotation density, defaults, and persistence as a separate future package under `docs/uiux/reading-settings-system/`.

## Recommended Development Order

1. Add reader and annotation SCSS tokens.
2. Build `AnnotationGlyph`.
3. Restyle `InlineMark` and `ClickableWord`.
4. Refactor `WordPopup` visually into `WordLookupSlip` and `DictionaryNoteSheet`.
5. Add `LookupSaveState` helper and action copy.
6. Add source-context excerpt in the full sheet.
7. Add feedback entry points for annotation, lookup, and article-level feedback.
8. Add fixture states for local UI preview.
9. Do not implement reader customization tray in this package; start a separate reading settings design and business-logic package first.

## Review Expectations

When development is ready for review, provide:

- Screenshots or simulator captures for narrow mobile viewport.
- Before/after screenshots compared against the three `assets/target-viewport-*.png` references.
- A note explaining any schema limitations or deviations from this design package.
- Build/typecheck output.

Review should prioritize reading immersion, schema compatibility, state coverage, and visual restraint.

# Claread Reading Annotation System

> Status: approved design direction, ready for development handoff.
> Scope: reader surface, inline annotations, sentence notes, word lookup, saved vocabulary, and reader controls.

This directory is the UI/UX handoff package for the Claread reading and annotation redesign. It should be treated as the source of truth for development agents working on this area.

## Start Here

For implementation agents:

1. Read the project-level design context: `.impeccable.md`.
2. Read this file.
3. Read `agent-handoff.md`.
4. Use `implementation-mapping.md` and `development-materials-checklist.md` while coding.
5. Use the images in `assets/` as direction references, not pixel-perfect specs.

## Product Positioning

Claread should read as:

1. A premium mobile reading product.
2. A calm note-taking and annotation product.
3. An English support tool.

The UI should not look like a cram-school English app, a generic dictionary app, or an AI dashboard. The reading surface is the hero. AI explanations should feel like quiet margin intelligence: available, precise, and easy to dismiss.

## Approved Assets

| File | Purpose | Status |
|---|---|---|
| `assets/product-direction-overview.png` | Product-level direction across home, reader, annotations, word lookup, vocabulary library, and design system. | Primary overall reference |
| `assets/reading-annotation-current-overview.png` | Focused direction for reading, word lookup, saved vocabulary, and custom annotation glyphs. | Primary module reference |
| `assets/annotation-micro-rules.png` | Micro rules for long grammar titles, sentence-analysis entry copy, and custom annotation glyphs. | Detail reference |
| `assets/sentence-analysis-final-detail.png` | Detail direction for `sentence_analysis`: clean default, temporary chunks, compact reading map. | Detail reference |

Outdated early direction assets have been removed. Do not reintroduce old visual directions that conflict with the approved references above.

## Documents

| File | Purpose |
|---|---|
| `agent-handoff.md` | One-page implementation handoff for Claude/Gemini agents. |
| `formal-design-brief.md` | Formal UI constraints for grammar note, sentence analysis, drop cap, reader customization, and word lookup. |
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

## Recommended Development Order

1. Add reader and annotation SCSS tokens.
2. Build `AnnotationGlyph`.
3. Restyle `InlineMark` and `ClickableWord`.
4. Refactor `WordPopup` visually into `WordLookupSlip` and `DictionaryNoteSheet`.
5. Add `LookupSaveState` helper and action copy.
6. Add source-context excerpt in the full sheet.
7. Add fixture states for local UI preview.
8. Only after the core reading/lookup pieces are stable, implement reader customization tray.

## Review Expectations

When development is ready for review, provide:

- Screenshots or simulator captures for narrow mobile viewport.
- Before/after screenshots for `InlineMark`, `ClickableWord`, mini lookup, full dictionary sheet, and sentence-analysis expanded state.
- A note explaining any schema limitations or deviations from this design package.
- Build/typecheck output.

Review should prioritize reading immersion, schema compatibility, state coverage, and visual restraint.

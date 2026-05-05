# Claread Reading Annotation System

> Status: concept direction approved for `grammar_note` and `sentence_analysis` detail design.  
> Scope: reading, inline annotation, sentence-level notes, reader customization.

This directory is the working package for the next Claread reading and note-taking UI/UX redesign. It mirrors the purpose of `docs/uiux/loading-animation/`: keep approved visual references, implementation constraints, and handoff notes in one place before product code changes.

## Assets

| File | Purpose | Status |
|---|---|---|
| `assets/reading-notes-system-overview.png` | Overall reading + notes system concept. Useful for product direction, not a final implementation spec. | Direction reference |
| `assets/grammar-sentence-analysis-details.png` | Approved detail direction for inline grammar marks and sentence analysis entries. | Primary design reference |

## Product Positioning

Claread should read as:

1. A premium mobile reading product.
2. A calm note-taking and annotation product.
3. An English support tool.

The UI should not look like a cram-school English app. The reading surface is the hero. AI explanations should feel like margin intelligence: available, precise, and quiet.

## Design Direction

- Paper first: warm off-white reading surface, not pure white.
- Annotation as stationery: highlights, underlines, brackets, and note tabs should feel like highlighter, pencil, and notebook marks.
- Progressive explanation: show weak inline signals by default, reveal explanation only on tap.
- Low color noise: semantic annotation colors exist, but they are muted and low opacity.
- WeChat mini program practicalities: avoid large texture images in runtime; prefer CSS/SVG-like shapes where possible.

## Schema Compatibility

The design must respect the current workflow output:

| Workflow output | Existing frontend capability | Design rule |
|---|---|---|
| `vocab_highlight` | `inline_mark`, background, clickable | Warm yellow highlighter, single-word emphasis |
| `phrase_gloss` | `inline_mark`, background, clickable | Muted lavender phrase sweep |
| `context_gloss` | `inline_mark`, underline, clickable | Cool blue pencil underline |
| `grammar_note` | `inline_mark` underline, non-clickable, plus `sentence_entry` | Fine purple-gray structural marks in text, compact sentence-end entry |
| `sentence_analysis` | `sentence_entry` only, optional chunks parsed from content | No default inline mark; show sentence-end entry, expand to temporary chunk marking |
| `translations` | sentence-level translation | Secondary text layer, user-toggleable |

## Next Step

Before implementation, create formal detail designs for:

1. `grammar_note` collapsed and expanded states.
2. `sentence_analysis` collapsed and expanded states.
3. Drop-cap first paragraph reading style.
4. Reader customization tray.
5. Word lookup mini card adjusted to the same paper-note visual language.


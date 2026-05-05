# Formal Design Brief

Use this brief when generating or reviewing the next formal design drafts for the reading and annotation system.

## Goal

Create final UI detail drafts for Claread's mobile reading and annotation experience. The design must preserve immersion while supporting in-flow AI explanations.

Primary current overview reference:

- `assets/product-direction-overview.png`
- `assets/reading-annotation-current-overview.png`

## Must Match Current Workflow

The design must not assume extra backend fields unless explicitly marked as a future enhancement.

### `grammar_note`

Available data:

- `inline_mark.annotation_type = grammar_note`
- `inline_mark.render_type = underline`
- `inline_mark.visual_tone = grammar`
- `inline_mark.clickable = false`
- `inline_mark.anchor.kind = text | multi_text`
- `multi_text.parts[].role` may exist
- related `sentence_entry.entry_type = grammar_note`
- `sentence_entry.label`, `title`, `content`

Required states:

- Inline default.
- Sentence-entry collapsed.
- Expanded explanation.
- Multi-span grammar relation.
- Active/expanded state with role labels.

### `sentence_analysis`

Available data:

- no inline mark
- `sentence_entry.entry_type = sentence_analysis`
- `sentence_entry.label`, `title`, `content`
- optional chunks can be parsed from content

Required states:

- Collapsed entry after sentence.
- Expanded sentence chunk marking.
- Compact chunk explanation list.

## Visual Requirements

- Warm paper background.
- Serif English reading typography.
- Chinese translation secondary and quieter.
- Thin pencil-like grammar marks.
- Low-opacity highlighter marks.
- No thick purple blocks.
- No large cards interrupting every sentence.
- No decorative illustrations inside the reader.
- UI controls should feel native and Apple-like: restrained, tactile, low-friction.

## Detail Drafts To Produce

1. `grammar_note` default, collapsed entry, expanded entry.
2. `grammar_note` multi-span structure with roles.
3. `sentence_analysis` collapsed entry.
4. `sentence_analysis` expanded chunk mode.
5. Drop-cap first paragraph.
6. Reader customization tray.
7. Word lookup card in the same design language.

## Word Lookup And Vocabulary

Reference: `word-lookup-and-vocabulary-ux.md`.

Current schema supports three separate lookup-oriented mark types:

- `vocab_highlight`: single-word dictionary lookup, no AI glossary payload.
- `phrase_gloss`: phrase lookup with `glossary.zh` and `glossary.phrase_type`.
- `context_gloss`: context-sensitive lookup with `glossary.gloss` and `glossary.reason`.

Design requirements:

- Mini lookup should be a lightweight reading slip anchored to the tapped word.
- Full lookup should be a paper-like dictionary note sheet, not a heavy modal.
- AI phrase/context explanations appear before dictionary content only when `glossary` exists.
- Saved vocabulary state must show new, merged, already saved, and mastered states clearly.
- Dense saved-vocab highlights must remain quieter than active workflow annotations.

## Micro Rules

### Grammar Tab Text

- Collapsed `grammar_note` tabs use `语法 · {title}` only for short titles.
- Medium titles should stay on one line and truncate with ellipsis.
- Long titles should collapse to `语法`; the full `title || label` appears in the expanded footnote.
- The collapsed tab should not exceed roughly 60% of the reading column width.

### Sentence Analysis Entry Copy

- Collapsed `sentence_analysis` entry copy is `句式解析`.
- Do not show chunk count in the entry label, for example avoid `句式解析 · 4段`.
- Chunk count and reading order are expressed only inside the expanded breakdown rows.

### Annotation Glyphs

- Use a custom `AnnotationGlyph` system for annotation entry icons.
- Avoid generic feature icons for core annotation types.
- Glyphs should use a quiet paper-annotation style: rounded caps, thin strokes, muted default color, subtle active tint.
- Required glyphs: `grammar_note`, `sentence_analysis`, `vocab`, `phrase`, `context`, `merged_note`.

Reference: `assets/annotation-micro-rules.png`.

### Sentence Analysis

- Collapsed copy is `句式解析`.
- The default reading state has no permanent sentence structure markings.
- Expanded state may temporarily show chunk underlines, circled sequence markers, and a compact reading map.
- Collapsing the entry returns the sentence to clean reading.

Reference: `assets/sentence-analysis-final-detail.png`.

## Acceptance Criteria

- The design can be implemented with the current schema.
- The reader remains readable if all annotations are hidden.
- The reader remains readable if annotations are dense.
- A sentence with both grammar note and sentence analysis does not become visually noisy.
- The expanded explanation can fit on a mobile screen without pushing too much text away.
- The same language works in immersive and intensive reading modes.

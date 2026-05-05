# Formal Design Brief

Use this brief when generating or reviewing the next formal design drafts for the reading and annotation system.

## Goal

Create final UI detail drafts for Claread's mobile reading and annotation experience. The design must preserve immersion while supporting in-flow AI explanations.

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

## Acceptance Criteria

- The design can be implemented with the current schema.
- The reader remains readable if all annotations are hidden.
- The reader remains readable if annotations are dense.
- A sentence with both grammar note and sentence analysis does not become visually noisy.
- The expanded explanation can fit on a mobile screen without pushing too much text away.
- The same language works in immersive and intensive reading modes.


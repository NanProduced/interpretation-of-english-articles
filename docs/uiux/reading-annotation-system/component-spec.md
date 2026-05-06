# Claread Reading Annotation Component Spec

> Status: implementation specification.
> Purpose: convert approved visual direction into concrete component rules for Taro / WeChat Mini Program implementation.

This file is the component-level source of truth for implementation agents. Use it together with `.impeccable.md`, `README.md`, `agent-handoff.md`, and `agent-correction-brief.md`.

## Design References

Use these generated materials for implementation and visual review:

| File | Use |
|---|---|
| `assets/component-spec-board.png` | Main component measurements, tokens, and Do / Don't rules. |
| `assets/state-matrix-reference.png` | Required states for reader, annotation notes, word lookup, dictionary sheet, save states, and feedback. |
| `assets/target-viewport-reader-annotations.png` | Target mobile viewport for reader, inline marks, grammar note, sentence-analysis note. |
| `assets/target-viewport-mini-lookup.png` | Target mobile viewport for anchored mini word lookup slip. |
| `assets/target-viewport-dictionary-sheet.png` | Target mobile viewport for full dictionary note sheet. |
| `assets/annotation-glyph-detail.svg` | Supplemental detail for `AnnotationGlyph` variants and states. |
| `assets/annotation-note-card-detail.svg` | Supplemental detail for note tab/card anatomy and feedback footer structure. |
| `assets/annotation-edge-states-detail.svg` | Supplemental detail for dense annotations, degraded lookup states, and feedback selection. |

If images disagree, use this order:

1. `component-spec-board.png`
2. `target-viewport-*.png`
3. `state-matrix-reference.png`
4. `annotation-*-detail.svg` for local component details only

Do not copy archived design-board card treatments into production UI.

Reader customization settings are out of scope for this component spec. Font size, line height, theme, translation visibility, annotation density, defaults, and persistence should be specified in a separate future package under `docs/uiux/reading-settings-system/`.

## Product Hierarchy

Every component must preserve this order:

1. Reading.
2. Notes and annotation.
3. English support.

If an explanation component makes the article harder to read, reduce its visual weight.

## Core Tokens

Use one reader token set for this module. Avoid mixing old `--grammar-surface`, `--sentence-surface`, or generic dashboard card tokens into reader components.

```scss
--reader-paper: #FAF9F6;
--reader-surface: #FFFFFF;
--reader-paper-deep: #F6F3EC;
--reader-paper-warm: #FBF9F4;
--reader-ink: #111111;
--reader-muted: #7A7D86;
--reader-subtle: #9BA0A8;

--reader-border-light: rgba(17, 17, 17, 0.04);
--reader-border-subtle: rgba(17, 17, 17, 0.07);
--shadow-reader-sm: 0 4rpx 14rpx rgba(17, 17, 17, 0.045);
--shadow-reader-md: 0 10rpx 30rpx rgba(17, 17, 17, 0.08);
--shadow-reader-lg: 0 18rpx 56rpx rgba(17, 17, 17, 0.12);

--annotation-vocab-bg: rgba(242, 196, 84, 0.28);
--annotation-vocab-bg-active: rgba(242, 196, 84, 0.38);
--annotation-phrase-bg: rgba(151, 126, 224, 0.18);
--annotation-phrase-bg-active: rgba(151, 126, 224, 0.28);
--annotation-context-line: rgba(76, 145, 194, 0.72);
--annotation-context-line-active: rgba(76, 145, 194, 0.88);
--annotation-grammar-line: rgba(116, 102, 148, 0.62);
--annotation-grammar-line-active: rgba(116, 102, 148, 0.78);
--annotation-grammar-surface: rgba(116, 102, 148, 0.06);

--radius-note: 18rpx;
--radius-slip: 24rpx;
--radius-card: 28rpx;
--radius-sheet: 34rpx;
--radius-pill: 999rpx;
```

## ReaderContextBar

Purpose: quiet metadata row under reader tabs.

Content:

- Source: `手动输入` or `每日文章`.
- Goal / variant: example `考试备考（CET-4/6）`.
- Mode: `精读` or `原文`.
- Optional edit pencil.

Spec:

| Property | Value |
|---|---|
| Height | about `44rpx` |
| Padding | `16rpx var(--reader-padding) 4rpx` |
| Font size | `23rpx` |
| Text color | `--reader-muted`; source may use `--reader-subtle` |
| Gap | `12rpx` |
| Divider | `·`, muted, opacity about `0.55` |
| Background | transparent |

Rules:

- Do not render strong badges for `reading_goal` or `reading_variant`.
- Do not use exam red / purple chips.
- Long variant text must truncate on one line.

## InlineMark

Purpose: stationery-like signals inside reading text.

| Type | Style |
|---|---|
| `vocab_highlight` | Warm yellow wash, `--annotation-vocab-bg`, no border. |
| `phrase_gloss` | Muted lavender sweep, `--annotation-phrase-bg`, no border. |
| `context_gloss` | Fine blue underline, `2rpx`, `--annotation-context-line`. |
| `grammar_note` | Fine purple-gray underline plus very faint surface wash. |
| Saved vocab | Tiny folded-corner marker, not a strong badge. |

Rules:

- Marks must remain readable when dense.
- Highlight opacity should stay low.
- Do not use thick colored blocks.
- Do not add permanent sentence-analysis inline marks.

## NoteTab

Purpose: compact in-flow entry for annotation detail.

Spec:

| Property | Value |
|---|---|
| Surface | `--reader-surface` |
| Border | `1rpx solid rgba(17, 17, 17, 0.075)` |
| Shadow | subtle, near `--shadow-reader-sm` but lighter |
| Height | about `58rpx` |
| Padding | `11rpx 20rpx` |
| Radius | `10rpx` |
| Max width | `60%` of reading column |
| Font | `25rpx`, medium, one line |
| Overflow | ellipsis |

Copy rules:

- Short grammar title: `语法 · {title}`.
- Long grammar title: `语法`.
- Sentence analysis: always `句式解析`.
- Never show `句式解析 · 4段` in collapsed state.

## AnnotationNoteCard

Purpose: expanded grammar / sentence note attached to local reading flow.

Spec:

| Property | Value |
|---|---|
| Surface | `--reader-surface` |
| Border | `1rpx solid rgba(17, 17, 17, 0.07)` |
| Radius | `28rpx` |
| Shadow | `--shadow-reader-sm` |
| Width | full reading column, not page edge to edge |
| Padding | `26rpx 28rpx 20rpx` |
| Header | title left, small close icon right |
| Divider | subtle `rgba(17, 17, 17, 0.055)` |
| Body font | Chinese `28rpx`, line-height around `1.7` |
| Source excerpt | `--reader-paper-deep`, radius `14rpx`, not a heavy beige card |
| Feedback row | bottom, subtle top divider |

Feedback row:

- `有帮助`
- `不准确`
- `反馈`

Rules:

- The card should feel like a note slip, not a dashboard card.
- Do not use large beige explanation cards as the main surface.
- Do not use heavy shadows.
- Do not nest cards inside cards except for a very light source excerpt.

## Sentence Analysis Expanded

Default:

- No inline mark.
- Collapsed entry copy: `句式解析`.

Expanded:

- Temporary chunk marks may appear in the sentence.
- Chunk list uses compact rows.
- Row layout: marker, label, English fragment, optional explanation.

Spec:

| Property | Value |
|---|---|
| Chunk marker | circle, `28rpx` |
| Chunk row border | subtle bottom line |
| English fragment font | reader serif, about `25rpx` |
| Label font | `24rpx`, medium |

Rules:

- Chunk marks disappear when collapsed.
- Do not display chunk counts in collapsed entry.
- Avoid rainbow blocks; use muted sequence dots and fine underlines.

## WordLookupSlip

Purpose: anchored mini lookup card for quick meaning confirmation.

Spec:

| Property | Value |
|---|---|
| Width | `408rpx` |
| Surface | `--reader-surface` |
| Border | `1rpx solid rgba(17, 17, 17, 0.075)` |
| Radius | `24rpx` |
| Shadow | `0 10rpx 30rpx rgba(17,17,17,.11)` plus subtle 1px shadow |
| Padding | `22rpx 24rpx 18rpx` |
| Word font | serif, `34rpx`, bold |
| Meaning font | `25rpx`, line-height `1.42` |
| Tail | small, points to selected word |

Content hierarchy:

1. Word.
2. Phonetic and optional mini label.
3. One or two-line meaning.
4. Save action row.

Rules:

- Must anchor visually to selected word.
- Should not cover too much text.
- Do not center it like a modal.
- Do not render fake synonym data if dictionary API does not return it.
- `phrase_gloss` and `context_gloss` may prioritize glossary content.

## DictionaryNoteSheet

Purpose: full lookup sheet for dictionary depth, source context, save, and feedback.

Spec:

| Property | Value |
|---|---|
| Surface | `--reader-surface` |
| Top radius | `34rpx` |
| Shadow | `0 -14rpx 44rpx rgba(17,17,17,.12)` |
| Max height | `86vh` |
| Header word | serif, `60rpx`, bold |
| Horizontal padding | `40rpx` |
| Footer button height | `86rpx` |
| Primary button | black pill |
| Secondary button | white outline pill |

Content order:

1. Word, phonetic, optional filtered exam tag.
2. Source context excerpt.
3. AI phrase/context insight only when `glossary` exists.
4. Dictionary tabs and definitions.
5. Footer actions.

Exam tag rules:

- Only show exam tags when `reading_goal === 'exam'`.
- Filter by `reading_variant`.
- Example: `reading_variant=cet` shows only `CET-4` / `CET-6`.
- Do not show exam tags in daily or academic modes.

Save copy:

| State | Copy |
|---|---|
| Not saved | `记入生词本` |
| Same lemma, new context | `加入当前语境` |
| Already saved here | `已记入` |
| Multiple contexts | `已记入 · n个语境` |
| Mastered | `已掌握` |

Rules:

- The sheet should feel like a note sheet, not a generic dictionary app.
- Source context should be helpful but not heavier than the dictionary.
- AI insight should be visually distinct but quiet.

## Article-End Feedback

Purpose: ask about overall analysis quality without interrupting reading.

Spec:

- Place after article-end actions.
- Surface: very light `--reader-paper-deep` tint.
- Radius around `22rpx`.
- Title: `本次解读对你有帮助吗？`
- Actions: quiet icon buttons and `写反馈`.

Rules:

- This is secondary.
- Do not use large CTA cards.
- Do not interrupt reading with a modal unless the user taps `写反馈`.

## Required Implementation Fixtures

Create or maintain fixture states for visual review:

1. Reader clean default.
2. Dense inline annotations.
3. Grammar collapsed short title.
4. Grammar collapsed long title.
5. Grammar expanded with feedback row.
6. Sentence analysis collapsed.
7. Sentence analysis expanded with chunks.
8. Mini lookup loading.
9. Mini lookup word result.
10. Mini phrase gloss.
11. Mini context gloss.
12. Dictionary disambiguation.
13. Full dictionary sheet with context.
14. Save state variants.
15. Article-end feedback.

Screenshots should be captured at a mobile-equivalent viewport and compared against the generated target viewport images.

## Do / Don't

Do:

- Use one production card style.
- Keep reader text visually dominant.
- Use white note surfaces for cards and sheets.
- Use low-opacity marks and fine lines.
- Keep feedback secondary.
- Prefer progressive disclosure.

Don't:

- Mix beige design-board cards with production cards.
- Use purple badges or exam-style chips.
- Show chunk counts in collapsed sentence analysis.
- Invent backend fields to match a mock.
- Hardcode sample synonyms or dictionary details.
- Use generic dashboard card styling inside the reader.

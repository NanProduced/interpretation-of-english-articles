# Claread UI Design Context

## Product Identity

Claread 透读 is a premium mobile reading and note-taking product with English assistance.

The product hierarchy is strict:

1. Reading product first.
2. Note-taking and annotation product second.
3. English learning and dictionary tool third.

The interface must never feel like a cram-school English app, a generic dictionary app, or an AI dashboard. The reading surface is the hero. AI and English support should feel like quiet margin intelligence: precise, available, and easy to dismiss.

## Users

Primary users are adult readers with some English foundation:

- College students and exam-prep readers.
- Professionals reading English news, essays, research summaries, and industry material.
- English reading enthusiasts who want comprehension support without turning every article into a classroom exercise.

Usage is fragmented and mobile-first. Users may read during commuting, breaks, or late evening study. They need low cognitive load, fast return to the text, and progressive depth.

## Brand Personality

Three words:

- Calm
- Precise
- Editorial

Desired emotional effect:

- The app should feel trustworthy and quiet.
- Reading should feel focused, not busy.
- Notes should feel crafted and tactile, not system-generated.
- English support should feel intelligent but restrained.

## Brand Assets And Signal

Claread now has a dedicated brand Logo. Do not use the old `C` loading mark as the brand symbol.

Brand expression should be subtle:

- Use the Logo as a quiet identity signal, not an oversized decoration.
- Do not force the Logo into every state or combine it with unrelated icons.
- Brand feeling should come more from typography, paper surfaces, annotation language, and motion than from repeated logo placement.

## Aesthetic Direction

Core direction: Apple-like paper reading system.

This means:

- Warm off-white paper surfaces instead of pure white.
- Deep ink text, restrained secondary text, and careful hierarchy.
- Thin, tactile annotation marks that feel like stationery.
- Smooth, native-feeling motion with short duration and natural deceleration.
- High polish through spacing, alignment, touch feedback, and typography.

Useful references:

- Apple system UI restraint and hierarchy.
- Goodnotes-style paper and annotation tactility.
- Premium e-reader typography and quiet reading controls.
- Editorial mobile reading layouts with generous line height and clear margins.

Anti-references:

- Cram-school English apps.
- Dense dictionary panels.
- Dashboard-like cards inside the reader.
- Purple-heavy AI surfaces.
- Thick colored blocks, badges, and large shadows.
- Generic Lucide icons for core branded annotation concepts.
- Decorative gradients, glassmorphism, or ornamental blobs.

## Core Design Principles

### 1. Reading Surface First

The article must stay readable even when all annotations are present.

- English text owns the page.
- Translation, grammar, sentence analysis, and dictionary support are secondary layers.
- Default state must be calm.
- Expanded explanations should be local and reversible.

### 2. Notes As Stationery

Annotations should feel like highlighter, pencil, folded notes, and notebook slips, not UI chips.

- `vocab_highlight`: warm low-opacity highlighter wash.
- `phrase_gloss`: muted lavender highlighter sweep.
- `context_gloss`: fine blue pencil underline.
- `grammar_note`: thin structural underline and compact footnote entry.
- `sentence_analysis`: no permanent inline mark; expanded mode may temporarily show chunk guides.
- Saved vocabulary: tiny bookmark or folded-corner signal.

### 3. Progressive Disclosure

Show the least needed information first.

- Inline marks signal that help exists.
- Tap reveals a compact local explanation.
- Expand only for deeper dictionary, examples, sentence maps, or detailed notes.
- Avoid showing all explanations at once in the reading flow.

### 4. Reading + Notes + English

Every feature must honor this order.

- If a design improves English explanation but damages reading immersion, reject it.
- If a note is useful but visually interrupts the text, compress it or move it behind interaction.
- Dictionary content is a support layer, not the main product surface.

### 5. Apple-Like Polish

Apple-like does not mean copying iOS visuals. It means:

- Strong hierarchy.
- Fewer visible controls.
- Clear touch targets.
- Crisp alignment.
- Natural transitions.
- No unnecessary labels.
- A sense that every pixel has been chosen.

## Reading And Annotation Rules

### Grammar Note

`grammar_note` is a local grammar hint.

Current schema:

- Inline mark exists.
- Sentence entry exists.
- Inline mark is not clickable.
- Multi-span anchors may include roles.

Design rules:

- Collapsed entry may show `语法 · {title}` only when the title is short.
- Long titles collapse to `语法`; full title appears inside the expanded footnote.
- No thick purple blocks.
- No permanent role labels in default reading.
- Expanded state may reveal role labels and stronger structural marks.

### Sentence Analysis

`sentence_analysis` is a sentence-level structure view.

Current schema:

- No inline mark.
- Sentence entry only.
- Optional chunks can be parsed from content.

Design rules:

- Collapsed copy is always `句式解析`.
- Do not show `x段` in the collapsed entry.
- Default reading state stays clean.
- Expanded state may temporarily show chunk underlines, numbered reading order, and a compact reading map.
- Collapsing returns the sentence to normal reading.

### Word Lookup And Vocabulary

Point-word lookup is a reading loupe plus notebook slip.

Current workflow types:

- `vocab_highlight`: single-word dictionary lookup, no AI glossary payload.
- `phrase_gloss`: phrase or expression, with `glossary.zh` and `phrase_type`.
- `context_gloss`: context meaning, with `glossary.gloss` and `glossary.reason`.

Design rules:

- Mini lookup should be small, anchored, paper-like, and quick to dismiss.
- Full dictionary sheet should feel like a note sheet, not a modal dictionary app.
- `phrase_gloss` and `context_gloss` should prioritize AI context insight before dictionary fallback.
- `vocab_highlight` should prioritize dictionary meaning and save action.
- Save states must distinguish `记入生词本`, `加入当前语境`, `已记入`, `已记入 · n个语境`, and `已掌握`.

## Reader Customization

Reader customization is appropriate for Claread and should be part of the long-term reading product.

First version should support:

- Font size.
- Line height.
- Translation visibility.
- Annotation density.
- Warm paper / clean / night theme.

Implementation must stay practical for WeChat Mini Program:

- Prefer CSS class tokens over runtime-heavy style recalculation.
- Avoid shipping large custom font files until package size is reviewed.
- Keep settings local and immediate.

## Visual Tokens

Use these as direction, not rigid final values.

```scss
--color-ink: #111111;
--color-paper: #FAF9F6;
--color-paper-deep: #F4F1EA;
--color-line: rgba(17, 17, 17, 0.08);
--color-muted: #7A7D86;

--tone-vocab-bg: rgba(242, 196, 84, 0.28);
--tone-phrase-bg: rgba(151, 126, 224, 0.18);
--tone-context-line: rgba(76, 145, 194, 0.72);
--tone-grammar-line: rgba(116, 102, 148, 0.62);

--radius-sheet: 36rpx;
--radius-note: 24rpx;
--radius-pill: 999rpx;
```

Spacing:

- Base rhythm: `8rpx`.
- Reading horizontal padding: generous, usually `40rpx` to `56rpx`.
- Paragraph rhythm: enough for breathing, not card separation.
- Tap targets: at least `56rpx` where possible.

Typography:

- English reading text may use a refined serif stack already available in the project.
- Chinese UI and translation text should use system UI fonts.
- Avoid decorative or trendy font choices.
- Do not overuse bold in the reader.

## Motion

Motion should be native-feeling and quiet.

- Use transform and opacity.
- Prefer 160ms to 260ms for common interactions.
- Use ease-out quart/quint-like deceleration.
- No bounce, elastic, or playful overshoot.
- Bottom sheets should rise with calm momentum.
- Mini lookup should appear as if lifted from the selected word.

## WeChat Mini Program Constraints

The app uses Taro 3 + React for WeChat Mini Program.

Design and implementation must respect:

- Use `rpx` for layout.
- Avoid fragile selectors such as IDs and complex descendants.
- Avoid heavy runtime texture assets inside the reader.
- Keep package size under control.
- Avoid native component overlay conflicts.
- Use `ScrollView` carefully for long result pages.
- Minimize frequent large `setData` updates.
- Keep safe-area handling explicit.

## Implementation Bias

When implementing UI:

- Prefer small, reusable components with explicit state.
- Use schema-compatible rendering first.
- Only request backend schema changes when the UI benefit is real.
- Do not invent data fields in a design unless marked as a future enhancement.
- Keep the reading experience functional if annotations are hidden, dense, failed, or partially degraded.

## Current Approved Design Decisions

- The old loading `C` is retired as a brand symbol.
- Loading assets should use the actual Claread Logo and paper/reading metaphors subtly.
- `grammar_note` and `sentence_analysis` are separate UI systems.
- `sentence_analysis` uses temporary chunk marks only in expanded state.
- Annotation icons should become a custom `AnnotationGlyph` family.
- Point-word lookup should become `WordLookupSlip` plus `DictionaryNoteSheet`.
- The next UI work should preserve immersion while making notes and lookup feel premium and tactile.

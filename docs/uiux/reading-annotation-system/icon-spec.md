# Annotation Icon Spec

> Status: implementation asset spec.
> Scope: fixed icon assets for the reading annotation system.

Use these icons as source assets for `AnnotationGlyph`. Do not ask implementation agents to redraw annotation icons with ad hoc CSS, emoji, or generic icon libraries.

## Files

| Variant | File | Default token | Use |
|---|---|---|---|
| `grammar_note` | `icons/grammar-note.svg` | `--annotation-grammar-line` | Grammar note tab and expanded grammar card header. |
| `sentence_analysis` | `icons/sentence-analysis.svg` | `--annotation-context-line` | Sentence analysis tab and expanded sentence card header. |
| `vocab` | `icons/vocab.svg` | `rgba(185, 132, 24, 0.82)` | Vocabulary highlight and word lookup entry. |
| `phrase` | `icons/phrase.svg` | `rgba(105, 83, 176, 0.72)` | Phrase gloss and phrase insight. |
| `context` | `icons/context.svg` | `--annotation-context-line` | Context-sensitive gloss. |
| `feedback` | `icons/feedback.svg` | `--reader-muted` | Quiet feedback entry. |
| `saved_vocab` | `icons/saved-vocab.svg` | `--reader-ink` at low opacity | Saved vocabulary marker or save action. |

## Rendering Rules

- Base icon viewport: `48 x 48`.
- Default rendered size in note tabs: `28rpx` to `32rpx`.
- Expanded card header size: `32rpx` to `36rpx`.
- Stroke color uses `currentColor`; implementation controls color through the wrapper.
- Keep line caps rounded.
- Do not add filled icon containers by default.
- Do not replace these with lucide icons unless the design package explicitly changes.

## State Rules

| State | Rule |
|---|---|
| Default | Muted semantic color, opacity around `0.72` to `0.82`. |
| Active | Same icon, slightly stronger color or subtle tinted background. |
| Disabled | Same icon, opacity around `0.32`; do not switch icon shape. |
| Dense reader | Prefer smaller icon size and lower opacity instead of hiding all note entries. |

## Implementation Guidance

Recommended component:

```text
client/src/components/AnnotationGlyph/index.tsx
client/src/components/AnnotationGlyph/index.scss
```

Recommended props:

```ts
type AnnotationGlyphVariant =
  | 'grammar_note'
  | 'sentence_analysis'
  | 'vocab'
  | 'phrase'
  | 'context'
  | 'feedback'
  | 'saved_vocab'

type AnnotationGlyphProps = {
  variant: AnnotationGlyphVariant
  state?: 'default' | 'active' | 'disabled'
  size?: 'sm' | 'md' | 'lg'
}
```

In WeChat Mini Program, if direct external SVG rendering is inconvenient, translate each SVG into the component's inline shape implementation once. The shape should remain path-equivalent to the SVG assets.

Do not create a new visual interpretation during implementation.

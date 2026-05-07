# Annotation Icon Spec

> Status: implementation guidance.
> Scope: icon choices for the reading annotation system in WeChat Mini Program.

Use the existing `client/src/components/LucideIcon` runtime path first. Do not ship separate SVG icon files for this module unless a later design pass explicitly requires custom brand glyph assets.

The goal is not to exactly redraw icons from the reference images. The goal is to pick quiet, context-appropriate icons that support the paper-reading UI and render reliably in WeChat Mini Program.

## Preferred Icon Source

Use:

```text
client/src/components/LucideIcon/index.tsx
```

If an icon name is missing, add the Lucide path string to `SVG_PATHS` inside `LucideIcon` instead of adding external SVG files.

Do not use:

- Emoji.
- Random CSS-drawn icons.
- External SVG files loaded with `Image`.
- Web-style inline SVG assumptions that rely on `currentColor`.

## Mapping

| UI Meaning | Preferred LucideIcon | Fallback | Token |
|---|---|---|---|
| Grammar note | `network` | `layout-template` | `--annotation-grammar-line` |
| Sentence analysis | `sliders-horizontal` or `list-tree` | `layout-template` | `--annotation-context-line` |
| Vocabulary / save word | `bookmark` | `book` | `--reader-ink` or warm vocab tone |
| Phrase gloss | `link-2` | `languages` | muted phrase tone |
| Context gloss | `message-square-text` | `messageSquare` | `--annotation-context-line` |
| Feedback | `messageSquare` | `thumbs-up` / `thumbs-down` for quick reactions | `--reader-muted` |
| Close | `x` | none | `--reader-ink` |
| Expand / next | `chevron-right` | none | `--reader-muted` |
| Audio | `volume-2` | none | `--reader-muted` |

Some preferred names may not exist in the current `LucideIcon` map yet. Add only the few missing path strings needed for this module.

## Size Rules

| Placement | Size |
|---|---|
| Note tab icon | `28rpx` to `32rpx` |
| Expanded note header | `32rpx` to `36rpx` |
| Mini lookup action | `28rpx` |
| Sheet footer button | `28rpx` to `32rpx` |
| Tiny metadata / inline hint | `20rpx` to `24rpx` |

## Visual Rules

- Icons should feel secondary to text.
- Prefer line icons with rounded caps and moderate stroke.
- Do not put every icon inside a colored chip.
- Do not use strong purple or exam-style colors.
- Do not use oversized icons inside reader text.
- Use color tokens through `LucideIcon` props, not hard-coded one-off colors.

## Implementation Rule

`AnnotationGlyph` may remain as a semantic wrapper, but it should render `LucideIcon` internally:

```text
AnnotationGlyph(type="grammar_note") -> LucideIcon(name="network")
AnnotationGlyph(type="sentence_analysis") -> LucideIcon(name="sliders-horizontal")
```

This keeps component semantics stable while using a Mini Program-compatible icon pipeline.

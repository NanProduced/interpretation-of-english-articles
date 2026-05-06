# Claread Reading Settings System

> Status: planned, not ready for implementation.
> Scope: reader customization UI, preference model, persistence, defaults, and interaction with annotation rendering.

This package is intentionally separate from `docs/uiux/reading-annotation-system`.

Reading settings are not only a UI problem. They affect reading layout, annotation density, translation visibility, user preference persistence, default values, and possibly per-article or global behavior. Do not implement a settings tray from the annotation-system design package alone.

## Questions To Evaluate

Before designing or coding this module, decide:

1. Which settings are first-version product requirements.
2. Which settings are global user preferences versus per-article overrides.
3. Which settings should persist locally, sync to cloud, or reset per session.
4. How font size and line height affect annotation anchoring and sentence-entry spacing.
5. How annotation density should degrade dense marks without hiding critical notes.
6. How translation visibility interacts with original-only and intensive-reading modes.
7. Whether theme support starts with warm paper only, or includes clean and night themes.

## Candidate Setting Areas

These are candidates, not approved requirements:

- Font size.
- Line height.
- Translation visibility.
- Annotation density.
- Paper/theme mode.
- Tap behavior for word lookup versus annotation expansion.

## Dependency

The first reading settings pass should reuse the reader and annotation tokens from:

- `../reading-annotation-system/component-spec.md`
- `../reading-annotation-system/assets/component-spec-board.png`

It should not create a parallel visual language.

# Claread Academic Reading System

> Status: text-first design specification.
> Scope: academic mode result page, academic inline notes, research brief, term detail, logic/interpretation notes.
> Related source: `docs/differentiated/academic_reading_differentiation.md`.

This package defines the separate UI/UX direction for Claread academic mode.

Academic mode is not an exam-oriented annotation view. It is a research reading assistant: it helps the reader understand concepts, arguments, hedging, and careful academic translation while keeping the article readable.

## Start Here

For implementation agents:

1. Read `PRODUCT.md`.
2. Read `docs/differentiated/academic_reading_differentiation.md`, especially section 12.
3. Read this file and `component-spec.md`.
4. Implement from the written design language and schema contract. Do not rely on generated design images.
5. Do not copy the exam/grammar annotation card rhythm into academic mode.

## Design References

This package intentionally has no design-image dependency.

Implementation should be guided by:

- Product design context in `PRODUCT.md`.
- Academic product requirements in `docs/differentiated/academic_reading_differentiation.md`.
- The written component rules in `component-spec.md`.
- The current academic schema and frontend VM types.

Do not treat any generated academic screenshots as authoritative. If a mock image exists elsewhere, it is illustrative only and must not override this text spec.

## Product Positioning

Academic mode should feel like:

1. A quiet mobile paper reader.
2. A scholarly margin note system.
3. A research assistant that explains concepts and arguments.

It should not feel like:

- A vocabulary learning mode.
- A grammar teaching mode.
- A dashboard of AI summaries.
- A paper review app with dense research cards.

## Schema Boundary

Current frontend data comes from `AcademicRenderSceneVm`:

| Data | UI Role |
|---|---|
| `title` | Academic article title above the reader context bar. |
| `translations` | Secondary sentence-level Chinese translation. |
| `inline_marks` with `term_note` | Inline term signal and term detail entry. |
| `inline_marks` with `logic_note` | Inline argument/logic signal and logic note entry. |
| `sentence_entries` with `term_note` | Local concept note, usually compact. |
| `sentence_entries` with `logic_note` | Local argument note. |
| `sentence_entries` with `interpretation_note` | Local explanatory paraphrase, no permanent inline mark. |
| `content_summary` | Research brief, collapsed by default or compact by default. |
| `warnings` | Quiet degraded state or fragment note. |

Do not invent unsupported fields for v1. Paragraph roles exist in backend normalized data, but current render scene does not expose a dedicated `paragraph_role_marks` field. A paragraph role rail is therefore a future enhancement unless the projection changes.

## Design Direction

Academic mode keeps the Claread reader surface as the hero.

The main shift is from "annotation cards after sentences" to "scholarly notes around the reading flow":

- Research brief is a compact paper slip, not a dashboard summary card.
- Terms are treated as concepts, not vocabulary words.
- Logic notes explain argumentative force, not grammar.
- Interpretation notes appear only when a sentence needs decontextualization or disambiguation.
- Translation is important but still visually secondary to the English source.

## Visual Language

Academic mode should feel like a quiet research reading desk:

- Warm paper, deep ink, and restrained secondary text.
- Scholarly notes that feel like margin annotations or paper slips, not dashboard widgets.
- Low-chroma academic tones: blue-gray for concepts, muted amber for argument movement, muted green-gray for interpretation.
- Thin lines, soft borders, and small labels instead of bold badges.
- Sparse, deliberate color. Color identifies semantic type; it does not decorate the page.
- Typography should support long reading: English source uses the reader serif stack; Chinese UI, translation, and notes use system sans.
- The page should have a clear reading rhythm: title, quiet context, optional compact brief, then text. It should not start with a heavy AI summary.

Avoid:

- Purple-heavy AI labels.
- Thick colored side stripes.
- Large summary panels before the article.
- Dense stacks of explanation cards.
- Exam tags, vocabulary-drill language, grammar labels, or classroom phrasing.
- Raw backend values such as `academic_general`.

## Implementation Bias

Create academic-specific components instead of stretching `AnalysisCard`:

- `AcademicResultView`
- `AcademicResearchBrief`
- `AcademicParagraphBlock`
- `AcademicInlineMark`
- `AcademicNoteSlip`
- `AcademicTermSheet`

Reuse shared primitives where appropriate:

- `NavBar`
- `ReaderContextBar`
- `WordPopup` positioning ideas, not dictionary content assumptions
- `FeedbackSystem` entry points

Avoid making academic mode a large branch inside `ParagraphBlock`. If the same component needs too many academic-only conditions, split it.

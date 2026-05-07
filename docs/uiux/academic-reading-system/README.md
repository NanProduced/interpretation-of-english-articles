# Claread Academic Reading System

> Status: draft design direction for review.
> Scope: academic mode result page, academic inline notes, research brief, term detail, logic/interpretation notes.
> Related source: `docs/differentiated/academic_reading_differentiation.md`.

This package defines the separate UI/UX direction for Claread academic mode.

Academic mode is not an exam-oriented annotation view. It is a research reading assistant: it helps the reader understand concepts, arguments, hedging, and careful academic translation while keeping the article readable.

## Start Here

For implementation agents:

1. Read `PRODUCT.md`.
2. Read `docs/differentiated/academic_reading_differentiation.md`, especially section 12.
3. Read this file and `component-spec.md`.
4. Use the PNGs in `assets/` as visual references.
5. Do not copy the exam/grammar annotation card rhythm into academic mode.

## Approved Draft Assets

| File | Purpose |
|---|---|
| `assets/target-viewport-academic-reader.png` | Main academic result page, title, quiet context bar, compact research brief, and reading flow. |
| `assets/target-viewport-academic-notes.png` | In-reading term, logic, and interpretation note treatment. |
| `assets/target-viewport-academic-term-sheet.png` | Term detail sheet for `term_note` and academic context definition. |
| `assets/academic-component-spec-board.png` | Component vocabulary, tokens, and mapping from academic schema to UI. |

These images should stay visually close to `../reading-annotation-system/assets/`:

- Same warm paper surface.
- Same restrained navigation.
- Same reader-first hierarchy.
- Same low-noise stationery feeling.

They intentionally differ in information architecture:

- Academic mode uses research brief and local scholarly notes.
- Exam/daily mode uses grammar notes, sentence analysis, and word lookup.

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


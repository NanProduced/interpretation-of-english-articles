# Claread Academic Reading Component Spec

> Status: draft implementation spec for review.
> Purpose: describe how academic schema output should become a distinct Claread academic reading UI.

## Core Principle

Academic mode is content-understanding first. It should help the user read a difficult academic text without turning the page into a set of English lessons.

The hierarchy is:

1. English source text.
2. Research-grade Chinese translation.
3. Academic notes: term, logic, interpretation.
4. Research brief and feedback.

## Token Direction

Use the same reader tokens from `../reading-annotation-system/component-spec.md` and add only academic semantic tones.

```scss
--academic-term-line: rgba(73, 111, 143, 0.72);
--academic-term-surface: rgba(73, 111, 143, 0.08);
--academic-logic-line: rgba(181, 117, 35, 0.62);
--academic-logic-surface: rgba(181, 117, 35, 0.09);
--academic-interpret-line: rgba(85, 118, 102, 0.62);
--academic-interpret-surface: rgba(85, 118, 102, 0.08);
--academic-brief-surface: #FFFFFF;
--academic-brief-tint: #F7F3EC;
```

Rules:

- Keep academic colors lower in chroma than exam or vocabulary colors.
- Do not use purple-heavy AI badges.
- Do not use thick left stripes. Use thin lines, small labels, or quiet dot markers.

## Academic Header

Purpose: show that this is an academic reading result without turning the page into a mode dashboard.

Content:

- Article title from `AcademicRenderSceneVm.title`.
- Quiet `ReaderContextBar`: `手动输入 · 学术透读 · 精读`.
- Optional warning row only when `warnings` require it.

Spec:

| Property | Value |
|---|---|
| Title font | serif or reader title style, about `38rpx` to `42rpx` |
| Title line-height | `1.35` |
| Context row | same as reading annotation system |
| Bottom divider | `1rpx rgba(17,17,17,.05)` |

Rules:

- Do not show strong academic badges.
- Do not show `academic_general` raw values.
- Do not show a large summary card before the reader.

## AcademicResearchBrief

Purpose: give the user a research-level orientation without stealing the first screen.

Data:

- `content_summary.overview`
- `research_question`
- `methodology`
- `key_findings`
- `limitations`
- `completeness`

Default state:

- Compact by default.
- Shows title `内容导读`, completeness label, and one short overview.
- Has a quiet expand affordance.

Expanded state:

- Shows structured rows for research question, method, findings, limitations.
- Rows are paper rows, not nested dashboard cards.

Spec:

| Property | Value |
|---|---|
| Surface | `--reader-surface` |
| Radius | `28rpx` |
| Border | `1rpx solid rgba(17,17,17,.07)` |
| Shadow | same as note card, very light |
| Padding | `26rpx 28rpx` |
| Overview font | `27rpx`, line-height `1.62` |
| Section label | `22rpx`, muted, medium |

Rules:

- Do not place a thick colored side stripe on the brief.
- Do not expand automatically if it pushes the first paragraph below the fold.
- If `content_summary` is null, render nothing.

## Academic Inline Marks

| Type | Visual | Interaction |
|---|---|---|
| `term_note` | fine blue-gray underline or very light concept wash | Tap opens term slip or term sheet. |
| `logic_note` | amber hairline underline or tiny argument marker | Tap opens logic note slip. |
| `interpretation_note` | no permanent inline mark | Shown as local note entry only. |

Rules:

- Academic term marks are not saved vocabulary marks.
- Do not show exam tags in academic mode.
- Do not use the dictionary word sheet for `term_note` unless the user explicitly asks for dictionary depth.
- Dense academic marks should remain readable; prefer underlines over saturated backgrounds.

## AcademicNoteSlip

Purpose: local in-reading explanation for term, logic, or interpretation entries.

Variants:

- `term`: concept definition.
- `logic`: argumentative relation.
- `interpretation`: explanatory paraphrase.

Spec:

| Property | Value |
|---|---|
| Width | full reading column |
| Surface | `--reader-surface` |
| Radius | `26rpx` |
| Border | `1rpx solid rgba(17,17,17,.07)` |
| Shadow | `0 8rpx 24rpx rgba(17,17,17,.045)` |
| Header | small semantic label plus title |
| Body | `27rpx`, line-height `1.65` |
| Footer | quiet feedback actions |

Rules:

- A note slip should explain one idea.
- Avoid multiple note slips directly stacked after every sentence.
- If several entries belong to one sentence, group them under one compact `学术注释` entry and reveal details inside.

## AcademicTermSheet

Purpose: deeper concept explanation for `term_note`.

Data:

- `lookup_text`
- `glossary.zh`
- `glossary.zhUncertain`
- `glossary.contextDefinition`
- `glossary.termCategory`
- optional sentence context

Spec:

| Property | Value |
|---|---|
| Surface | `--reader-surface` |
| Top radius | `34rpx` |
| Max height | `72vh` to `78vh` |
| Header term | serif, `54rpx` |
| Category tag | muted tiny pill, not exam badge |
| Context box | warm paper tint |
| Primary section | `本文语境` before generic dictionary |
| Footer | `写反馈`, optional `加入术语表` if product supports it later |

Rules:

- Do not render `记入生词本` as the primary action for academic terms unless the product decides academic terms also enter vocabulary.
- Current v1 can use `写反馈` only in the footer.
- If `zh_uncertain` is true, show a quiet uncertainty note, not a warning block.

## Translation Layer

Academic translation is a comprehension aid, not a classroom answer.

Spec:

| Property | Value |
|---|---|
| Font | system Chinese |
| Size | `25rpx` to `27rpx` |
| Color | `rgba(17,17,17,.38)` to `rgba(17,17,17,.46)` |
| Line-height | `1.65` |

Rules:

- Preserve paragraph rhythm.
- Do not render translations in beige boxes by default.
- Translation notes are not currently exposed in `AcademicRenderSceneVm`; do not invent them.

## Feedback

Use the feedback-system package for detailed behavior.

Academic-specific feedback targets:

- `term_note`
- `logic_note`
- `interpretation_note`
- `content_summary`
- whole academic result

Feedback entry copy should be quiet:

- `有帮助`
- `不准确`
- `写反馈`

## Required Visual Review Fixtures

1. Academic first viewport with compact research brief.
2. Academic reader with term and logic marks.
3. Term detail sheet.
4. Logic note slip.
5. Interpretation note slip.
6. Missing `content_summary`.
7. Dense term marks.
8. `zh_uncertain=true`.
9. Fragment input warning.
10. Degraded academic result.


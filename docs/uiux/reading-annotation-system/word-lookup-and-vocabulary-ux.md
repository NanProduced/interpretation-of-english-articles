# Word Lookup And Vocabulary UX

> Status: design preparation.
> Scope: point-word lookup, workflow vocabulary annotations, phrase/context glosses, saved vocabulary states.

Primary visual reference:

- `assets/reading-annotation-current-overview.png`

## Product Role

Point-word lookup should feel like a reading loupe plus a notebook slip, not a separate dictionary app. It is a support layer inside the reading flow.

The hierarchy is:

1. Keep the article readable.
2. Let users confirm meaning quickly.
3. Let users save a word with its source context.
4. Reveal dictionary depth only when the user asks.

## Current Workflow Schema

The current workflow produces three dictionary-related inline mark types.

| Workflow type | Public `InlineMark` | Meaning | UI priority |
|---|---|---|---|
| `vocab_highlight` | `annotation_type=vocab_highlight`, `render_type=background`, `visual_tone=vocab`, `lookup_kind=word`, `glossary=null` | A high-value single word. The app should fetch dictionary data after tap. | Dictionary first |
| `phrase_gloss` | `annotation_type=phrase_gloss`, `render_type=background`, `visual_tone=phrase`, `lookup_kind=phrase`, `glossary.zh`, `glossary.phrase_type` | A phrase/expression whose meaning should be understood as a whole. | AI phrase meaning first, dictionary second |
| `context_gloss` | `annotation_type=context_gloss`, `render_type=underline`, `visual_tone=context`, `lookup_kind=word`, `glossary.gloss`, `glossary.reason` | A word/expression where the normal dictionary meaning is not enough for the current sentence. | Context meaning first, dictionary second |

Important constraints:

- `vocab_highlight.text` is guaranteed to be a single word.
- `phrase_gloss.text` may be multi-word, and single-token phrase gloss is allowed only for proper nouns or compounds.
- `context_gloss.text` can be a word or expression, but the current projection sets `lookup_kind=word`.
- All three rely on text anchors plus `occurrence`; there is no extra semantic position metadata.
- `vocab_highlight` does not include a short meaning in the workflow result, so mini lookup must tolerate dictionary loading.

## Current Frontend Flow

Point-word query is handled by `WordPopup`.

Current behavior:

- Any tapped word or clickable inline mark opens mini mode near the tap point.
- Mini mode fetches `/dict?q=...` and shows a compact meaning.
- Tapping mini mode expands to a bottom sheet.
- Full mode shows optional AI glossary, dictionary meanings, phrases, examples, feedback, favorite, and add-to-vocab actions.
- Adding vocabulary stores the dictionary entry plus source sentence/context into local storage, then syncs to cloud.
- Existing saved vocabulary is rendered back into the reader as an additional highlight layer.

Relevant files:

- `client/src/components/WordPopup/index.tsx`
- `client/src/components/WordPopup/index.scss`
- `client/src/components/InlineMark/index.tsx`
- `client/src/components/InlineMark/index.scss`
- `client/src/components/ClickableWord/index.tsx`
- `client/src/pages/result/hooks/useResultActions.ts`
- `client/src/pages/result/hooks/useResultEffects.ts`
- `client/src/services/storage/index.ts`
- `client/src/services/api/vocabulary.client.ts`
- `client/src/types/view/render-scene.vm.ts`

## Design Direction

### Reading Loupe

The mini lookup should be a light, anchored reading slip:

- Small enough to avoid covering a paragraph.
- Paper surface, subtle border, very soft shadow.
- A tiny tail pointing to the selected word.
- No heavy card chrome.
- One-line word header, then one or two lines of meaning.
- If dictionary is still loading, show a calm skeleton line instead of a spinner.

### Dictionary Sheet

The expanded lookup should be a bottom sheet, but visually closer to a paper note than a modal:

- Large word set in reading typography.
- Phonetic/audio as quiet secondary metadata.
- AI context block appears only when `glossary` exists.
- Dictionary tabs are secondary and compact.
- Footer actions are tactile but not oversized.
- Save state must be visible after adding: `已记入 · 2个语境` or `加入当前语境`.

### Annotation Tone

Inline vocabulary marks should not compete with grammar or sentence analysis.

| Tone | Default mark | Tap/active state |
|---|---|---|
| `vocab` | warm highlighter wash, low opacity | slightly deeper paper-yellow wash |
| `phrase` | lavender highlighter sweep, longer and calmer | show phrase as grouped expression |
| `context` | fine blue pencil underline | underline lifts into context slip |
| saved vocab | tiny folded-corner/bookmark signal | active state shows saved metadata in sheet |

Avoid:

- Thick purple blocks.
- Large inset shadows.
- Strong colored badges inside text.
- Reusing generic Lucide icons for every core dictionary state.

## Required States

### Mini Lookup

1. Plain word tap, dictionary loading.
2. Plain word tap, dictionary entry found.
3. `vocab_highlight`, dictionary entry found.
4. `phrase_gloss`, AI phrase meaning available.
5. `context_gloss`, context gloss and reason available.
6. Dictionary disambiguation result.
7. No result or network failure.

### Full Sheet

1. Entry result with meanings.
2. Entry result with examples and phrases.
3. Disambiguation candidate list.
4. AI phrase gloss plus dictionary fallback.
5. AI context gloss plus reason.
6. Add-to-vocab idle.
7. Add-to-vocab saved.
8. Add-to-vocab merged with existing lemma and multiple source contexts.

### Saved Vocabulary In Reader

1. Locally saved but not synced.
2. Synced new word.
3. Mastered word.
4. Same lemma appears in multiple forms.

## Recommended UI Model

### `WordLookupSlip`

Mini mode component.

Inputs:

- `lookupText`
- `mark.annotationType`
- `mark.visualTone`
- `glossary`
- `dictionaryResult`
- `loading`
- `savedState`

Display rules:

- If `glossary.zh` exists, show it before dictionary.
- If `glossary.gloss` exists, show it before dictionary and expose `reason` only in full sheet.
- If no glossary exists, show dictionary summary.
- If dictionary has disambiguation candidates, mini says `多个义项` and expands on tap.

### `DictionaryNoteSheet`

Full mode component.

Sections:

1. Header: word, phonetic, optional exam tags.
2. Context insight: only for `phrase_gloss` or `context_gloss`.
3. Definitions: dictionary meanings, phrases, examples.
4. Source context: original sentence with selected word softly marked.
5. Actions: save/update context, feedback, close.

### `VocabularySaveState`

State model for action copy.

| Condition | Copy |
|---|---|
| Not saved | `记入生词本` |
| Same lemma saved, current source not saved | `加入当前语境` |
| Same source already saved | `已记入` |
| Multiple source refs | `已记入 · n个语境` |
| Mastered | `已掌握` |

This may require a small frontend helper that compares `VocabEntry.sourceRefs` against current `recordId`, `sentenceId`, anchor text, and occurrence.

## Implementation Notes

### Feasible Without Schema Change

- Restyle inline marks and saved vocabulary markers.
- Restyle mini popup and full bottom sheet.
- Prioritize AI `glossary` content in mini/full views.
- Add disambiguation-specific mini state.
- Improve saved/merged action copy after `saveVocabEntry`.
- Add source sentence preview inside the full sheet using existing `contextSentence`.

### Small Frontend Additions Recommended

- Add a `savedLookupState` derived from local/cloud vocabulary.
- Pass current sentence id into word popup when available.
- Replace generic icons with the custom `AnnotationGlyph` family.
- Add compact skeleton lines for dictionary loading.

### Backend / Schema Enhancement Candidates

Not required for first implementation, but useful later:

- Preserve `lookup_kind=phrase` for multi-token `context_gloss`.
- Add optional `difficulty` or `reason_tag` for `vocab_highlight`.
- Return a short AI-generated `hint` for `vocab_highlight` when dictionary fetch is slow.

## Acceptance Criteria

- A user can tap a word and understand it without losing reading position.
- AI phrase/context explanations are visibly different from plain dictionary lookup.
- Saving a word clearly communicates whether it is new, merged, or already saved.
- Dense annotations still feel like paper marks, not UI chips.
- The full sheet never makes English learning feel like the product's primary identity.

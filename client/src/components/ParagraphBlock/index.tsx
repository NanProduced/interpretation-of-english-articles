import { useMemo } from 'react'
import { View, Text } from '@tarojs/components'
import { InlineMarkModel, SentenceEntryModel, TextAnchor, MultiTextAnchor, VisualTone, SentenceModel, TranslationModel } from '../../types/view/render-scene.vm'
import InlineMark from '../InlineMark'
import SentenceActionChip from '../SentenceActionChip'
import './index.scss'

const TONE_PRIORITY: Record<VisualTone, number> = {
  vocab: 1,
  phrase: 2,
  context: 3,
  grammar: 4,
}

interface ParagraphBlockProps {
  sentences: SentenceModel[]
  translations: TranslationModel[]
  showTranslation: boolean
  inlineMarks: InlineMarkModel[]
  activeMarkId?: string | null
  tailEntries: SentenceEntryModel[]
  pageMode: 'immersive' | 'bilingual' | 'intensive'
  onWordClick?: (mark: InlineMarkModel, word: string, event?: any) => void
  onChipClick?: (entry: SentenceEntryModel) => void
}

function findTextAnchorPosition(text: string, anchorText: string, occurrence: number = 1): number {
  let count = 0
  let pos = 0
  const safeOccurrence = occurrence || 1
  while (count < safeOccurrence) {
    const idx = text.indexOf(anchorText, pos)
    if (idx === -1) return -1
    count++
    if (count === safeOccurrence) return idx
    pos = idx + 1
  }
  return -1
}

function renderTextWithMarks(
  text: string,
  marks: InlineMarkModel[],
  activeMarkId?: string | null,
  onWordClick?: (mark: InlineMarkModel, word: string, event?: any) => void
) {
  if (marks.length === 0) {
    return <Text className='sentence-text'>{text}</Text>
  }

  const flatParts: Array<{ mark: InlineMarkModel; start: number; end: number; text: string }> = []
  
  marks.forEach((m) => {
    if (m.anchor.kind === 'text') {
      const pos = findTextAnchorPosition(text, m.anchor.anchorText, m.anchor.occurrence || 1)
      if (pos >= 0) {
        flatParts.push({ mark: m, start: pos, end: pos + m.anchor.anchorText.length, text: m.anchor.anchorText })
      }
    } else {
      m.anchor.parts.forEach((part, idx) => {
        const pos = findTextAnchorPosition(text, part.anchorText, part.occurrence || 1)
        if (pos >= 0) {
          const partMark: InlineMarkModel = {
            ...m,
            id: `${m.id}-part-${idx}`,
            parentId: m.id, // Track parent ID for activation
            anchor: {
              kind: 'text',
              sentenceId: m.anchor.sentenceId,
              anchorText: part.anchorText,
              occurrence: part.occurrence,
            },
          }
          flatParts.push({ mark: partMark, start: pos, end: pos + part.anchorText.length, text: part.anchorText })
        }
      })
    }
  })

  flatParts.sort((a, b) => {
    if (a.start !== b.start) return a.start - b.start
    if (a.end !== b.end) return b.end - a.end
    return TONE_PRIORITY[a.mark.visualTone] - TONE_PRIORITY[b.mark.visualTone]
  })

  const resultElements: Array<JSX.Element | string> = []
  let lastEnd = 0

  for (const item of flatParts) {
    if (item.start < lastEnd) continue

    if (item.start > lastEnd) {
      resultElements.push(text.slice(lastEnd, item.start))
    }

    const isActive = activeMarkId === item.mark.id || (item.mark.parentId && activeMarkId === item.mark.parentId)

    resultElements.push(
      <InlineMark
        key={item.mark.id}
        mark={item.mark}
        text={item.text}
        isActive={isActive}
        onClick={onWordClick}
      />
    )

    lastEnd = item.end
  }

  if (lastEnd < text.length) {
    resultElements.push(text.slice(lastEnd))
  }

  return <Text className='sentence-text'>{resultElements}</Text>
}

export default function ParagraphBlock({
  sentences,
  translations,
  showTranslation,
  inlineMarks,
  activeMarkId,
  tailEntries,
  pageMode,
  onWordClick,
  onChipClick,
}: ParagraphBlockProps) {
  
  // Assemble the paragraph translations into one block
  const fullTranslation = sentences
    .map(s => translations.find(t => t.sentenceId === s.sentenceId)?.translationZh)
    .filter(Boolean)
    .join(' ')

  // --- Rendering Functions for different modes ---

  // 1. Immersive mode: Simple English paragraph
  if (pageMode === 'immersive') {
    return (
      <View className='paragraph-block immersive'>
        <View className='english-paragraph'>
          <Text className='english-flow'>
            {sentences.map((sentence, idx) => {
              const sentenceMarks = inlineMarks.filter(mark => mark.anchor.sentenceId === sentence.sentenceId)
              return (
                <Text key={sentence.sentenceId} className='sentence-span'>
                  {renderTextWithMarks(sentence.text, sentenceMarks, activeMarkId, onWordClick)}
                  {idx < sentences.length - 1 ? <Text className='space-char'> </Text> : ''}
                </Text>
              )
            })}
          </Text>
        </View>
      </View>
    )
  }

  // 2. Bilingual mode: English paragraph + Translation paragraph
  if (pageMode === 'bilingual') {
    return (
      <View className='paragraph-block bilingual'>
        <View className='english-paragraph'>
          <Text className='english-flow'>
            {sentences.map((sentence, idx) => {
              const sentenceMarks = inlineMarks.filter(mark => mark.anchor.sentenceId === sentence.sentenceId)
              return (
                <Text key={sentence.sentenceId} className='sentence-span'>
                  {renderTextWithMarks(sentence.text, sentenceMarks, activeMarkId, onWordClick)}
                  {idx < sentences.length - 1 ? <Text className='space-char'> </Text> : ''}
                </Text>
              )
            })}
          </Text>
        </View>
        {fullTranslation && (
          <View className='translation-paragraph'>
            <Text className='translation-text'>{fullTranslation}</Text>
          </View>
        )}
      </View>
    )
  }

  // 3. Intensive mode: Sentence-by-sentence analysis (Separated layers)
  return (
    <View className='paragraph-block intensive'>
      {sentences.map((sentence) => {
        const sentenceMarks = inlineMarks.filter(mark => mark.anchor.sentenceId === sentence.sentenceId)
        const sentenceEntries = tailEntries.filter(entry => entry.sentenceId === sentence.sentenceId)
        const sentenceTranslation = translations.find(t => t.sentenceId === sentence.sentenceId)?.translationZh

        return (
          <View key={sentence.sentenceId} className='sentence-block'>
            {/* Layer 1: Main Text */}
            <View className='sentence-main'>
              <Text className='english-flow'>
                {renderTextWithMarks(sentence.text, sentenceMarks, activeMarkId, onWordClick)}
              </Text>
            </View>

            {/* Layer 2: Analysis Entries (Action Chips) */}
            {sentenceEntries.length > 0 && (
              <View className='sentence-analysis'>
                <View className='analysis-chips'>
                  {sentenceEntries.map((entry) => (
                    <SentenceActionChip
                      key={entry.id}
                      entry={entry}
                      onClick={onChipClick}
                    />
                  ))}
                </View>
              </View>
            )}

            {/* Layer 3: Translation */}
            {showTranslation && sentenceTranslation && (
              <View className='sentence-translation'>
                <Text className='translation-text'>{sentenceTranslation}</Text>
              </View>
            )}
          </View>
        )
      })}
    </View>
  )
}


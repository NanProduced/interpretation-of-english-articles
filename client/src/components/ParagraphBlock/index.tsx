import { useMemo } from 'react'
import { View, Text } from '@tarojs/components'
import { InlineMarkModel, SentenceEntryModel, TextAnchor, MultiTextAnchor, VisualTone, SentenceModel, TranslationModel } from '../../types/v2-render'
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
        const pos = findTextAnchorPosition(text, part.text, part.occurrence || 1)
        if (pos >= 0) {
          const partMark: InlineMarkModel = {
            ...m,
            id: `${m.id}-part-${idx}`,
            anchor: {
              kind: 'text',
              sentenceId: m.anchor.sentenceId,
              anchorText: part.text,
              occurrence: part.occurrence,
            },
          }
          flatParts.push({ mark: partMark, start: pos, end: pos + part.text.length, text: part.text })
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

    resultElements.push(
      <InlineMark
        key={item.mark.id}
        mark={item.mark}
        text={item.text}
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

  return (
    <View className='paragraph-block'>
      <View className='english-paragraph'>
        {/* Everything inside Text to allow inline wrapping */}
        <Text className='english-flow'>
          {sentences.map((sentence, idx) => {
            const sentenceMarks = inlineMarks.filter(mark => mark.anchor.sentenceId === sentence.sentenceId)
            const sentenceEntries = tailEntries.filter(entry => entry.sentenceId === sentence.sentenceId)
            
            return (
              <Text key={sentence.sentenceId} className='sentence-span'>
                {renderTextWithMarks(sentence.text, sentenceMarks, onWordClick)}
                
                {/* 句尾如果是最后一个词，保留一个自然空格或换行缓冲 */}
                {idx < sentences.length - 1 ? <Text className='space-char'> </Text> : ''}

                {/* 精读模式下的 Action Chip 内联显示 */}
                {pageMode === 'intensive' && sentenceEntries.length > 0 && (
                  <Text className='tail-entries-inline'>
                    {sentenceEntries.map((entry) => (
                      <SentenceActionChip
                        key={entry.id}
                        entry={entry}
                        onClick={onChipClick}
                      />
                    ))}
                    {idx < sentences.length - 1 ? <Text className='space-char'> </Text> : ''}
                  </Text>
                )}
              </Text>
            )
          })}
        </Text>
      </View>

      {showTranslation && fullTranslation && (
        <View className='translation-paragraph'>
          <Text className='translation-text'>{fullTranslation}</Text>
        </View>
      )}
    </View>
  )
}

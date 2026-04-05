import { useMemo } from 'react'
import { View, Text } from '@tarojs/components'
import { InlineMarkModel, SentenceEntryModel, VisualTone, SentenceModel, TranslationModel } from '../../types/view/render-scene.vm'
import InlineMark from '../InlineMark'
import SentenceActionChip from '../SentenceActionChip'
import ClickableWord from '../ClickableWord'
import { tokenizeText } from './utils'
import './index.scss'

const TONE_PRIORITY: Record<VisualTone, number> = {
  vocab: 1,
  phrase: 2,
  context: 3,
  grammar: 4,
}

export interface WordClickPayload {
  word: string
  mark: InlineMarkModel | null
  event?: any
}

interface ParagraphBlockProps {
  sentences: SentenceModel[]
  translations: TranslationModel[]
  showTranslation: boolean
  inlineMarks: InlineMarkModel[]
  activeMarkId?: string | null
  tailEntries: SentenceEntryModel[]
  pageMode: 'immersive' | 'bilingual' | 'intensive'
  onWordClick?: (payload: WordClickPayload) => void
  onChipClick?: (entry: SentenceEntryModel) => void
}

function findTextAnchorPosition(text: string, anchorText: string, occurrence = 1): number {
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

/**
 * 在已有标注的基础上，把"标注词之间"的普通英文文本也变成可点击词。
 * plainSegment: 标注词前后的普通文本（已被 text.slice 截取，不含标注词）
 */
function renderPlainSegmentAsClickableWords(
  plainText: string,
  onWordClick?: (payload: WordClickPayload) => void
): React.ReactNode[] {
  if (!plainText) return []
  const tokens = tokenizeText(plainText)
  return tokens.map((token, idx) => {
    if (token.type === 'word') {
      return (
        <ClickableWord
          key={`cw-${idx}`}
          word={token.text}
          onClick={(w) => onWordClick?.({ word: w, mark: null })}
        />
      )
    }
    return <Text key={`p-${idx}`}>{token.text}</Text>
  })
}

function renderTextWithMarks(
  text: string,
  marks: InlineMarkModel[],
  activeMarkId?: string | null,
  onWordClick?: (payload: WordClickPayload) => void
) {
  if (marks.length === 0) {
    // 无标注：整句普通文本 → 全部英文词可点击
    const tokens = tokenizeText(text)
    return (
      <Text className='sentence-text'>
        {tokens.map((token, idx) =>
          token.type === 'word' ? (
            <ClickableWord
              key={`cw-${idx}`}
              word={token.text}
              onClick={(w) => onWordClick?.({ word: w, mark: null })}
            />
          ) : (
            <Text key={`p-${idx}`}>{token.text}</Text>
          )
        )}
      </Text>
    )
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
            parentId: m.id,
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

  const resultElements: Array<React.ReactNode | string> = []
  let lastEnd = 0

  for (const item of flatParts) {
    if (item.start < lastEnd) continue

    // 先把标注词之前的普通文本渲染为可点击词
    if (item.start > lastEnd) {
      const plainSegment = text.slice(lastEnd, item.start)
      resultElements.push(...renderPlainSegmentAsClickableWords(plainSegment, onWordClick))
    }

    // 标注词本身
    const isActive = activeMarkId === item.mark.id || (item.mark.parentId && activeMarkId === item.mark.parentId)
    resultElements.push(
      <InlineMark
        key={item.mark.id}
        mark={item.mark}
        text={item.text}
        isActive={isActive}
        onWordClick={onWordClick}
      />
    )

    lastEnd = item.end
  }

  // 标注词之后的剩余文本
  if (lastEnd < text.length) {
    const plainSegment = text.slice(lastEnd)
    resultElements.push(...renderPlainSegmentAsClickableWords(plainSegment, onWordClick))
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
  const marksBySentenceId = useMemo(() => {
    const map = new Map<string, InlineMarkModel[]>()
    inlineMarks.forEach((m) => {
      const sid = m.anchor.sentenceId
      if (!map.has(sid)) map.set(sid, [])
      map.get(sid)!.push(m)
    })
    return map
  }, [inlineMarks])

  const entriesBySentenceId = useMemo(() => {
    const map = new Map<string, SentenceEntryModel[]>()
    tailEntries.forEach((e) => {
      if (!map.has(e.sentenceId)) map.set(e.sentenceId, [])
      map.get(e.sentenceId)!.push(e)
    })
    return map
  }, [tailEntries])

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
              const sentenceMarks = marksBySentenceId.get(sentence.sentenceId) || []
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
              const sentenceMarks = marksBySentenceId.get(sentence.sentenceId) || []
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
        const sentenceMarks = marksBySentenceId.get(sentence.sentenceId) || []
        const sentenceEntries = entriesBySentenceId.get(sentence.sentenceId) || []
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

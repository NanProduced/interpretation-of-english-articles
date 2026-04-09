import { useMemo, memo } from 'react'
import { View, Text } from '@tarojs/components'
import { InlineMarkModel, SentenceEntryModel, VisualTone, SentenceModel, TranslationModel } from '../../types/view/render-scene.vm'
import InlineMark from '../InlineMark'
import ClickableWord from '../ClickableWord'
import AnalysisCard, { type AnalysisCardProps } from '../AnalysisCard'
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
  inlineMarks: InlineMarkModel[]
  activeMarkId?: string | null
  selectedWord?: string | null
  tailEntries: SentenceEntryModel[]
  pageMode: 'immersive' | 'intensive'
  vocabList?: string[]
  onWordClick?: (payload: WordClickPayload) => void
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

function renderPlainSegmentAsClickableWords(
  plainText: string,
  selectedWord?: string | null,
  vocabList?: string[],
  onWordClick?: (payload: WordClickPayload) => void
): React.ReactNode[] {
  if (!plainText) return []
  const tokens = tokenizeText(plainText)
  return tokens.map((token, idx) => {
    if (token.type === 'word') {
      const isSaved = vocabList?.includes(token.text.toLowerCase())
      const isSelected = selectedWord === token.text
      return (
        <ClickableWord
          key={`cw-${idx}`}
          word={token.text}
          isSaved={isSaved}
          className={isSelected ? 'active' : ''}
          onClick={(w, e) => onWordClick?.({ word: w, mark: null, event: e })}
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
  selectedWord?: string | null,
  vocabList?: string[],
  onWordClick?: (payload: WordClickPayload) => void,
  isImmersive?: boolean
) {
  // 沉浸模式下只保留词汇相关的标记（vocab, phrase, context）
  const visibleMarks = isImmersive 
    ? marks.filter(m => ['vocab', 'phrase', 'context'].includes(m.visualTone))
    : marks

  if (visibleMarks.length === 0) {
    return (
      <Text className='sentence-text'>
        {renderPlainSegmentAsClickableWords(text, selectedWord, vocabList, onWordClick)}
      </Text>
    )
  }

  const flatParts: Array<{ mark: InlineMarkModel; start: number; end: number; text: string }> = []

  visibleMarks.forEach((m) => {
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

    if (item.start > lastEnd) {
      const plainSegment = text.slice(lastEnd, item.start)
      resultElements.push(...renderPlainSegmentAsClickableWords(plainSegment, selectedWord, vocabList, onWordClick))
    }

    if (!item.mark.clickable) {
      const toneClass = `tone-${item.mark.visualTone}`
      const tokens = tokenizeText(item.text)
      const grammarWords = tokens.map((token, idx) => {
        if (token.type === 'word') {
          const isSaved = vocabList?.includes(token.text.toLowerCase())
          const isSelected = selectedWord === token.text
          return (
            <ClickableWord
              key={`gw-${item.mark.id}-${idx}`}
              word={token.text}
              isSaved={isSaved}
              className={[toneClass, isSelected ? 'active' : ''].filter(Boolean).join(' ')}
              onClick={(w, e) => onWordClick?.({ word: w, mark: null, event: e })}
            />
          )
        }
        return <Text key={`gp-${idx}`}>{token.text}</Text>
      })
      resultElements.push(...grammarWords)
      lastEnd = item.end
      continue
    }

    const isActive = activeMarkId === item.mark.id || (item.mark.parentId && activeMarkId === item.mark.parentId)
    const isSaved = vocabList?.includes(item.text.toLowerCase())
    resultElements.push(
      <InlineMark
        key={item.mark.id}
        mark={item.mark}
        text={item.text}
        isActive={isActive}
        isSaved={isSaved}
        onWordClick={onWordClick}
      />
    )

    lastEnd = item.end
  }

  if (lastEnd < text.length) {
    const plainSegment = text.slice(lastEnd)
    resultElements.push(...renderPlainSegmentAsClickableWords(plainSegment, selectedWord, vocabList, onWordClick))
  }

  return <Text className='sentence-text'>{resultElements}</Text>
}

const ParagraphBlock = memo(function ParagraphBlock({
  sentences,
  translations,
  inlineMarks,
  activeMarkId,
  selectedWord,
  tailEntries,
  pageMode,
  vocabList,
  onWordClick,
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

  if (pageMode === 'immersive') {
    return (
      <View className='paragraph-block immersive'>
        <View className='english-paragraph'>
          <Text className='english-flow'>
            {sentences.map((sentence, idx) => {
              const sentenceMarks = marksBySentenceId.get(sentence.sentenceId) || []
              return (
                <Text key={sentence.sentenceId} className='sentence-span'>
                  {renderTextWithMarks(sentence.text, sentenceMarks, activeMarkId, selectedWord, vocabList, onWordClick, true)}
                  {idx < sentences.length - 1 ? <Text className='space-char'> </Text> : ''}
                </Text>
              )
            })}
          </Text>
        </View>
      </View>
    )
  }

  return (
    <View className='paragraph-block intensive'>
      {sentences.map((sentence) => {
        const sentenceMarks = marksBySentenceId.get(sentence.sentenceId) || []
        const sentenceEntries = entriesBySentenceId.get(sentence.sentenceId) || []
        const sentenceTranslation = translations.find(t => t.sentenceId === sentence.sentenceId)?.translationZh

        // 收集解析卡片
        const analysisCards: (AnalysisCardProps & { id: string })[] = [
          // 1. 词汇/短语卡片 (从 inlineMarks 中带有 glossary 的生成)
          ...sentenceMarks
            .filter(m => m.glossary && ['vocab', 'phrase', 'context'].includes(m.visualTone))
            .map(m => ({
              id: m.id,
              type: 'vocab' as const,
              title: m.lookupText || (m.anchor.kind === 'text' ? m.anchor.anchorText : m.id),
              label: m.visualTone === 'phrase' ? '核心短语' : m.visualTone === 'context' ? '语境释义' : '核心词汇',
              content: m.glossary?.zh || m.glossary?.gloss || '',
              phonetic: '',
              tags: [] as string[],
            })),
          // 2. 语法卡片 (从 sentenceEntries 筛选)
          ...sentenceEntries
            .filter(e => e.entryType === 'grammar_note')
            .map(e => ({
              id: e.id,
              type: 'grammar' as const,
              title: e.title || e.label,
              label: '语法要点',
              content: e.content,
              phonetic: undefined,
              tags: undefined,
            })),
          // 3. 句式卡片 (从 sentenceEntries 筛选)
          ...sentenceEntries
            .filter(e => e.entryType === 'sentence_analysis')
            .map(e => ({
              id: e.id,
              type: 'sentence' as const,
              title: e.label,
              label: '句式解析',
              content: e.content,
              phonetic: undefined,
              tags: undefined,
            })),
        ]

        return (
          <View key={sentence.sentenceId} className='sentence-block'>
            <View className='sentence-main'>
              <Text className='english-flow'>
                {renderTextWithMarks(sentence.text, sentenceMarks, activeMarkId, selectedWord, vocabList, onWordClick, false)}
              </Text>
            </View>

            {sentenceTranslation && (
              <View className='sentence-translation'>
                <Text className='translation-text'>{sentenceTranslation}</Text>
              </View>
            )}

            {analysisCards.length > 0 && (
              <View className='analysis-cards-list'>
                {analysisCards.map((card, idx) => (
                  <AnalysisCard
                    key={(card as any).id ?? idx}
                    type={card.type}
                    title={card.title}
                    label={card.label}
                    content={card.content}
                    phonetic={card.phonetic}
                    tags={card.tags}
                  />
                ))}
              </View>
            )}
          </View>
        )
      })}
    </View>
  )
})

export default ParagraphBlock

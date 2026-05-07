import { useMemo, memo, useState, useEffect, useCallback } from 'react'
import Taro from '@tarojs/taro'
import { View, Text } from '@tarojs/components'
import { InlineMarkModel, AnyInlineMarkModel, SentenceEntryModel, AnySentenceEntryModel, VisualTone, AcademicVisualTone, SentenceModel, TranslationModel } from '../../types/view/render-scene.vm'
import ClickableWord from '../ClickableWord'
import GrammarInlineSpan from '../GrammarInlineSpan'
import InlineMark from '../InlineMark'
import AnalysisCard, { type AnalysisCardProps } from '../AnalysisCard'
import FeedbackSheet from '../FeedbackSystem/FeedbackSheet'
import { tokenizeText, parseSentenceAnalysis, findFuzzyMatch, tokenizeSentenceWithAnalysis } from './utils'
import type { ClickEvent } from '../../types/taro-events'
import './index.scss'

const TONE_PRIORITY: Record<VisualTone | AcademicVisualTone, number> = {
  vocab: 1,
  phrase: 2,
  context: 3,
  grammar: 4,
  term: 5,
  logic: 6,
}

export interface WordClickPayload {
  word: string
  mark: AnyInlineMarkModel | null
  event?: ClickEvent
  contextSentence?: string
  occurrence?: number
}

interface ParagraphBlockProps {
  order: number
  sentences: SentenceModel[]
  translations: TranslationModel[]
  inlineMarks: AnyInlineMarkModel[]
  activeMarkId?: string | null
  activeSentenceId?: string | null
  selectedWord?: string | null
  tailEntries: AnySentenceEntryModel[]
  pageMode: 'immersive' | 'intensive'
  vocabList?: string[]
  vocabSavedMap?: Record<string, string>
  recordId?: string
  cloudId?: string
  onWordClick?: (payload: WordClickPayload) => void
  onSentenceClick?: (sentenceId: string) => void
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
  vocabSet?: Set<string>,
  onWordClick?: (payload: WordClickPayload) => void,
  vocabSavedMap?: Record<string, string>,
): React.ReactNode[] {
  if (!plainText) return []
  const tokens = tokenizeText(plainText)
  return tokens.map((token, idx) => {
    if (token.type === 'word') {
      const isSaved = vocabSet?.has(token.text.toLowerCase())
      const savedStatus = vocabSavedMap?.[token.text.toLowerCase()]
      return (
        <ClickableWord
          key={`cw-${idx}`}
          word={token.text}
          isSaved={isSaved}
          savedStatus={savedStatus}
          className={selectedWord === token.text ? 'active' : ''}
          onClick={(w, e) => onWordClick?.({ word: w, mark: null, event: e })}
        />
      )
    }
    return <Text key={`p-${idx}`}>{token.text}</Text>
  })
}

function renderTextWithAnalysis(
  text: string,
  chunks: { label: string; text: string }[],
) {
  const atoms = tokenizeSentenceWithAnalysis(text, chunks)
  const seenChunkIds = new Set<string>()

  return (
    <Text className='english-flow sentence-text is-analyzing'>
      {atoms.map((atom, idx) => {
        const colorIndex = atom.chunkId ? parseInt(atom.chunkId.split('-')[1]) % 5 : 0
        let isFirst = false
        if (atom.chunkId && !seenChunkIds.has(atom.chunkId)) {
          seenChunkIds.add(atom.chunkId)
          isFirst = true
        }
        
        return (
          <Text 
            key={idx} 
            className={`analysis-atom ${atom.chunkId ? `is-chunk color-type-${colorIndex}` : 'is-gap'}`}
          >
            {isFirst && <Text className='chunk-inline-marker'>{colorIndex + 1}</Text>}
            {atom.text}
          </Text>
        )
      })}
    </Text>
  )
}

function renderTextWithMarks(
  text: string,
  marks: AnyInlineMarkModel[],
  activeMarkId?: string | null,
  selectedWord?: string | null,
  vocabSet?: Set<string>,
  onWordClick?: (payload: WordClickPayload) => void,
  isImmersive?: boolean,
  isHighlighted?: boolean,
  vocabSavedMap?: Record<string, string>,
  isDropCap?: boolean,
) {
  // 用于追踪单词在整句中的出现次数
  const wordOccurrenceMap: Record<string, number> = {}
  let dropCapHandled = !isDropCap

  const handleDropCap = (textToProcess: string, renderCallback: (rest: string) => React.ReactNode) => {
    if (dropCapHandled) return renderCallback(textToProcess)
    
    const match = textToProcess.match(/[a-zA-Z]/)
    if (!match || match.index === undefined) return renderCallback(textToProcess)
    
    dropCapHandled = true
    const index = match.index
    const prefix = textToProcess.slice(0, index)
    const firstLetter = match[0]
    const rest = textToProcess.slice(index + 1)
    
    return (
      <Text>
        {prefix}
        <Text className='drop-cap'>{firstLetter}</Text>
        {renderCallback(rest)}
      </Text>
    )
  }

  const handleWordClick = (payload: WordClickPayload) => {
    // 在整句中计算点击词的 occurrence
    // 由于前端分词和后端 spaCy 分词可能略有差异，这里我们采取一种简单的“第几次出现”策略
    const word = payload.word.toLowerCase()
    // 我们需要重新扫描一遍 text 来确定这个 payload.word 在整个句子中的位置
    // 但更简单的方法是在渲染时就给每个 ClickableWord 分配一个 occurrence
    onWordClick?.({ ...payload, contextSentence: text })
  }

  // 改进：为了精确计算 occurrence，我们需要在渲染过程中动态计数
  const getNextOccurrence = (word: string) => {
    const w = word.toLowerCase()
    wordOccurrenceMap[w] = (wordOccurrenceMap[w] || 0) + 1
    return wordOccurrenceMap[w]
  }

  // 沉浸模式下只保留词汇相关的标记（vocab, phrase, context）
  const visibleMarks = isImmersive 
    ? marks.filter(m => ['vocab', 'phrase', 'context', 'term', 'logic'].includes(m.visualTone))
    : marks

  if (visibleMarks.length === 0) {
    return (
      <Text className='sentence-text'>
        {handleDropCap(text, (restText) => (
          <Text>
            {renderPlainSegmentAsClickableWords(restText, selectedWord, vocabSet, (p) => {
              const occ = getNextOccurrence(p.word)
              onWordClick?.({ ...p, contextSentence: text, occurrence: occ })
            }, vocabSavedMap)}
          </Text>
        ))}
      </Text>
    )
  }

  // ... 后续逻辑中也要应用 getNextOccurrence ...


  const flatParts: Array<{ mark: AnyInlineMarkModel; start: number; end: number; text: string; role?: string }> = []

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
          const partMark: AnyInlineMarkModel = {
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
          flatParts.push({ mark: partMark, start: pos, end: pos + part.anchorText.length, text: part.anchorText, role: part.role })
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
      resultElements.push(
        handleDropCap(plainSegment, (restText) => (
          <Text key={`plain-${lastEnd}`}>
            {renderPlainSegmentAsClickableWords(restText, selectedWord, vocabSet, (p) => {
              const occ = getNextOccurrence(p.word)
              onWordClick?.({ ...p, contextSentence: text, occurrence: occ })
            }, vocabSavedMap)}
          </Text>
        ))
      )
    }

    if (!item.mark.clickable) {
      const isActive = !!(activeMarkId === item.mark.id || (item.mark.parentId && activeMarkId === item.mark.parentId))
      const role = item.role

      resultElements.push(
        handleDropCap(item.text, (restText) => (
          <GrammarInlineSpan
            key={item.mark.id}
            mark={item.mark}
            text={restText}
            selectedWord={selectedWord}
            vocabSet={vocabSet}
            vocabSavedMap={vocabSavedMap}
            isActive={isActive}
            role={role}
            contextSentence={text}
            onWordClick={onWordClick}
            getNextOccurrence={getNextOccurrence}
          />
        ))
      )
      lastEnd = item.end
      continue
    }

    const isVocabulary = ['vocab', 'phrase', 'context', 'term'].includes(item.mark.visualTone)
    const isActive = !!(activeMarkId === item.mark.id || (item.mark.parentId && activeMarkId === item.mark.parentId))
    const isSaved = vocabSet?.has(item.text.toLowerCase())
    const savedStatus = vocabSavedMap?.[item.text.toLowerCase()]
    
    // 词汇类标记整体点击时，由于它们通常是一个词或短语，我们也尝试计算它的 occurrence
    // 但标记类（InlineMark）通常本身就带有 anchor 信息，这里传 occurrence 是作为双重保险
    const markOcc = getNextOccurrence(item.text)

    // 词汇类强制使用 background (marker) 渲染
    const effectiveMark = isVocabulary 
      ? { ...item.mark, renderType: 'background' as const } 
      : item.mark

    resultElements.push(
      handleDropCap(item.text, (restText) => (
        <InlineMark
          key={item.mark.id}
          mark={effectiveMark}
          text={restText}
          isActive={isActive}
          isSaved={isSaved}
          savedStatus={savedStatus}
          onWordClick={(p) => onWordClick?.({ ...p, contextSentence: text, occurrence: markOcc })}
        />
      ))
    )

    lastEnd = item.end
  }

  if (lastEnd < text.length) {
    const plainSegment = text.slice(lastEnd)
    resultElements.push(
      handleDropCap(plainSegment, (restText) => (
        <Text key={`plain-${lastEnd}`}>
          {renderPlainSegmentAsClickableWords(restText, selectedWord, vocabSet, (p) => {
            const occ = getNextOccurrence(p.word)
            onWordClick?.({ ...p, contextSentence: text, occurrence: occ })
          }, vocabSavedMap)}
        </Text>
      ))
    )
  }

  return <Text className={`sentence-text ${isHighlighted ? 'is-highlighted' : ''}`}>{resultElements}</Text>
}

const ParagraphBlock = memo(function ParagraphBlock({
  order,
  sentences,
  translations,
  inlineMarks,
  activeMarkId,
  selectedWord,
  tailEntries,
  pageMode,
  vocabList,
  vocabSavedMap,
  recordId,
  cloudId,
  activeSentenceId,
  onWordClick,
  onSentenceClick,
}: ParagraphBlockProps) {
  const vocabSet = useMemo(() => new Set(vocabList ?? []), [vocabList])
  const [activeAnalysisId, setActiveAnalysisId] = useState<string | null>(null)
  const [feedbackTarget, setFeedbackTarget] = useState<{
    targetId: string
    annotationType: string
    prefillSentiment?: 'positive' | 'negative' | 'neutral'
    contextJson: Record<string, unknown>
  } | null>(null)
  const containerClass = `paragraph-block ${pageMode} ${activeAnalysisId ? 'has-active-analysis' : ''}`

  // 监听分析卡片激活状态，自动定位锚点
  useEffect(() => {
    if (activeAnalysisId) {
      const scrollTimer = setTimeout(() => {
        const query = Taro.createSelectorQuery()
        query.select(`.sentence-text.is-analyzing`).boundingClientRect()
        query.selectViewport().scrollOffset()
        query.exec((res) => {
          if (res[0] && res[1]) {
            const top = res[0].top + res[1].scrollTop - 200
            Taro.pageScrollTo({
              scrollTop: top,
              duration: 300
            })
          }
        })
      }, 100)
      return () => clearTimeout(scrollTimer)
    }
  }, [activeAnalysisId])

  const handleAnalysisToggle = (entryId: string, expanded: boolean) => {
    setActiveAnalysisId(expanded ? entryId : null)
  }

  const handleCardFeedback = useCallback((entryId: string, entryType: string, title: string, content: string, prefillSentiment?: 'positive' | 'negative' | 'neutral') => {
    setFeedbackTarget({
      targetId: entryId,
      annotationType: entryType,
      prefillSentiment,
      contextJson: { title, content_preview: content.slice(0, 200) },
    })
  }, [])

  const marksBySentenceId = useMemo(() => {
    const map = new Map<string, AnyInlineMarkModel[]>()
    inlineMarks.forEach((m) => {
      const sid = m.anchor.sentenceId
      if (!map.has(sid)) map.set(sid, [])
      map.get(sid)!.push(m)
    })
    return map
  }, [inlineMarks])

  const entriesBySentenceId = useMemo(() => {
    const map = new Map<string, AnySentenceEntryModel[]>()
    tailEntries.forEach((e) => {
      if (!map.has(e.sentenceId)) map.set(e.sentenceId, [])
      map.get(e.sentenceId)!.push(e)
    })
    return map
  }, [tailEntries])

  if (pageMode === 'immersive') {
    return (
      <View className={containerClass}>
        <View className='english-paragraph'>
          <Text className='english-flow'>
            {sentences.map((sentence, idx) => {
              const sentenceMarks: AnyInlineMarkModel[] = marksBySentenceId.get(sentence.sentenceId) || []
              return (
                <Text 
                  key={sentence.sentenceId} 
                  className={`sentence-span ${activeSentenceId === sentence.sentenceId ? 'is-highlighted-source' : ''}`}
                  onClick={() => onSentenceClick?.(sentence.sentenceId)}
                >
                  {renderTextWithMarks(sentence.text, sentenceMarks, activeMarkId, selectedWord, vocabSet, onWordClick, true, activeSentenceId === sentence.sentenceId, vocabSavedMap, order === 1 && idx === 0)}
                  {idx < sentences.length - 1 ? <Text className='space-char'> </Text> : ''}
                </Text>
              )
            })}
          </Text>
        </View>
      </View>
    )
  }

  // --- Intensive Mode Chunking Logic ---
  const sentenceDataList = sentences.map(sentence => {
    const sentenceMarks: AnyInlineMarkModel[] = marksBySentenceId.get(sentence.sentenceId) || []
    const sentenceEntries: AnySentenceEntryModel[] = entriesBySentenceId.get(sentence.sentenceId) || []
    const sentenceTranslation = translations.find(t => t.sentenceId === sentence.sentenceId)?.translationZh

    const analysisCards: (AnalysisCardProps & { id: string })[] = [
      ...sentenceEntries
        .filter(e => e.entryType === 'grammar_note')
        .map(e => {
          const mark = sentenceMarks.find(m => m.id === e.id)
          let snippet = ''
          if (mark) {
            if (mark.anchor.kind === 'text') snippet = mark.anchor.anchorText
            else if (mark.anchor.kind === 'multi_text') snippet = mark.anchor.parts.map(p => p.anchorText).join(' ... ')
          }
          return {
            id: e.id,
            type: 'grammar' as const,
            title: e.title || e.label,
            label: '语法要点',
            content: e.content,
            snippet: snippet,
            recordId: recordId || undefined,
            cloudId: cloudId || undefined,
            entryId: e.id,
            annotationType: 'grammar_note',
            onFeedback: recordId ? (sentiment?: 'positive' | 'negative' | 'neutral') => handleCardFeedback(e.id, 'grammar_note', e.title || e.label, e.content, sentiment) : undefined,
          }
        }),
        ...sentenceEntries
          .filter(e => e.entryType === 'sentence_analysis')
          .map(e => {
            const parsed = parseSentenceAnalysis(e.content)
            return {
              id: e.id,
              type: 'sentence' as const,
              title: e.label,
              label: '句式解析',
              content: e.content,
              structuredData: parsed,
              isExpanded: activeAnalysisId === e.id,
              onToggle: (expanded: boolean) => handleAnalysisToggle(e.id, expanded),
              recordId: recordId || undefined,
              cloudId: cloudId || undefined,
              entryId: e.id,
              annotationType: 'sentence_analysis',
              onFeedback: recordId ? () => handleCardFeedback(e.id, 'sentence_analysis', e.label, e.content) : undefined,
            }
          }),
        ...sentenceEntries
          .filter(e => e.entryType === 'term_note')
          .map(e => ({
            id: e.id,
            type: 'term' as const,
            title: e.title || e.label,
            label: '术语标注',
            content: e.content,
            onFeedback: recordId ? () => handleCardFeedback(e.id, 'term_note', e.title || e.label, e.content) : undefined,
          })),
        ...sentenceEntries
          .filter(e => e.entryType === 'logic_note')
          .map(e => ({
            id: e.id,
            type: 'logic' as const,
            title: e.title || e.label,
            label: '逻辑关系',
            content: e.content,
            onFeedback: recordId ? () => handleCardFeedback(e.id, 'logic_note', e.title || e.label, e.content) : undefined,
          })),
        ...sentenceEntries
          .filter(e => e.entryType === 'interpretation_note')
          .map(e => ({
            id: e.id,
            type: 'interpretation' as const,
            title: e.title || e.label,
            label: '解释说明',
            content: e.content,
            onFeedback: recordId ? () => handleCardFeedback(e.id, 'interpretation_note', e.title || e.label, e.content) : undefined,
          })),
        ...sentenceEntries
          .filter(e => e.entryType === 'content_summary')
          .map(e => ({
            id: e.id,
            type: 'summary' as const,
            title: e.title || e.label,
            label: '内容概要',
            content: e.content,
          })),
    ]

    return { sentence, sentenceMarks, sentenceTranslation, analysisCards }
  })

  // 将没有解析卡片的连续句子合并为一个 Chunk
  const chunks: { id: string; hasCards: boolean; items: typeof sentenceDataList }[] = []
  let currentChunk: typeof chunks[0] | null = null

  sentenceDataList.forEach(item => {
    if (item.analysisCards.length > 0) {
      // 有卡片的句子必须独立成块
      chunks.push({ id: item.sentence.sentenceId, hasCards: true, items: [item] })
      currentChunk = null
    } else {
      // 没有卡片的句子合并到当前的无卡片块中
      if (!currentChunk || currentChunk.hasCards) {
        currentChunk = { id: `chunk-${item.sentence.sentenceId}`, hasCards: false, items: [] }
        chunks.push(currentChunk)
      }
      currentChunk.items.push(item)
    }
  })

  return (
    <View className={containerClass}>
      <View className='paragraph-header'>
        <Text className='paragraph-anchor'>{order < 10 ? `0${order}` : order} /</Text>
        <View className='paragraph-divider' />
      </View>
      {chunks.map((chunk, cIdx) => {
        if (chunk.hasCards) {
          const item = chunk.items[0]
          return (
            <View key={`chunk-${chunk.id}-${cIdx}`} className='sentence-block'>
              <View className='sentence-main'>
                {activeAnalysisId && item.analysisCards.some(c => c.id === activeAnalysisId && c.type === 'sentence') ? (
                  // 正在进行句式分析：使用 Ruby 标注模式
                  renderTextWithAnalysis(
                    item.sentence.text, 
                    item.analysisCards.find(c => c.id === activeAnalysisId)?.structuredData?.chunks || []
                  )
                ) : (
                  // 普通精读模式：使用马克笔涂抹模式
                  <Text className='english-flow'>
                    {renderTextWithMarks(item.sentence.text, item.sentenceMarks, activeMarkId, selectedWord, vocabSet, onWordClick, false, activeSentenceId === item.sentence.sentenceId, vocabSavedMap)}
                  </Text>
                )}
              </View>

              {item.sentenceTranslation && (
                <View 
                  className={`sentence-translation ${activeSentenceId === item.sentence.sentenceId ? 'is-highlighted' : ''}`}
                  onClick={() => onSentenceClick?.(item.sentence.sentenceId)}
                >
                  <Text className='translation-text'>{item.sentenceTranslation}</Text>
                </View>
              )}

              {item.analysisCards.length > 0 && (
                <View className='analysis-cards-list'>
                  {item.analysisCards.map((card, cardIdx) => (
                    <AnalysisCard
                      key={`${card.id}-${cardIdx}`}
                      type={card.type}
                      title={card.title}
                      label={card.label}
                      content={card.content}
                      snippet={(card as any).snippet}
                      phonetic={card.phonetic}
                      tags={card.tags}
                      badgeIndex={card.badgeIndex}
                      structuredData={card.structuredData}
                      isExpanded={card.isExpanded}
                      onToggle={card.onToggle}
                      onFeedback={card.onFeedback}
                      recordId={(card as any).recordId}
                      cloudId={(card as any).cloudId}
                      entryId={(card as any).entryId}
                      annotationType={(card as any).annotationType}
                    />
                  ))}
                </View>
              )}
            </View>
          )
        } else {
          // 合并渲染无卡片的句子
          const mergedTranslation = chunk.items
            .map(i => i.sentenceTranslation)
            .filter(Boolean)
            .join(' ')

          return (
            <View key={`m-chunk-${chunk.id}-${cIdx}`} className='sentence-block chunk-merged'>
              <View className='sentence-main'>
                <Text className='english-flow'>
                  {chunk.items.map((item, idx) => (
                    <Text 
                      key={`s-${item.sentence.sentenceId}-${idx}`} 
                      className={`sentence-span ${activeSentenceId === item.sentence.sentenceId ? 'is-highlighted-source' : ''}`}
                      onClick={() => onSentenceClick?.(item.sentence.sentenceId)}
                    >
                      {renderTextWithMarks(item.sentence.text, item.sentenceMarks, activeMarkId, selectedWord, vocabSet, onWordClick, false, activeSentenceId === item.sentence.sentenceId, vocabSavedMap)}
                      {idx < chunk.items.length - 1 ? <Text className='space-char'> </Text> : ''}
                    </Text>
                  ))}
                </Text>
              </View>

              <View className='sentence-translation merged'>
                {chunk.items.map((item, idx) => (
                  item.sentenceTranslation ? (
                    <Text 
                      key={`t-${item.sentence.sentenceId}-${idx}`}
                      className={`translation-text segment ${activeSentenceId === item.sentence.sentenceId ? 'is-highlighted' : ''}`}
                      onClick={() => onSentenceClick?.(item.sentence.sentenceId)}
                    >
                      {item.sentenceTranslation}
                      {idx < chunk.items.length - 1 ? ' ' : ''}
                    </Text>
                  ) : null
                ))}
              </View>
            </View>
          )
        }
      })}
      {feedbackTarget && recordId && (
        <View className='annotation-feedback-overlay' onClick={() => setFeedbackTarget(null)}>
          <FeedbackSheet
            scope="annotation"
            prefillSentiment={feedbackTarget.prefillSentiment}
            payload={{
              targetId: feedbackTarget.targetId,
              analysisRecordId: cloudId || recordId,
              annotationType: feedbackTarget.annotationType,
              contextJson: feedbackTarget.contextJson,
            }}
            contextSummary={(feedbackTarget.contextJson.title as string) || (feedbackTarget.contextJson.content_preview as string)}
            onClose={() => setFeedbackTarget(null)}
          />
        </View>
      )}
    </View>
  )
})

export default ParagraphBlock

import { useState, useCallback } from 'react'
import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import LucideIcon from '../LucideIcon'
import AnnotationGlyph, { type AnnotationGlyphType } from '../AnnotationGlyph'
import type { StopPropagationEvent } from '../../types/taro-events'
import { submitFeedback } from '../../services/api/feedback.client'
import { parseSentenceAnalysis, type AnalysisChunk } from '../ParagraphBlock/utils'
import './index.scss'

export type AnalysisCardType = 'vocab' | 'grammar' | 'sentence' | 'term' | 'logic' | 'interpretation' | 'summary'

export interface AnalysisCardProps {
  type: AnalysisCardType
  title: string
  label?: string
  content: string
  phonetic?: string
  tags?: string[]
  initiallyExpanded?: boolean
  badgeIndex?: number
  isExpanded?: boolean
  snippet?: string
  onToggle?: (expanded: boolean) => void
  onFeedback?: () => void
  structuredData?: { summary?: string; chunks?: AnalysisChunk[] }
  recordId?: string
  entryId?: string
  annotationType?: string
}

const TYPE_CONFIG: Record<AnalysisCardType, { icon: string; glyph?: AnnotationGlyphType; colorClass: string; defaultLabel: string }> = {
  vocab: {
    icon: 'languages',
    glyph: 'vocab',
    colorClass: 'type-vocab',
    defaultLabel: '核心词汇',
  },
  grammar: {
    icon: 'network',
    glyph: 'grammar_note',
    colorClass: 'type-grammar',
    defaultLabel: '语法',
  },
  sentence: {
    icon: 'layout-template',
    glyph: 'sentence_analysis',
    colorClass: 'type-sentence',
    defaultLabel: '句式解析',
  },
  term: {
    icon: 'flask-conical',
    colorClass: 'type-term',
    defaultLabel: '术语标注',
  },
  logic: {
    icon: 'git-branch',
    colorClass: 'type-logic',
    defaultLabel: '逻辑关系',
  },
  interpretation: {
    icon: 'message-square-text',
    colorClass: 'type-interpretation',
    defaultLabel: '解释说明',
  },
  summary: {
    icon: 'file-text',
    colorClass: 'type-summary',
    defaultLabel: '内容概要',
  },
}

function renderMarkdownContent(content: string) {
  if (!content) return null
  const parts = content.split(/(\*\*.*?\*\*)/g)
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      const text = part.slice(2, -2)
      return <Text key={idx} className='markdown-bold'>{text}</Text>
    }
    return <Text key={idx}>{part}</Text>
  })
}

export default function AnalysisCard({
  type,
  title,
  content,
  phonetic,
  tags,
  initiallyExpanded,
  isExpanded: controlledIsExpanded,
  snippet,
  onToggle,
  onFeedback,
  structuredData: externalStructuredData,
  recordId,
  entryId,
  annotationType,
}: AnalysisCardProps) {
  const [internalIsExpanded, setInternalIsExpanded] = useState(initiallyExpanded ?? false)
  const [quickFeedbackState, setQuickFeedbackState] = useState<'none' | 'positive' | 'negative'>('none')
  const isExpanded = controlledIsExpanded !== undefined ? controlledIsExpanded : internalIsExpanded
  const config = TYPE_CONFIG[type]
  const structuredData = externalStructuredData || (type === 'sentence' ? parseSentenceAnalysis(content) : null)

  const handleToggle = (e: StopPropagationEvent) => {
    e?.stopPropagation?.()
    const nextState = !isExpanded
    if (controlledIsExpanded === undefined) {
      setInternalIsExpanded(nextState)
    }
    onToggle?.(nextState)
  }

  const handleCollapse = (e: StopPropagationEvent) => {
    e?.stopPropagation?.()
    if (controlledIsExpanded === undefined) {
      setInternalIsExpanded(false)
    }
    onToggle?.(false)
  }

  const handleQuickFeedback = useCallback(async (sentiment: 'positive' | 'negative') => {
    if (!recordId || !entryId || quickFeedbackState !== 'none') return
    setQuickFeedbackState(sentiment)
    try {
      await submitFeedback({
        feedbackScope: 'annotation',
        targetId: entryId,
        analysisRecordId: recordId,
        sentiment,
        feedbackType: sentiment === 'positive' ? 'helpful' : 'inaccurate',
        annotationType: annotationType || type,
        content: undefined,
        contextJson: { title, content_preview: content.slice(0, 200) },
      })
      Taro.showToast({ title: '感谢反馈', icon: 'success', duration: 1200 })
    } catch {
      setQuickFeedbackState('none')
      Taro.showToast({ title: '提交失败', icon: 'none', duration: 1200 })
    }
  }, [recordId, entryId, quickFeedbackState, annotationType, type, title, content])

  const getCollapsedCopy = () => {
    if (type === 'sentence') return '句式解析'
    if (type === 'grammar') return title.length > 8 ? '语法' : `语法 · ${title}`
    return title || config.defaultLabel
  }

  return (
    <View className={`analysis-card ${config.colorClass} ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <View className='card-summary-row' onClick={handleToggle}>
        <View className='summary-main'>
          {config.glyph ? (
            <AnnotationGlyph type={config.glyph} size={20} state={isExpanded ? 'active' : 'default'} />
          ) : (
            <LucideIcon name={config.icon} size={16} color='var(--text-muted)' />
          )}
          <Text className='card-collapsed-title' numberOfLines={1}>{getCollapsedCopy()}</Text>
        </View>
        <View className={`summary-icon ${isExpanded ? 'is-expanded' : ''}`}>
          <LucideIcon name='chevronDown' size={14} color='var(--text-muted)' />
        </View>
      </View>

      <View className={`card-content-expandable ${isExpanded ? 'show' : 'hide'}`}>
        <View className='card-body' onClick={(e) => e.stopPropagation()}>
          {(type === 'grammar' || type === 'sentence') && (
            <View className='expanded-title-row'>
              <Text className='expanded-full-title'>{title && title !== config.defaultLabel ? title : config.defaultLabel}</Text>
              <View className='collapse-btn' onClick={handleCollapse}>
                <LucideIcon name='x' size={17} color='var(--text-main)' strokeWidth={1.8} />
              </View>
            </View>
          )}

          {(phonetic || (tags && tags.length > 0)) && (
            <View className='card-meta-row'>
              {phonetic && <Text className='card-phonetic'>/{phonetic}/</Text>}
              {tags && tags.length > 0 && (
                <View className='card-tags'>
                  {tags.map((tag) => (
                    <View key={tag} className='tag-badge'>{tag}</View>
                  ))}
                </View>
              )}
            </View>
          )}

          <View className='card-content-wrapper'>
            {type === 'grammar' && snippet && (
              <View className='grammar-snippet-box'>
                <Text className='snippet-label'>原文片段</Text>
                <Text className='snippet-text'>{snippet}</Text>
              </View>
            )}

            {type === 'sentence' ? (
              <View className='sentence-analysis-details'>
                {structuredData?.summary && (
                  <Text className='analysis-summary'>{structuredData.summary}</Text>
                )}
                {structuredData?.chunks && structuredData.chunks.length > 0 && (
                  <View className='analysis-chunks-list'>
                    {structuredData.chunks.map((chunk: AnalysisChunk, idx: number) => (
                      <View key={idx} className={`chunk-detail-item color-idx-${idx % 5}`}>
                        <View className='chunk-detail-label'>
                          <Text className='label-index'>{idx + 1}</Text>
                          <Text className='label-text'>{chunk.label}</Text>
                        </View>
                        <Text className='chunk-detail-text' numberOfLines={2}>{chunk.text}</Text>
                      </View>
                    ))}
                  </View>
                )}
              </View>
            ) : (
              <Text className='card-content'>{renderMarkdownContent(content)}</Text>
            )}
          </View>

          {(onFeedback || recordId) && (
            <View className='card-feedback-row'>
              {recordId && entryId && (
                <>
                  <View
                    className={`feedback-quick-btn ${quickFeedbackState === 'positive' ? 'is-submitted' : ''} ${quickFeedbackState !== 'none' && quickFeedbackState !== 'positive' ? 'is-disabled' : ''}`}
                    onClick={(e) => { e.stopPropagation(); void handleQuickFeedback('positive') }}
                  >
                    <LucideIcon name='thumbsUp' size={13} color='var(--text-muted)' strokeWidth={1.8} />
                    <Text className='feedback-quick-text'>{quickFeedbackState === 'positive' ? '已反馈' : '有帮助'}</Text>
                  </View>
                  <View
                    className={`feedback-quick-btn ${quickFeedbackState === 'negative' ? 'is-submitted' : ''} ${quickFeedbackState !== 'none' && quickFeedbackState !== 'negative' ? 'is-disabled' : ''}`}
                    onClick={(e) => { e.stopPropagation(); void handleQuickFeedback('negative') }}
                  >
                    <LucideIcon name='thumbsDown' size={13} color='var(--text-muted)' strokeWidth={1.8} />
                    <Text className='feedback-quick-text'>{quickFeedbackState === 'negative' ? '已反馈' : '不准确'}</Text>
                  </View>
                </>
              )}
              {onFeedback && (
                <View className='feedback-detail-btn' onClick={(e) => { e.stopPropagation(); onFeedback() }}>
                  <LucideIcon name='messageSquare' size={13} color='var(--text-muted)' strokeWidth={1.8} />
                  <Text className='feedback-detail-text'>反馈</Text>
                </View>
              )}
            </View>
          )}
        </View>
      </View>
    </View>
  )
}

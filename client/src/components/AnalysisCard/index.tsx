import { useState, useEffect } from 'react'
import { View, Text } from '@tarojs/components'
import LucideIcon from '../LucideIcon'
import AnnotationGlyph, { type AnnotationGlyphType } from '../AnnotationGlyph'
import type { StopPropagationEvent } from '../../types/taro-events'
import { useConfigStore } from '../../stores/config'
import './index.scss'

export type AnalysisCardType = 'vocab' | 'grammar' | 'sentence' | 'term' | 'logic' | 'interpretation' | 'summary'

import { parseSentenceAnalysis, type AnalysisChunk } from '../ParagraphBlock/utils'

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
  onToggle?: (expanded: boolean) => void
  onFeedback?: () => void
  structuredData?: { summary?: string; chunks?: AnalysisChunk[] }
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
  label,
  content,
  phonetic,
  tags,
  initiallyExpanded,
  badgeIndex,
  isExpanded: controlledIsExpanded,
  onToggle,
  onFeedback,
  structuredData: externalStructuredData,
}: AnalysisCardProps) {
  const globalDefaultExpanded = useConfigStore((s) => s.defaultCardExpanded)
  const [internalIsExpanded, setInternalIsExpanded] = useState(initiallyExpanded ?? globalDefaultExpanded)
  const isExpanded = controlledIsExpanded !== undefined ? controlledIsExpanded : internalIsExpanded

  useEffect(() => {
    if (initiallyExpanded === undefined) {
      setInternalIsExpanded(globalDefaultExpanded)
    }
  }, [globalDefaultExpanded, initiallyExpanded])

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

  // Micro Rules for collapsed tab text
  const getCollapsedCopy = () => {
    if (type === 'sentence') return '句式解析'
    if (type === 'grammar') {
      return title.length > 8 ? '语法' : `语法 · ${title}`
    }
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
        <View className='summary-icon'>
          <LucideIcon 
            name={isExpanded ? 'chevron-up' : 'chevron-down'} 
            size={14} 
            color='var(--text-muted)' 
          />
        </View>
      </View>

      <View className={`card-content-expandable ${isExpanded ? 'show' : 'hide'}`}>
        <View className='card-body' onClick={(e) => e.stopPropagation()}>
          {/* Expanded Full Title */}
          {(type === 'grammar' || type === 'sentence') && (
             <View className='expanded-title-row'>
               <Text className='expanded-full-title'>{title}</Text>
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
            {type === 'sentence' ? (
              <View className='sentence-analysis-details'>
                {structuredData?.summary && (
                  <Text className='analysis-summary'>{structuredData.summary}</Text>
                )}
                {structuredData?.chunks && structuredData.chunks.length > 0 && (
                  <View className='analysis-chunks-list'>
                    {structuredData.chunks.map((chunk: AnalysisChunk, idx: number) => {
                      return (
                        <View key={idx} className='chunk-detail-item'>
                          <View className='chunk-detail-label'>
                            <Text className='label-index'>{idx + 1}</Text>
                            <Text className='label-text'>{chunk.label}</Text>
                          </View>
                          <Text className='chunk-detail-text'>{chunk.text}</Text>
                        </View>
                      )
                    })}
                  </View>
                )}
              </View>
            ) : (
              <Text className='card-content'>{renderMarkdownContent(content)}</Text>
            )}
          </View>
          
          {onFeedback && (
            <View className='card-footer'>
              <View className='card-feedback-btn' onClick={(e) => { e.stopPropagation(); onFeedback() }}>
                <LucideIcon name='messageSquare' size={14} color='var(--reader-muted)' />
              </View>
            </View>
          )}
        </View>
      </View>
    </View>
  )
}

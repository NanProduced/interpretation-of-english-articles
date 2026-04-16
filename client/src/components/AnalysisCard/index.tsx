import { useState, useEffect } from 'react'
import { View, Text } from '@tarojs/components'
import LucideIcon from '../LucideIcon'
import { useConfigStore } from '../../stores/config'
import './index.scss'

export type AnalysisCardType = 'vocab' | 'grammar' | 'sentence'

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
  structuredData?: any
  sentenceId?: string
  sentenceText?: string
  annotationId?: string
  onFeedback?: () => void
}

const TYPE_CONFIG = {
  vocab: {
    icon: 'languages',
    colorClass: 'type-vocab',
    accentColor: 'var(--vocab-accent)',
    defaultLabel: '核心词汇',
  },
  grammar: {
    icon: 'network',
    colorClass: 'type-grammar',
    accentColor: 'var(--grammar-accent)',
    defaultLabel: '语法要点',
  },
  sentence: {
    icon: 'layout-template',
    colorClass: 'type-sentence',
    accentColor: 'var(--sentence-accent)',
    defaultLabel: '句式解析',
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
  structuredData: externalStructuredData,
  sentenceId,
  sentenceText,
  annotationId,
  onFeedback,
}: AnalysisCardProps) {
  const globalDefaultExpanded = useConfigStore((s) => s.defaultCardExpanded)
  const [internalIsExpanded, setInternalIsExpanded] = useState(initiallyExpanded ?? globalDefaultExpanded)
  const isExpanded = controlledIsExpanded !== undefined ? controlledIsExpanded : internalIsExpanded

  // 同步全局配置
  useEffect(() => {
    if (initiallyExpanded === undefined) {
      setInternalIsExpanded(globalDefaultExpanded)
    }
  }, [globalDefaultExpanded, initiallyExpanded])

  const config = TYPE_CONFIG[type]

  // 如果是句式解析，进行结构化解析（优先使用外部传入的数据）
  const structuredData = externalStructuredData || (type === 'sentence' ? parseSentenceAnalysis(content) : null)

  const handleToggle = (e: any) => {
    e?.stopPropagation?.()
    const nextState = !isExpanded
    if (controlledIsExpanded === undefined) {
      setInternalIsExpanded(nextState)
    }
    onToggle?.(nextState)
  }

  return (
    <View className={`analysis-card ${config.colorClass} ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <View className='card-summary-row' onClick={handleToggle}>
        <View className='summary-main'>
          <LucideIcon name={config.icon} size={16} color={config.accentColor} />
          {/* 语法点和句式解析现在都在头部显示具体标题 */}
          {type === 'grammar' || type === 'sentence' ? (
            <Text className='card-title-header' numberOfLines={1}>{title}</Text>
          ) : (
            <Text className='card-category-label'>{label || config.defaultLabel}</Text>
          )}
        </View>
        <View className='summary-icon'>
          <LucideIcon 
            name={isExpanded ? 'chevron-up' : 'chevron-down'} 
            size={16} 
            color='var(--text-muted)' 
          />
        </View>
      </View>

      <View className={`card-content-expandable ${isExpanded ? 'show' : 'hide'}`}>
        <View className='card-body' onClick={(e) => e.stopPropagation()}>
          {/* 这里是如 Figma 稿中的紫色标签区域 */}
          {/* 如果是语法类型或句式解析，标题已在头部展示，此处仅保留序号（如果有） */}
          {(badgeIndex !== undefined || (type !== 'grammar' && type !== 'sentence')) && (
            <View className='card-title-badges'>
              {badgeIndex !== undefined && (
                <View className='badge-index-circle'>{badgeIndex}</View>
              )}
              {type !== 'grammar' && type !== 'sentence' && (
                <View className='title-tag-badge'>{title}</View>
              )}
            </View>
          )}
          {/* Phonetic and tags moved inside the expandable body if they exist */}
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
                      const colorIndex = idx % 5;
                      return (
                        <View key={idx} className={`chunk-detail-item color-type-${colorIndex}`}>
                          <View className='chunk-detail-label'>
                            <View className='label-dot' />
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
          
          {/* 语法要点标识和反馈按钮 */}
          <View className='card-footer'>
            <View className={`type-indicator-badge type-${type}`}>
              <Text className='indicator-text'>{label || config.defaultLabel}</Text>
            </View>
            {/* 语法标注和句式解析显示反馈按钮 */}
            {(type === 'grammar' || type === 'sentence') && onFeedback && (
              <View 
                className='feedback-btn-small'
                onClick={(e) => {
                  e?.stopPropagation?.()
                  onFeedback()
                }}
              >
                <LucideIcon name='messageSquare' size={14} color='var(--text-muted)' />
                <Text className='feedback-btn-text'>反馈</Text>
              </View>
            )}
          </View>
        </View>
      </View>
    </View>
  )
}

import { useState, useEffect } from 'react'
import { View, Text } from '@tarojs/components'
import LucideIcon from '../LucideIcon'
import { useConfigStore } from '../../stores/config'
import './index.scss'

export type AcademicNoteType = 'term' | 'logic' | 'interpretation'

export interface AcademicNoteCardProps {
  type: AcademicNoteType
  label: string
  title: string
  content: string
  category?: string
  definition?: string
  contextHint?: string
  relation?: string
  literalTranslation?: string
  whyNotLiteral?: string
  rhetoricalPurpose?: string
  initiallyExpanded?: boolean
  isExpanded?: boolean
  onToggle?: (expanded: boolean) => void
}

const TYPE_CONFIG = {
  term: {
    icon: 'book-open',
    colorClass: 'type-term',
    accentColor: 'var(--term-accent)',
    defaultLabel: '术语理解',
  },
  logic: {
    icon: 'git-branch',
    colorClass: 'type-logic',
    accentColor: 'var(--logic-accent)',
    defaultLabel: '逻辑关系',
  },
  interpretation: {
    icon: 'lightbulb',
    colorClass: 'type-interpretation',
    accentColor: 'var(--interpretation-accent)',
    defaultLabel: '解释性理解',
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

export default function AcademicNoteCard({
  type,
  label,
  title,
  content,
  category,
  definition,
  contextHint,
  relation,
  literalTranslation,
  whyNotLiteral,
  rhetoricalPurpose,
  initiallyExpanded,
  isExpanded: controlledIsExpanded,
  onToggle,
}: AcademicNoteCardProps) {
  const globalDefaultExpanded = useConfigStore((s) => s.defaultCardExpanded)
  const [internalIsExpanded, setInternalIsExpanded] = useState(initiallyExpanded ?? globalDefaultExpanded)
  const isExpanded = controlledIsExpanded !== undefined ? controlledIsExpanded : internalIsExpanded

  useEffect(() => {
    if (initiallyExpanded === undefined) {
      setInternalIsExpanded(globalDefaultExpanded)
    }
  }, [globalDefaultExpanded, initiallyExpanded])

  const config = TYPE_CONFIG[type]

  const handleToggle = (e: any) => {
    e?.stopPropagation?.()
    const nextState = !isExpanded
    if (controlledIsExpanded === undefined) {
      setInternalIsExpanded(nextState)
    }
    onToggle?.(nextState)
  }

  return (
    <View className={`academic-note-card ${config.colorClass} ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <View className='card-summary-row' onClick={handleToggle}>
        <View className='summary-main'>
          <LucideIcon name={config.icon} size={16} color={config.accentColor} />
          <Text className='card-title-header' numberOfLines={1}>{title}</Text>
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
          <View className='card-title-badges'>
            <View className='title-tag-badge'>{label || config.defaultLabel}</View>
            {category && (
              <View className='category-badge'>{category}</View>
            )}
            {relation && (
              <View className='relation-badge'>{relation}</View>
            )}
          </View>

          <View className='card-content-wrapper'>
            {type === 'term' && (
              <View className='term-content'>
                {definition && (
                  <View className='definition-section'>
                    <Text className='section-label'>定义</Text>
                    <Text className='section-content'>{definition}</Text>
                  </View>
                )}
                {contextHint && (
                  <View className='context-section'>
                    <Text className='section-label'>语境提示</Text>
                    <Text className='section-content'>{contextHint}</Text>
                  </View>
                )}
                {content && (
                  <View className='main-content'>
                    <Text className='card-content'>{renderMarkdownContent(content)}</Text>
                  </View>
                )}
              </View>
            )}

            {type === 'logic' && (
              <View className='logic-content'>
                {content && (
                  <View className='main-content'>
                    <Text className='card-content'>{renderMarkdownContent(content)}</Text>
                  </View>
                )}
              </View>
            )}

            {type === 'interpretation' && (
              <View className='interpretation-content'>
                {literalTranslation && (
                  <View className='literal-section'>
                    <Text className='section-label'>字面翻译</Text>
                    <Text className='section-content literal'>{literalTranslation}</Text>
                  </View>
                )}
                {content && (
                  <View className='main-content'>
                    <Text className='section-label'>真实含义</Text>
                    <Text className='section-content intended'>{renderMarkdownContent(content)}</Text>
                  </View>
                )}
                {whyNotLiteral && (
                  <View className='why-section'>
                    <Text className='section-label'>为什么不能只按字面理解</Text>
                    <Text className='section-content'>{whyNotLiteral}</Text>
                  </View>
                )}
                {rhetoricalPurpose && (
                  <View className='purpose-section'>
                    <Text className='section-label'>修辞目的</Text>
                    <Text className='section-content'>{rhetoricalPurpose}</Text>
                  </View>
                )}
              </View>
            )}
          </View>
          
          <View className='card-footer'>
            <View className={`type-indicator-badge type-${type}`}>
              <Text className='indicator-text'>{label || config.defaultLabel}</Text>
            </View>
          </View>
        </View>
      </View>
    </View>
  )
}

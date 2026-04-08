import { useState, useEffect } from 'react'
import { View, Text } from '@tarojs/components'
import LucideIcon from '../LucideIcon'
import { useConfigStore } from '../../stores/config'
import './index.scss'

export type AnalysisCardType = 'vocab' | 'grammar' | 'sentence'

export interface AnalysisCardProps {
  type: AnalysisCardType
  title: string
  label?: string
  content: string
  phonetic?: string
  tags?: string[]
  initiallyExpanded?: boolean
}

const TYPE_CONFIG = {
  vocab: {
    icon: 'languages',
    colorClass: 'type-vocab',
    defaultLabel: '核心词汇',
  },
  grammar: {
    icon: 'network',
    colorClass: 'type-grammar',
    defaultLabel: '语法要点',
  },
  sentence: {
    icon: 'layout-template',
    colorClass: 'type-sentence',
    defaultLabel: '句式解析',
  },
}

export default function AnalysisCard({
  type,
  title,
  label,
  content,
  phonetic,
  tags,
  initiallyExpanded,
}: AnalysisCardProps) {
  const globalDefaultExpanded = useConfigStore((s) => s.defaultCardExpanded)
  const [isExpanded, setIsExpanded] = useState(initiallyExpanded ?? globalDefaultExpanded)

  // 同步全局配置（可选，看需求，这里暂时只在初始化时设置）
  useEffect(() => {
    if (initiallyExpanded === undefined) {
      setIsExpanded(globalDefaultExpanded)
    }
  }, [globalDefaultExpanded, initiallyExpanded])

  const config = TYPE_CONFIG[type]

  return (
    <View className={`analysis-card ${config.colorClass} ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <View className='card-header' onClick={() => setIsExpanded(!isExpanded)}>
        <View className='header-left'>
          <View className='icon-wrapper'>
            <LucideIcon name={config.icon} size={14} color='currentColor' />
          </View>
          <Text className='card-label'>{label || config.defaultLabel}</Text>
        </View>
        <View className='header-right'>
          <LucideIcon 
            name={isExpanded ? 'chevron-up' : 'chevron-down'} 
            size={16} 
            color='var(--text-sub)' 
          />
        </View>
      </View>

      <View className='card-body'>
        <View className='card-title-row'>
          <Text className='card-title'>{title}</Text>
          {phonetic && <Text className='card-phonetic'>/{phonetic}/</Text>}
          {tags && tags.length > 0 && (
            <View className='card-tags'>
              {tags.map((tag) => (
                <View key={tag} className='tag-badge'>{tag}</View>
              ))}
            </View>
          )}
        </View>
        
        {isExpanded && (
          <View className='card-content-wrapper'>
            <Text className='card-content'>{content}</Text>
          </View>
        )}
      </View>
    </View>
  )
}

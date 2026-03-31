import { useState } from 'react'
import { View, Text } from '@tarojs/components'
import { AnalysisCardModel } from '../../types/v2-render'
import { parseMarkdown } from '../../utils/parseMarkdown'
import LucideIcon from '../LucideIcon'
import './index.scss'

interface AnalysisCardProps {
  card: AnalysisCardModel
  onToggle?: (card: AnalysisCardModel) => void
}

/**
 * 渲染 Markdown 内容片段
 */
function renderMarkdownSegment(segment: ReturnType<typeof parseMarkdown>[number], index: number) {
  const { text, bold, italic, code, list } = segment

  const style: Record<string, string> = {}
  if (bold) style.fontWeight = 'bold'
  if (italic) style.fontStyle = 'italic'
  if (code) {
    style.backgroundColor = '#f3f4f6'
    style.padding = '2rpx 8rpx'
    style.borderRadius = '4rpx'
  }

  return (
    <Text
      key={index}
      style={Object.keys(style).length > 0 ? style : undefined}
    >
      {text}{list ? '\n' : ''}
    </Text>
  )
}

export default function AnalysisCard({ card, onToggle }: AnalysisCardProps) {
  const [expanded, setExpanded] = useState(card.expanded || false)

  const handleToggle = () => {
    const newExpanded = !expanded
    setExpanded(newExpanded)
    if (onToggle) {
      onToggle({ ...card, expanded: newExpanded })
    }
  }

  const contentSegments = card.content ? parseMarkdown(card.content) : []

  return (
    <View className={`analysis-card ${expanded ? 'expanded' : ''}`}>
      <View className='card-header' onClick={handleToggle}>
        <View className='header-left'>
          <LucideIcon name='sparkles' size={16} color='#8b5cf6' />
          <Text className='card-title'>{card.title}</Text>
        </View>
        <View className='toggle-icon'>
          <LucideIcon
            name={expanded ? 'chevron-up' : 'chevron-down'}
            size={18}
            color='#999'
          />
        </View>
      </View>

      {expanded && (
        <View className='card-content'>
          <Text className='content-text'>
            {contentSegments.map(renderMarkdownSegment)}
          </Text>
        </View>
      )}
    </View>
  )
}

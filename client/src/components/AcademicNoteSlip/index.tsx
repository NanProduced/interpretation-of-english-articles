import { useState } from 'react'
import { View, Text } from '@tarojs/components'
import LucideIcon from '../LucideIcon'
import type { AcademicSentenceEntryType } from '../../types/view/render-scene.vm'
import './index.scss'

type AcademicNoteSlipVariant = 'term' | 'logic' | 'interpretation'

interface AcademicNoteSlipProps {
  variant: AcademicNoteSlipVariant
  title: string
  content: string
  label?: string
  initiallyExpanded?: boolean
  onToggle?: (expanded: boolean) => void
  onFeedback?: () => void
}

const VARIANT_CONFIG: Record<AcademicNoteSlipVariant, {
  icon: string
  defaultLabel: string
  colorClass: string
}> = {
  term: {
    icon: 'flask-conical',
    defaultLabel: '术语',
    colorClass: 'variant-term',
  },
  logic: {
    icon: 'git-branch',
    defaultLabel: '论证',
    colorClass: 'variant-logic',
  },
  interpretation: {
    icon: 'message-square-text',
    defaultLabel: '解释',
    colorClass: 'variant-interpretation',
  },
}

export default function AcademicNoteSlip({
  variant,
  title,
  content,
  label,
  initiallyExpanded = false,
  onToggle,
  onFeedback,
}: AcademicNoteSlipProps) {
  const [isExpanded, setIsExpanded] = useState(initiallyExpanded)
  const config = VARIANT_CONFIG[variant]
  const displayLabel = label || config.defaultLabel

  const handleToggle = () => {
    const next = !isExpanded
    setIsExpanded(next)
    onToggle?.(next)
  }

  return (
    <View className={`academic-note-slip ${config.colorClass} ${isExpanded ? 'expanded' : 'collapsed'}`}>
      {/* Colorize: 类型化视觉标识 */}
      {/* Collapsed Entry - Click to expand */}
      <View className='note-slip-header' onClick={handleToggle}>
        <View className='header-main'>
          <View className='semantic-label'>
            <Text className='label-text'>{displayLabel}</Text>
          </View>
          <Text className='header-title' numberOfLines={1}>{title}</Text>
        </View>
        <View className={`expand-icon ${isExpanded ? 'is-expanded' : ''}`}>
          <LucideIcon name='chevronRight' size={14} color='var(--reader-muted)' />
        </View>
      </View>

      {/* Expanded Content */}
      <View className={`note-slip-body ${isExpanded ? 'show' : 'hide'}`}>
        <View className='body-content'>
          <Text className='content-text'>{content}</Text>
        </View>

        {/* Footer - 反馈已移至页面底部全局入口，保持卡片简洁 */}
      </View>
    </View>
  )
}

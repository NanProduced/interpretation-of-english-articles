import { View, Text } from '@tarojs/components'
import { getSafeDisplayLabel } from '../../config/purpose'
import LucideIcon from '../LucideIcon'
import './index.scss'

interface ReaderContextBarProps {
  sourceType?: string
  readingGoal?: string
  readingVariant?: string
  pageMode?: string
  isAcademicMode?: boolean
  onClick?: () => void
  onEdit?: () => void
  onModeToggle?: () => void
}

export default function ReaderContextBar({
  sourceType,
  readingGoal,
  readingVariant,
  pageMode,
  isAcademicMode,
  onClick,
  onEdit,
  onModeToggle,
}: ReaderContextBarProps) {
  const sourceLabel = sourceType === 'user_input' ? '手动输入' : '每日文章'
  const goalLabel = getSafeDisplayLabel(readingGoal || 'daily_reading', readingVariant)
  const modeLabel = pageMode === 'immersive' ? '原文' : '精读'

  return (
    <View className='reader-context-bar' onClick={onClick}>
      <View className='reader-context-items'>
        <Text className='context-item source'>{sourceLabel}</Text>
        <Text className='context-divider'>·</Text>
        <Text className='context-item goal' numberOfLines={1}>{goalLabel}</Text>
        <Text className='context-divider'>·</Text>
        <View
          className={`context-item mode ${pageMode || ''}`}
          onClick={(e) => {
            e.stopPropagation()
            onModeToggle?.()
          }}
        >
          <Text>{modeLabel}</Text>
        </View>
        {isAcademicMode && (
          <>
            <Text className='context-divider'>·</Text>
            <Text className='context-item academic'>学术模式</Text>
          </>
        )}
      </View>
      <View
        className='context-edit-icon'
        onClick={(e) => {
          e.stopPropagation()
          onEdit?.()
        }}
      >
        <LucideIcon name='pencil' size={13} color='var(--text-muted)' strokeWidth={1.8} />
      </View>
    </View>
  )
}

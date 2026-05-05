import { View, Text } from '@tarojs/components'
import { getSafeDisplayLabel } from '../../config/purpose'
import './index.scss'

interface ReaderContextBarProps {
  sourceType?: string
  readingGoal?: string
  readingVariant?: string
  pageMode?: string
  isAcademicMode?: boolean
}

export default function ReaderContextBar({
  sourceType,
  readingGoal,
  readingVariant,
  pageMode,
  isAcademicMode,
}: ReaderContextBarProps) {
  const sourceLabel = sourceType === 'user_input' ? '手动输入' : '每日文章'
  const goalLabel = getSafeDisplayLabel(readingGoal, readingVariant)
  const modeLabel = pageMode === 'immersive' ? '沉浸阅读' : '深度解析'

  return (
    <View className='reader-context-bar'>
      <View className='reader-context-items'>
        <Text className='context-item source'>{sourceLabel}</Text>
        <Text className='context-divider'>·</Text>
        <Text className='context-item goal'>{goalLabel}</Text>
        <Text className='context-divider'>·</Text>
        <Text className='context-item mode'>{modeLabel}</Text>
        {isAcademicMode && (
          <>
            <Text className='context-divider'>·</Text>
            <Text className='context-item academic'>学术模式</Text>
          </>
        )}
      </View>
    </View>
  )
}

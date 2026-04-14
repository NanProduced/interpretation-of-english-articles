import { View, Text } from '@tarojs/components'
import { ReadingGoal } from '../../config/purpose'
import LucideIcon from '../LucideIcon'
import ConfigEditor from '../ConfigEditor'
import './index.scss'

interface BottomSheetSelectProps {
  visible: boolean
  currentGoal: ReadingGoal
  currentLevel: string | null
  onClose: () => void
  onSelect: (goal: ReadingGoal, level: string | null) => void
}

export default function BottomSheetSelect({
  visible,
  currentGoal,
  currentLevel,
  onClose,
  onSelect,
}: BottomSheetSelectProps) {
  if (!visible) return null

  return (
    <View className='bs-select-overlay' onClick={onClose}>
      <View className='bs-select-container' onClick={(e) => e.stopPropagation()}>
        {/* 拖动条 */}
        <View className='bs-drag-handle' />

        {/* Header */}
        <View className='bs-header'>
          <Text className='bs-title'>选择分析模式</Text>
          <View className='bs-close-btn' onClick={onClose}>
            <LucideIcon name='x' size={20} color='var(--text-muted)' />
          </View>
        </View>

        {/* 列表内容 */}
        <View className='bs-content'>
          <ConfigEditor 
            mode='compact'
            initialGoal={currentGoal}
            initialLevel={currentLevel}
            onComplete={(g, l) => {
              onSelect(g, l)
              onClose()
            }}
          />
        </View>
        
        <View className='bs-safe-bottom' />
      </View>
    </View>
  )
}

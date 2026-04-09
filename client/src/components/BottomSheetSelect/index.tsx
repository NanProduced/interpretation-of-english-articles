import { useState, useEffect } from 'react'
import { View, Text } from '@tarojs/components'
import { ReadingGoal, READING_CONFIG_MAP } from '../../config/purpose'
import LucideIcon from '../LucideIcon'
import './index.scss'

interface BottomSheetSelectProps {
  visible: boolean
  currentGoal: ReadingGoal
  currentLevel: string | null
  onClose: () => void
  onSelect: (goal: ReadingGoal, level: string | null) => void
}

/**
 * 阶段状态：
 * 'goals' - 显示主选项列表（日常阅读/考试备考/学术文献）
 * 'variants' - 显示某个主选项的变体列表（如 CET-4/CET-6/Gaokao）
 */
type Stage = 'goals' | 'variants'

export default function BottomSheetSelect({
  visible,
  currentGoal,
  currentLevel,
  onClose,
  onSelect,
}: BottomSheetSelectProps) {
  const [stage, setStage] = useState<Stage>('goals')
  const [selectedGoal, setSelectedGoal] = useState<ReadingGoal | null>(null)

  // 重置状态当 sheet 打开
  useEffect(() => {
    if (visible) {
      setStage('goals')
      setSelectedGoal(null)
    }
  }, [visible])

  if (!visible) return null

  const goals = Object.keys(READING_CONFIG_MAP) as ReadingGoal[]

  const handleGoalClick = (goal: ReadingGoal) => {
    const config = READING_CONFIG_MAP[goal]
    if (config.variants) {
      setSelectedGoal(goal)
      setStage('variants')
    } else {
      onSelect(goal, config.defaultVariant)
      onClose()
    }
  }

  const handleVariantClick = (variantValue: string) => {
    if (selectedGoal) {
      onSelect(selectedGoal, variantValue)
      onClose()
    }
  }

  const handleBack = () => {
    setStage('goals')
    setSelectedGoal(null)
  }

  const currentConfig = selectedGoal ? READING_CONFIG_MAP[selectedGoal] : null

  return (
    <View className='bs-select-overlay' onClick={onClose}>
      <View className='bs-select-container' onClick={(e) => e.stopPropagation()}>
        {/* 拖动条 */}
        <View className='bs-drag-handle' />

        {/* Header */}
        <View className='bs-header'>
          {stage === 'variants' ? (
            <View className='bs-back-btn' onClick={handleBack}>
              <LucideIcon name='chevronLeft' size={20} color='var(--text-sub)' />
            </View>
          ) : (
            <View style={{ width: '40rpx' }} />
          )}
          <Text className='bs-title'>
            {stage === 'goals' ? '选择分析模式' : currentConfig?.label}
          </Text>
          <View className='bs-close-btn' onClick={onClose}>
            <LucideIcon name='x' size={20} color='var(--text-muted)' />
          </View>
        </View>

        {/* 列表内容 */}
        <View className='bs-list'>
          {stage === 'goals' &&
            goals.map((goal) => {
              const config = READING_CONFIG_MAP[goal]
              const isSelected = goal === currentGoal
              return (
                <View
                  key={goal}
                  className={`bs-option ${isSelected ? 'selected' : ''}`}
                  onClick={() => handleGoalClick(goal)}
                >
                  <View className='bs-option-left'>
                    <Text className='bs-option-label'>{config.label}</Text>
                    {config.description && (
                      <Text className='bs-option-desc'>{config.description}</Text>
                    )}
                  </View>
                  <View className='bs-option-right'>
                    {isSelected && (
                      <LucideIcon name='check' size={18} color='var(--color-ink)' />
                    )}
                    {config.variants && (
                      <LucideIcon name='chevronRight' size={16} color='var(--text-muted)' />
                    )}
                  </View>
                </View>
              )
            })}

          {stage === 'variants' &&
            currentConfig?.variants?.map((variant) => {
              const isSelected = variant.value === currentLevel
              return (
                <View
                  key={variant.value}
                  className={`bs-option ${isSelected ? 'selected' : ''}`}
                  onClick={() => handleVariantClick(variant.value)}
                >
                  <Text className='bs-option-label'>{variant.label}</Text>
                  {isSelected && (
                    <LucideIcon name='check' size={18} color='var(--color-ink)' />
                  )}
                </View>
              )
            })}
        </View>
      </View>
    </View>
  )
}

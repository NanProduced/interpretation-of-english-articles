import { View, Text } from '@tarojs/components'
import { SentenceEntryModel } from '../../types/view/render-scene.vm'
import LucideIcon from '../LucideIcon'
import './index.scss'

interface SentenceActionChipProps {
  entry: SentenceEntryModel
  onClick?: (entry: SentenceEntryModel) => void
}

const TYPE_CONFIG = {
  grammar_note: { 
    icon: 'book', 
    color: 'var(--color-grammar)',
    label: '语法点'
  }, 
  sentence_analysis: { 
    icon: 'sparkles', 
    color: 'var(--color-info)',
    label: '句子分析'
  },
}

export default function SentenceActionChip({ entry, onClick }: SentenceActionChipProps) {
  const config = TYPE_CONFIG[entry.entryType]

  const handleClick = (e: any) => {
    e.stopPropagation()
    if (onClick) {
      onClick(entry)
    }
  }

  return (
    <View
      className={`sentence-action-chip ${entry.entryType}`}
      onClick={handleClick}
      role='button'
      aria-label={`展开解读: ${entry.label}`}
    >
      <LucideIcon name={config.icon} size={12} color={config.color} />
      <Text className='chip-label' style={{ color: config.color }}>
        {config.label}
      </Text>
    </View>
  )
}

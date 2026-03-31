import { View, Text } from '@tarojs/components'
import { SentenceTailEntryModel } from '../../types/v2-render'
import LucideIcon from '../LucideIcon'
import './index.scss'

interface SentenceActionChipProps {
  entry: SentenceTailEntryModel
  onClick?: (entry: SentenceTailEntryModel) => void
}

const TYPE_CONFIG = {
  grammar: { icon: 'book', color: '#22c55e', label: '语法' },
  sentence_analysis: { icon: 'sparkles', color: '#8b5cf6', label: '句解' },
  context: { icon: 'layers', color: '#4285f4', label: '语境' },
}

export default function SentenceActionChip({ entry, onClick }: SentenceActionChipProps) {
  const config = TYPE_CONFIG[entry.type]

  const handleClick = () => {
    if (onClick) {
      onClick(entry)
    }
  }

  return (
    <View
      className={`sentence-action-chip ${entry.type}`}
      onClick={handleClick}
    >
      <LucideIcon name={config.icon} size={14} color={config.color} />
      <Text className='chip-label' style={{ color: config.color }}>
        {entry.label}
      </Text>
    </View>
  )
}

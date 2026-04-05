import { View, Text } from '@tarojs/components'
import { SentenceEntryModel } from '../../types/view/render-scene.vm'
import LucideIcon from '../LucideIcon'
import './index.scss'

interface SentenceActionChipProps {
  entry: SentenceEntryModel
  onClick?: (entry: SentenceEntryModel) => void
}

const TYPE_CONFIG = {
  grammar_note: { icon: 'book', color: '#22c55e' },
  sentence_analysis: { icon: 'sparkles', color: '#8b5cf6' },
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
    >
      <LucideIcon name={config.icon} size={12} color={config.color} />
      <Text className='chip-label' style={{ color: config.color }}>
        {entry.label}
      </Text>
    </View>
  )
}

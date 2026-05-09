import { memo } from 'react'
import { Text } from '@tarojs/components'
import type { CommonEvent } from '@tarojs/components/types/common'
import type { ClickEvent } from '../../types/taro-events'
import './index.scss'

interface ClickableWordProps {
  word: string
  isSaved?: boolean
  savedStatus?: string
  className?: string
  isInSelection?: boolean
  onClick: (word: string, event: ClickEvent) => void
  onLongPress?: (word: string, event: CommonEvent) => void
}

const ClickableWord = memo(function ClickableWord({ word, isSaved, savedStatus, className, isInSelection, onClick, onLongPress }: ClickableWordProps) {
  const savedClass = isSaved
    ? `saved ${savedStatus === 'mastered' ? 'saved-mastered' : ''}`
    : ''

  const selectionClass = isInSelection ? 'in-selection' : ''

  return (
    <Text
      className={['clickable-word', className, savedClass, selectionClass].filter(Boolean).join(' ')}
      onClick={(e) => {
        e.stopPropagation()
        onClick(word, e)
      }}
      onLongPress={onLongPress ? (e) => {
        e.stopPropagation()
        onLongPress(word, e)
      } : undefined}
    >
      {word}
    </Text>
  )
})

export default ClickableWord

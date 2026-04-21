import { memo } from 'react'
import { Text } from '@tarojs/components'
import type { ClickEvent } from '../../types/taro-events'
import './index.scss'

interface ClickableWordProps {
  word: string
  isSaved?: boolean
  savedStatus?: string
  className?: string
  onClick: (word: string, event: ClickEvent) => void
}

const ClickableWord = memo(function ClickableWord({ word, isSaved, savedStatus, className, onClick }: ClickableWordProps) {
  const savedClass = isSaved
    ? `saved ${savedStatus === 'mastered' ? 'saved-mastered' : ''}`
    : ''

  return (
    <Text
      className={['clickable-word', className, savedClass].filter(Boolean).join(' ')}
      onClick={(e) => {
        e.stopPropagation()
        onClick(word, e)
      }}
    >
      {word}
    </Text>
  )
})

export default ClickableWord

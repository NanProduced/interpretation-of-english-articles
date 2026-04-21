import { View, Text } from '@tarojs/components'
import { memo } from 'react'
import type { DailyReaderHighlight } from '../../types/view/daily-reader.vm'
import './index.scss'

interface Props {
  highlight: DailyReaderHighlight
  isActive?: boolean
  onWordClick?: (highlight: DailyReaderHighlight) => void
}

const TYPE_CLASS: Record<string, string> = {
  vocab_highlight: 'daily-hl--vocab',
  phrase_gloss: 'daily-hl--phrase',
  context_gloss: 'daily-hl--context',
}

const DailyReaderHighlightWord = memo(function DailyReaderHighlightWord({
  highlight,
  isActive,
  onWordClick,
}: Props) {
  const typeClass = TYPE_CLASS[highlight.type] || 'daily-hl--vocab'

  return (
    <Text
      className={`daily-hl ${typeClass} ${isActive ? 'daily-hl--active' : ''}`}
      onClick={(e) => {
        e.stopPropagation()
        onWordClick?.(highlight)
      }}
    >
      {highlight.text}
    </Text>
  )
})

export default DailyReaderHighlightWord

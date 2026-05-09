import { View, Text } from '@tarojs/components'
import { memo } from 'react'
import type { DailyReaderHighlight } from '../../types/view/daily-reader.vm'
import type { ITouchEvent } from '@tarojs/components/types/common'
import './index.scss'

interface Props {
  highlight: DailyReaderHighlight
  isActive?: boolean
  isHintTarget?: boolean
  onWordClick?: (highlight: DailyReaderHighlight, tapPosition: { x: number; y: number }) => void
}

const TYPE_CLASS: Record<string, string> = {
  vocab_highlight: 'daily-hl--vocab',
  phrase_gloss: 'daily-hl--phrase',
  context_gloss: 'daily-hl--context',
}

const TYPE_ICON: Record<string, string> = {
  vocab_highlight: '文',
  phrase_gloss: '句',
  context_gloss: '境',
}

const DailyReaderHighlightWord = memo(function DailyReaderHighlightWord({
  highlight,
  isActive,
  isHintTarget,
  onWordClick,
}: Props) {
  const typeClass = TYPE_CLASS[highlight.type] || 'daily-hl--vocab'
  const typeIcon = TYPE_ICON[highlight.type] || '文'

  const handleClick = (e: ITouchEvent) => {
    e.stopPropagation()
    if (!onWordClick) return
    
    const touch = e.touches?.[0] || e.changedTouches?.[0]
    const position = touch 
      ? { x: touch.clientX, y: touch.clientY }
      : { x: 0, y: 0 }
    
    onWordClick(highlight, position)
  }

  return (
    <Text
      className={`daily-hl ${typeClass} ${isActive ? 'daily-hl--active' : ''} ${isHintTarget ? 'daily-hl--hint' : ''}`}
      onClick={handleClick}
    >
      {highlight.text}
      <Text className='daily-hl__icon'>{typeIcon}</Text>
    </Text>
  )
})

export default DailyReaderHighlightWord

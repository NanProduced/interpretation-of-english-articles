import { View, Text } from '@tarojs/components'
import { memo, useCallback } from 'react'
import type { DailyReaderBody as DailyReaderBodyType, DailyReaderHighlight } from '../../types/view/daily-reader.vm'
import DailyReaderHighlightWord from '../DailyReaderHighlightWord'
import type { ClickEvent } from '../../types/taro-events'
import type { ITouchEvent } from '@tarojs/components/types/common'
import './index.scss'

interface Props {
  body: DailyReaderBodyType
  highlights: DailyReaderHighlight[]
  onHighlightClick?: (highlight: DailyReaderHighlight, tapPosition?: { x: number; y: number }, contextSentence?: string) => void
  onWordClick?: (word: string, tapPosition?: { x: number; y: number }) => void
  showHighlightHint?: boolean
}

const DailyReaderBody = memo(function DailyReaderBody({
  body,
  highlights,
  onHighlightClick,
  onWordClick,
  showHighlightHint,
}: Props) {
  const handleTextClick = useCallback(
    (e: ClickEvent) => {
      const target = e.target as HTMLElement
      if (!target || !target.dataset?.word) return
      
      const touch = e.touches?.[0] || e.changedTouches?.[0]
      const position = touch 
        ? { x: touch.clientX, y: touch.clientY }
        : undefined
      
      onWordClick?.(target.dataset.word, position)
    },
    [onWordClick],
  )

  return (
    <View className='daily-body'>
      {body.paragraphs.map((paragraph) => {
        const paraHighlights = highlights.filter(
          (h) => h.paragraphId === paragraph.id,
        )

        return (
          <View key={paragraph.id} className='daily-body__paragraph'>
            <Text className='daily-body__text' onClick={handleTextClick}>
              {renderParagraphWithHighlights(paragraph.text, paraHighlights, onHighlightClick, showHighlightHint)}
            </Text>
          </View>
        )
      })}
    </View>
  )
})

function renderParagraphWithHighlights(
  text: string,
  highlights: DailyReaderHighlight[],
  onHighlightClick?: (highlight: DailyReaderHighlight, tapPosition?: { x: number; y: number }, contextSentence?: string) => void,
  showHighlightHint?: boolean,
) {
  if (!highlights.length) return text

  const sorted = [...highlights].sort((a, b) => a.start - b.start)
  const parts: React.ReactNode[] = []
  let lastEnd = 0

  sorted.forEach((hl, idx) => {
    const start = Math.max(0, Math.min(hl.start, text.length))
    const end = Math.max(start, Math.min(hl.end, text.length))
    if (start < lastEnd || end <= start) return

    if (start > lastEnd) {
      parts.push(
        <Text key={`t-${idx}`}>{text.slice(lastEnd, start)}</Text>,
      )
    }
    parts.push(
      <DailyReaderHighlightWord
        key={`hl-${hl.id}`}
        highlight={hl}
        displayText={text.slice(start, end)}
        contextSentence={extractContextSentence(text, start, end)}
        onWordClick={onHighlightClick}
        isHintTarget={showHighlightHint && idx === 0}
      />,
    )
    lastEnd = end
  })

  if (lastEnd < text.length) {
    parts.push(<Text key='tail'>{text.slice(lastEnd)}</Text>)
  }

  return parts
}

function extractContextSentence(text: string, start: number, end: number) {
  const before = text.slice(0, start)
  const after = text.slice(end)
  const left = Math.max(
    before.lastIndexOf('.'),
    before.lastIndexOf('!'),
    before.lastIndexOf('?'),
    before.lastIndexOf(';'),
    before.lastIndexOf('。'),
    before.lastIndexOf('！'),
    before.lastIndexOf('？'),
  )
  const rightCandidates = ['.', '!', '?', ';', '。', '！', '？']
    .map((mark) => after.indexOf(mark))
    .filter((idx) => idx >= 0)
  const right = rightCandidates.length ? Math.min(...rightCandidates) + end + 1 : text.length
  return text.slice(left >= 0 ? left + 1 : 0, right).trim()
}

export default DailyReaderBody

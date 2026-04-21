import { View, Text } from '@tarojs/components'
import { memo, useCallback } from 'react'
import type { DailyReaderBody as DailyReaderBodyType, DailyReaderHighlight } from '../../types/view/daily-reader.vm'
import DailyReaderHighlightWord from '../DailyReaderHighlightWord'
import './index.scss'

interface Props {
  body: DailyReaderBodyType
  highlights: DailyReaderHighlight[]
  onHighlightClick?: (highlight: DailyReaderHighlight) => void
  onWordClick?: (word: string) => void
}

const DailyReaderBody = memo(function DailyReaderBody({
  body,
  highlights,
  onHighlightClick,
  onWordClick,
}: Props) {
  const handleTextClick = useCallback(
    (e: any) => {
      const target = e.target as HTMLElement
      if (!target || !target.dataset?.word) return
      onWordClick?.(target.dataset.word)
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
              {renderParagraphWithHighlights(paragraph.text, paraHighlights, onHighlightClick)}
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
  onHighlightClick?: (highlight: DailyReaderHighlight) => void,
) {
  if (!highlights.length) return text

  const sorted = [...highlights].sort((a, b) => a.start - b.start)
  const parts: React.ReactNode[] = []
  let lastEnd = 0

  sorted.forEach((hl, idx) => {
    if (hl.start > lastEnd) {
      parts.push(
        <Text key={`t-${idx}`}>{text.slice(lastEnd, hl.start)}</Text>,
      )
    }
    parts.push(
      <DailyReaderHighlightWord
        key={`hl-${hl.id}`}
        highlight={hl}
        onWordClick={onHighlightClick}
      />,
    )
    lastEnd = hl.end
  })

  if (lastEnd < text.length) {
    parts.push(<Text key='tail'>{text.slice(lastEnd)}</Text>)
  }

  return parts
}

export default DailyReaderBody

import { Text } from '@tarojs/components'
import { AnyInlineMarkModel, VisualTone, AcademicVisualTone } from '../../types/view/render-scene.vm'
import type { WordClickPayload } from '../ParagraphBlock'
import type { ClickEvent } from '../../types/taro-events'
import './index.scss'

const TONE_CLASSES: Record<VisualTone | AcademicVisualTone, string> = {
  vocab: 'tone-vocab',
  phrase: 'tone-phrase',
  context: 'tone-context',
  grammar: 'tone-grammar',
  term: 'tone-term',
  logic: 'tone-logic',
}

interface InlineMarkProps {
  mark: AnyInlineMarkModel
  text: string
  isActive?: boolean
  isSaved?: boolean
  savedStatus?: string
  onWordClick?: (payload: WordClickPayload) => void
}

export default function InlineMark({ mark, text, isActive, isSaved, savedStatus, onWordClick }: InlineMarkProps) {
  const toneClass = TONE_CLASSES[mark.visualTone]

  const handleClick = (e: ClickEvent) => {
    e.stopPropagation()
    if (mark.clickable && onWordClick) {
      onWordClick({ word: text, mark, event: e })
    }
  }

  const savedClass = isSaved
    ? `saved ${savedStatus === 'mastered' ? 'saved-mastered' : ''}`
    : ''

  return (
    <Text
      className={`inline-mark ${mark.renderType} ${toneClass} ${mark.clickable ? 'clickable' : ''} ${isActive ? 'active' : ''} ${savedClass}`}
      onClick={handleClick}
    >
      {text}
    </Text>
  )
}

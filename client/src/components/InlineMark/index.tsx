import { Text } from '@tarojs/components'
import { InlineMarkModel, VisualTone } from '../../types/view/render-scene.vm'
import type { WordClickPayload } from '../ParagraphBlock'
import './index.scss'

const TONE_CLASSES: Record<VisualTone, string> = {
  vocab: 'tone-vocab',
  phrase: 'tone-phrase',
  context: 'tone-context',
  grammar: 'tone-grammar',
}

interface InlineMarkProps {
  mark: InlineMarkModel
  text: string
  isActive?: boolean
  isSaved?: boolean // 是否已加入生词本
  onWordClick?: (payload: WordClickPayload) => void
}

export default function InlineMark({ mark, text, isActive, isSaved, onWordClick }: InlineMarkProps) {
  const toneClass = TONE_CLASSES[mark.visualTone]

  const handleClick = (e: any) => {
    e.stopPropagation()
    if (mark.clickable && onWordClick) {
      onWordClick({ word: text, mark, event: e })
    }
  }

  return (
    <Text
      className={`inline-mark ${mark.renderType} ${toneClass} ${mark.clickable ? 'clickable' : ''} ${isActive ? 'active' : ''} ${isSaved ? 'saved' : ''}`}
      onClick={handleClick}
    >
      {text}
    </Text>
  )
}

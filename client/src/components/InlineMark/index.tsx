import { Text } from '@tarojs/components'
import { InlineMarkModel, VisualTone } from '../../types/view/render-scene.vm'
import type { WordClickPayload } from '../ParagraphBlock'
import './index.scss'

interface InlineMarkProps {
  mark: InlineMarkModel
  text: string
  isActive?: boolean
  isSaved?: boolean // 是否已加入生词本
  onWordClick?: (payload: WordClickPayload) => void
}

const TONE_CLASSES: Record<VisualTone, string> = {
  vocab: 'tone-vocab',
  phrase: 'tone-phrase',
  context: 'tone-context',
  grammar: 'tone-grammar',
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
      role='button'
      aria-label={`${isSaved ? '已收藏生词: ' : ''}${mark.visualTone}标注: ${text}`}
    >
      {text}
    </Text>
  )
}

function hexToRgb(hex: string): string {
  if (hex.startsWith('var')) return '128, 128, 128'
  let r = 0, g = 0, b = 0
  if (hex.length === 4) {
    r = parseInt(hex[1] + hex[1], 16)
    g = parseInt(hex[2] + hex[2], 16)
    b = parseInt(hex[3] + hex[3], 16)
  } else if (hex.length === 7) {
    r = parseInt(hex[1] + hex[2], 16)
    g = parseInt(hex[3] + hex[4], 16)
    b = parseInt(hex[5] + hex[6], 16)
  }
  return `${r}, ${g}, ${b}`
}

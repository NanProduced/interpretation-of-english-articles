import { Text } from '@tarojs/components'
import { InlineMarkModel, VisualTone } from '../../types/render-scene'
import './index.scss'

interface InlineMarkProps {
  mark: InlineMarkModel
  text: string
  onClick?: (mark: InlineMarkModel, word: string, event?: any) => void
}

const TONE_COLORS: Record<VisualTone, { bg: string; text: string }> = {
  vocab: { bg: 'rgba(239, 68, 68, 0.1)', text: '#ef4444' },
  phrase: { bg: 'rgba(139, 92, 246, 0.1)', text: '#8b5cf6' },
  context: { bg: 'rgba(66, 133, 244, 0.1)', text: '#4285f4' },
  grammar: { bg: 'rgba(34, 197, 94, 0.1)', text: '#22c55e' },
}

export default function InlineMark({ mark, text, onClick }: InlineMarkProps) {
  const colors = TONE_COLORS[mark.visualTone]

  const handleClick = (e: any) => {
    e.stopPropagation()
    if (mark.clickable && onClick) {
      onClick(mark, text, e)
    }
  }

  if (mark.renderType === 'underline') {
    return (
      <Text
        className={`inline-mark underline ${mark.clickable ? 'clickable' : ''}`}
        style={{
          color: colors.text,
          borderBottomColor: colors.text,
        }}
        onClick={handleClick}
      >
        {text}
      </Text>
    )
  }

  return (
    <Text
      className={`inline-mark background ${mark.clickable ? 'clickable' : ''}`}
      style={{
        backgroundColor: colors.bg,
        color: colors.text,
      }}
      onClick={handleClick}
    >
      {text}
    </Text>
  )
}

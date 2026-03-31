import { View, Text } from '@tarojs/components'
import { InlineMarkModel, InlineMarkTone } from '../../types/v2-render'
import './index.scss'

interface InlineMarkProps {
  mark: InlineMarkModel
  text: string
  onClick?: (mark: InlineMarkModel, word: string) => void
}

const TONE_COLORS: Record<InlineMarkTone, { bg: string; text: string; border?: string }> = {
  info: { bg: 'rgba(66, 133, 244, 0.15)', text: '#4285f4' },
  focus: { bg: 'rgba(251, 146, 60, 0.15)', text: '#fb923c' },
  exam: { bg: 'rgba(239, 68, 68, 0.12)', text: '#ef4444' },
  phrase: { bg: 'rgba(139, 92, 246, 0.12)', text: '#8b5cf6' },
  grammar: { bg: 'rgba(34, 197, 94, 0.12)', text: '#22c55e' },
}

export default function InlineMark({ mark, text, onClick }: InlineMarkProps) {
  const colors = TONE_COLORS[mark.tone]

  const handleClick = () => {
    if (mark.clickable && onClick) {
      onClick(mark, text)
    }
  }

  if (mark.renderType === 'underline') {
    return (
      <Text
        className={`inline-mark underline ${mark.clickable ? 'clickable' : ''}`}
        style={{
          color: colors.text,
          borderBottomColor: colors.text,
          borderBottomStyle: 'dashed',
          borderBottomWidth: '1px',
        }}
        onClick={handleClick}
        onTap={handleClick}
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
      onTap={handleClick}
    >
      {text}
    </Text>
  )
}

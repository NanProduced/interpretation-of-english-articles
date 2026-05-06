import { View } from '@tarojs/components'
import './index.scss'

interface AnnotationGlyphProps {
  type: 'vocab' | 'phrase' | 'context' | 'grammar_note' | 'sentence_analysis' | 'saved_vocab' | 'merged_note' | 'feedback'
  size?: number
  state?: 'default' | 'active' | 'disabled'
  className?: string
}

export default function AnnotationGlyph({
  type,
  size = 36,
  state = 'default',
  className = ''
}: AnnotationGlyphProps) {
  const stateClass = state !== 'default' ? `glyph-state-${state}` : ''

  return (
    <View
      className={`annotation-glyph glyph-${type} ${stateClass} ${className}`}
      style={{ width: `${size}rpx`, height: `${size}rpx` }}
    />
  )
}

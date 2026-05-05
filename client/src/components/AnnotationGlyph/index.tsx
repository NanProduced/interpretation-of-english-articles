import { View } from '@tarojs/components'
import './index.scss'

export type AnnotationGlyphType =
  | 'vocab'
  | 'phrase'
  | 'context'
  | 'grammar_note'
  | 'sentence_analysis'
  | 'saved_vocab'
  | 'merged_note'
  | 'feedback'

export type AnnotationGlyphState = 'default' | 'active' | 'disabled'

interface AnnotationGlyphProps {
  type: AnnotationGlyphType
  state?: AnnotationGlyphState
  size?: number
  className?: string
}

// 纯代码绘制的 Annotation Glyphs (Paper annotation style)
const GLYPH_PATHS: Record<AnnotationGlyphType, string> = {
  // vocab: highlighter tip (tilted parallelogram)
  vocab: '<path d="M5 16 L13 4 L19 8 L11 20 Z"/>',
  // phrase: two staggered parallel highlighter strokes
  phrase: '<line x1="4" x2="16" y1="9" y2="9"/><line x1="8" x2="20" y1="15" y2="15"/>',
  // context: hairline underline with a dot at the end
  context: '<line x1="4" x2="17" y1="12" y2="12"/><circle cx="19" cy="12" r="1.5"/>',
  // grammar_note: two small nodes connected by a soft curve
  grammar_note: '<circle cx="6" cy="16" r="2.5"/><circle cx="18" cy="8" r="2.5"/><path d="M7.5 14.5 C 10 10, 14 14, 16.5 9.5"/>',
  // sentence_analysis: three staggered horizontal layers
  sentence_analysis: '<line x1="4" x2="16" y1="7" y2="7"/><line x1="8" x2="20" y1="12" y2="12"/><line x1="4" x2="14" y1="17" y2="17"/>',
  // saved_vocab: rectangular bookmark with bottom-right folded corner
  saved_vocab: '<path d="M5 4 H19 V15 L14 20 H5 Z"/><path d="M19 15 H14 V20"/>',
  // merged_note: folded paper tab
  merged_note: '<path d="M5 4 H15 L19 8 V20 H5 Z"/><path d="M15 4 V8 H19"/>',
  // feedback: simple chat bubble with question mark
  feedback: '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/><path d="M9 9h1a2 2 0 0 1 2 2v0a2 2 0 0 1-2 2h-1"/><line x1="12" y1="17" x2="12.01" y2="17"/>'
}

function encodeSvg(path: string, color: string, strokeWidth: number) {
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='${color}' stroke-width='${strokeWidth}' stroke-linecap='round' stroke-linejoin='round'>${path}</svg>`
  return svg.replace(/"/g, "'").replace(/#/g, '%23').replace(/</g, '%3C').replace(/>/g, '%3E')
}

// Map logical type & state to semantic colors
function getGlyphColor(type: AnnotationGlyphType, state: AnnotationGlyphState): string {
  if (state === 'disabled') {
    return 'rgba(122, 125, 134, 0.35)' // 35% opacity reader-muted
  }
  
  if (state === 'default') {
    return '#7A7D86' // reader-muted (ink gray)
  }

  // Active state tints
  switch (type) {
    case 'vocab':
      return '#E4B000'
    case 'saved_vocab':
      return '#E4B000' // or perhaps #3F6FB6 if merged, but #E4B000 is fine
    case 'phrase':
      return '#B9A8E6'
    case 'context':
      return '#5A6F8F'
    case 'grammar_note':
      return '#6B5FC7'
    case 'sentence_analysis':
      return '#3F6FB6'
    case 'merged_note':
      return '#3F6FB6'
    default:
      return '#121212'
  }
}

export default function AnnotationGlyph({
  type,
  state = 'default',
  size = 28,
  className = ''
}: AnnotationGlyphProps) {
  const path = GLYPH_PATHS[type] || ''
  
  // Use slightly thinner stroke for a "stationery/paper mark" feel
  const strokeWidth = 1.5 
  const color = getGlyphColor(type, state)
  const encoded = encodeSvg(path, color, strokeWidth)
  const backgroundImage = `url("data:image/svg+xml,${encoded}")`

  return (
    <View 
      className={`annotation-glyph annotation-glyph--${type} annotation-glyph--${state} ${className}`}
      style={{
        width: typeof size === 'number' ? `${size}rpx` : size,
        height: typeof size === 'number' ? `${size}rpx` : size,
        backgroundImage,
        backgroundRepeat: 'no-repeat',
        backgroundSize: '100% 100%',
        backgroundPosition: 'center',
        flexShrink: 0,
        boxSizing: 'border-box'
      }}
    />
  )
}

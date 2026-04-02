import { Text } from '@tarojs/components'
import { InlineMarkModel, VisualTone } from '../../types/render-scene'
import './index.scss'

interface InlineMarkProps {
  mark: InlineMarkModel
  text: string
  isActive?: boolean
  onClick?: (mark: InlineMarkModel, word: string, event?: any) => void
}

const TONE_COLORS: Record<VisualTone, string> = {
  vocab: 'var(--vocab-color)',
  phrase: 'var(--phrase-color)',
  context: 'var(--primary-color)',
  grammar: 'var(--grammar-color)',
}

export default function InlineMark({ mark, text, isActive, onClick }: InlineMarkProps) {
  const color = TONE_COLORS[mark.visualTone]

  const handleClick = (e: any) => {
    e.stopPropagation()
    if (mark.clickable && onClick) {
      onClick(mark, text, e)
    }
  }

  // 默认层使用半透明背景模拟真实文具感 (Highlighter style)
  const baseStyle = {
    backgroundColor: mark.renderType === 'background' ? `rgba(${hexToRgb(color)}, 0.15)` : 'transparent',
    color: mark.visualTone === 'context' ? 'var(--text-main)' : color,
    borderRadius: '4rpx',
    padding: '0 2rpx',
    margin: '0 1rpx',
    borderBottom: mark.renderType === 'underline' ? `2rpx dashed ${color}` : 'none',
  }

  const activeStyle = isActive ? {
    backgroundColor: 'var(--active-highlight-bg)',
    color: 'var(--active-highlight-text)',
    padding: '2rpx 4rpx',
    margin: '0 -2rpx',
    borderBottom: 'none',
    boxShadow: '0 2rpx 8rpx rgba(0,0,0,0.05)',
  } : {}

  return (
    <Text
      className={`inline-mark ${mark.renderType} ${mark.clickable ? 'clickable' : ''} ${isActive ? 'active' : ''}`}
      style={{
        ...baseStyle,
        ...activeStyle
      }}
      onClick={handleClick}
    >
      {text}
    </Text>
  )
}

// Helper to convert hex to rgb for alpha support
function hexToRgb(hex: string): string {
  if (hex.startsWith('var')) return '128, 128, 128'; // Fallback for CSS vars
  let r = 0, g = 0, b = 0;
  // 3 digits
  if (hex.length === 4) {
    r = parseInt(hex[1] + hex[1], 16);
    g = parseInt(hex[2] + hex[2], 16);
    b = parseInt(hex[3] + hex[3], 16);
  } else if (hex.length === 7) {
    r = parseInt(hex[1] + hex[2], 16);
    g = parseInt(hex[3] + hex[4], 16);
    b = parseInt(hex[5] + hex[6], 16);
  }
  return `${r}, ${g}, ${b}`;
}

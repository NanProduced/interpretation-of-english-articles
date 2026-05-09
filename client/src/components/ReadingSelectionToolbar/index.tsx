import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { memo, useState, useEffect, useCallback } from 'react'
import LucideIcon from '../LucideIcon'
import './index.scss'

export interface SelectionContext {
  recordId?: string
  paragraphId?: string
  sentenceId: string
  selectedText: string
  startOffset: number
  endOffset: number
  translation?: string
  anchorType: 'sentence' | 'paragraph' | 'text_range'
  isShort?: boolean
}

type CopyMode = 'original' | 'translation' | 'bilingual'

interface Props {
  visible: boolean
  context: SelectionContext | null
  onClose: () => void
  onCopy: (mode: CopyMode) => void
  onFavorite: () => void
  onNote: () => void
  onHighlight: (color: string) => void
  onFeedback: () => void
  onDictionary?: () => void
}

const COLOR_THEMES = [
  { value: 'warm_yellow', color: '#FCD34D' },
  { value: 'soft_blue', color: '#93C5FD' },
  { value: 'sage_green', color: '#86EFAC' },
]

const ReadingSelectionToolbar = memo(function ReadingSelectionToolbar({
  visible,
  context,
  onClose,
  onCopy,
  onFavorite,
  onNote,
  onHighlight,
  onFeedback,
  onDictionary,
}: Props) {
  const [showCopyMenu, setShowCopyMenu] = useState(false)
  const [activeColor, setActiveColor] = useState('warm_yellow')
  const [toolbarPos, setToolbarPos] = useState<{ top: number; left: number } | null>(null)

  useEffect(() => {
    if (!visible || !context?.sentenceId) {
      setToolbarPos(null)
      return
    }
    const timer = setTimeout(() => {
      const query = Taro.createSelectorQuery()
      query.selectAll(`.sentence-${context.sentenceId} .in-selection`).boundingClientRect()
      query.exec((res) => {
        const rects = res[0]
        if (!rects || rects.length === 0) {
          setToolbarPos(null)
          return
        }
        let top = Infinity
        let bottom = -Infinity
        let left = Infinity
        let right = -Infinity
        for (const r of rects) {
          if (!r) continue
          top = Math.min(top, r.top)
          bottom = Math.max(bottom, r.bottom)
          left = Math.min(left, r.left)
          right = Math.max(right, r.right)
        }
        const centerX = (left + right) / 2
        const aboveTop = top - 56
        const belowTop = bottom + 12
        const useAbove = aboveTop > 60
        setToolbarPos({
          top: useAbove ? aboveTop : belowTop,
          left: Math.max(16, Math.min(centerX, 360)),
        })
      })
    }, 80)
    return () => clearTimeout(timer)
  }, [visible, context?.sentenceId, context?.startOffset, context?.endOffset])

  const handleAction = useCallback((action: () => void) => (e: any) => {
    e.stopPropagation()
    action()
  }, [])

  const handleCopyClick = useCallback((e: any) => {
    e.stopPropagation()
    setShowCopyMenu(prev => !prev)
  }, [])

  const handleCopyMode = useCallback((mode: CopyMode) => (e: any) => {
    e.stopPropagation()
    setShowCopyMenu(false)
    onCopy(mode)
  }, [onCopy])

  const handleColorSelect = useCallback((color: string) => (e: any) => {
    e.stopPropagation()
    setActiveColor(color)
  }, [])

  const handleHighlight = useCallback((e: any) => {
    e.stopPropagation()
    onHighlight(activeColor)
  }, [onHighlight, activeColor])

  if (!visible || !context) return null

  const posStyle: React.CSSProperties = toolbarPos
    ? { position: 'absolute', top: `${toolbarPos.top}px`, left: `${toolbarPos.left}px`, transform: 'translateX(-50%)' }
    : {}

  return (
    <View className='sel-toolbar-root'>
      <View className='sel-backdrop' onClick={onClose} />
      <View
        className={`sel-floating-toolbar ${toolbarPos ? 'sel-floating-toolbar--anchored' : ''}`}
        style={posStyle}
        onClick={e => e.stopPropagation()}
      >
        <View className='sel-color-strip'>
          {COLOR_THEMES.map(t => (
            <View
              key={t.value}
              className={`sel-color-dot ${activeColor === t.value ? 'sel-color-dot--active' : ''}`}
              style={{ backgroundColor: t.color }}
              onClick={handleColorSelect(t.value)}
            >
              {activeColor === t.value && (
                <View className='sel-color-dot-inner' />
              )}
            </View>
          ))}
        </View>

        <View className='sel-divider' />

        <View className='sel-tool-btn' onClick={handleHighlight}>
          <LucideIcon name='highlighter' size={20} color='currentColor' />
        </View>

        <View className='sel-tool-btn' onClick={handleAction(onNote)}>
          <LucideIcon name='pen-line' size={20} color='currentColor' />
        </View>

        <View className='sel-tool-btn sel-tool-btn--has-menu' onClick={handleCopyClick}>
          <LucideIcon name='copy' size={20} color='currentColor' />
          {showCopyMenu && (
            <View className='sel-copy-menu' onClick={e => e.stopPropagation()}>
              <View className='sel-copy-menu-item' onClick={handleCopyMode('original')}>
                <Text>复制原文</Text>
              </View>
              {context.translation && (
                <View className='sel-copy-menu-item' onClick={handleCopyMode('translation')}>
                  <Text>复制译文</Text>
                </View>
              )}
              <View className='sel-copy-menu-item' onClick={handleCopyMode('bilingual')}>
                <Text>复制双语</Text>
              </View>
            </View>
          )}
        </View>

        <View className='sel-tool-btn' onClick={handleAction(onFavorite)}>
          <LucideIcon name='bookmark' size={20} color='currentColor' />
        </View>

        {context.isShort && onDictionary && (
          <View className='sel-tool-btn' onClick={handleAction(onDictionary)}>
            <LucideIcon name='book-open' size={20} color='currentColor' />
          </View>
        )}

        <View className='sel-divider' />

        <View className='sel-tool-btn' onClick={handleAction(onFeedback)}>
          <LucideIcon name='message-square-warning' size={20} color='currentColor' />
        </View>
      </View>
    </View>
  )
})

export default ReadingSelectionToolbar
export type { CopyMode }

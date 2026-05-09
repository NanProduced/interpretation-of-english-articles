import { View, Text } from '@tarojs/components'
import { memo, useState } from 'react'
import LucideIcon from '../LucideIcon'
import Taro from '@tarojs/taro'
import './index.scss'

export interface SelectionContext {
  recordId?: string
  paragraphId?: string
  sentenceId: string
  text: string
  translation?: string
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
  onHighlight: () => void
  onFeedback: () => void
  onDictionary?: () => void
}

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

  if (!visible || !context) return null

  const handleAction = (action: () => void) => (e: any) => {
    e.stopPropagation()
    action()
  }

  const handleCopyClick = (e: any) => {
    e.stopPropagation()
    setShowCopyMenu(prev => !prev)
  }

  const handleCopyMode = (mode: CopyMode) => (e: any) => {
    e.stopPropagation()
    setShowCopyMenu(false)
    onCopy(mode)
  }

  return (
    <View className='sel-toolbar-overlay' onClick={onClose}>
      <View className='sel-toolbar-container' onClick={e => e.stopPropagation()}>
        <View className='sel-toolbar'>
          <View className='sel-toolbar-item' onClick={handleAction(onHighlight)}>
            <LucideIcon name='highlighter' size={18} color='currentColor' />
            <Text className='sel-toolbar-text'>高亮</Text>
          </View>
          <View className='sel-toolbar-item' onClick={handleAction(onNote)}>
            <LucideIcon name='pen-line' size={18} color='currentColor' />
            <Text className='sel-toolbar-text'>笔记</Text>
          </View>
          <View className='sel-toolbar-item sel-toolbar-item--copy' onClick={handleCopyClick}>
            <LucideIcon name='copy' size={18} color='currentColor' />
            <Text className='sel-toolbar-text'>复制</Text>
            {showCopyMenu && (
              <View className='sel-copy-menu'>
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
          <View className='sel-toolbar-item' onClick={handleAction(onFavorite)}>
            <LucideIcon name='bookmark' size={18} color='currentColor' />
            <Text className='sel-toolbar-text'>收藏</Text>
          </View>

          {context.isShort && onDictionary && (
            <View className='sel-toolbar-item' onClick={handleAction(onDictionary)}>
              <LucideIcon name='book-open' size={18} color='currentColor' />
              <Text className='sel-toolbar-text'>查词</Text>
            </View>
          )}

          <View className='sel-toolbar-item' onClick={handleAction(onFeedback)}>
            <LucideIcon name='message-square-warning' size={18} color='currentColor' />
            <Text className='sel-toolbar-text'>反馈</Text>
          </View>
        </View>
      </View>
    </View>
  )
})

export default ReadingSelectionToolbar
export type { CopyMode }

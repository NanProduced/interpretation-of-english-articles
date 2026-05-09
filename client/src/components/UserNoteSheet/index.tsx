import { View, Text, Textarea } from '@tarojs/components'
import { memo, useState, useEffect } from 'react'
import LucideIcon from '../LucideIcon'
import './index.scss'

interface Props {
  visible: boolean
  selectionText?: string
  initialColor?: string
  initialNote?: string
  onClose: () => void
  onSave: (color: string, note: string) => void
  onHighlightOnly?: (color: string) => void
  onDelete?: () => void
}

const THEMES = [
  { value: 'warm_yellow', label: '暖黄', color: '#FCD34D', bg: 'rgba(252, 211, 77, 0.12)' },
  { value: 'soft_blue', label: '浅蓝', color: '#93C5FD', bg: 'rgba(147, 197, 253, 0.12)' },
  { value: 'sage_green', label: '柔绿', color: '#86EFAC', bg: 'rgba(134, 239, 172, 0.12)' },
]

const UserNoteSheet = memo(function UserNoteSheet({
  visible,
  selectionText,
  initialColor = 'warm_yellow',
  initialNote = '',
  onClose,
  onSave,
  onHighlightOnly,
  onDelete
}: Props) {
  const [color, setColor] = useState(initialColor)
  const [note, setNote] = useState(initialNote)

  useEffect(() => {
    if (visible) {
      setColor(initialColor)
      setNote(initialNote)
    }
  }, [visible, initialColor, initialNote])

  if (!visible) return null

  const handleSave = () => {
    onSave(color, note.trim())
  }

  const handleHighlightOnly = () => {
    onHighlightOnly?.(color)
  }

  const activeTheme = THEMES.find(t => t.value === color) || THEMES[0]

  return (
    <View className='un-overlay' onClick={onClose}>
      <View className='un-sheet' onClick={e => e.stopPropagation()}>
        <View className='un-handle' />

        <View className='un-header'>
          <View className='un-actions un-actions--left'>
            {onDelete && (
              <View className='un-icon-btn' onClick={onDelete}>
                <LucideIcon name='trash-2' size={20} color='var(--color-danger)' />
              </View>
            )}
          </View>
          <Text className='un-title'>{note.trim() ? '添加笔记' : '高亮标注'}</Text>
          <View className='un-actions un-actions--right'>
            <View className='un-icon-btn' onClick={onClose}>
              <LucideIcon name='x' size={20} color='var(--text-secondary)' />
            </View>
          </View>
        </View>

        <View className='un-body'>
          {selectionText && (
            <View className='un-selection-preview' style={{ backgroundColor: activeTheme.bg }}>
              <Text className='un-selection-text' numberOfLines={3}>
                {selectionText}
              </Text>
            </View>
          )}

          <Textarea
            className='un-textarea'
            placeholder='写下你的想法...'
            placeholderClass='un-textarea-placeholder'
            value={note}
            onInput={e => setNote(e.detail.value)}
            maxlength={500}
            focus
            autoHeight
          />

          <View className='un-theme-picker'>
            <Text className='un-theme-label'>高亮颜色</Text>
            <View className='un-theme-options'>
              {THEMES.map(t => (
                <View
                  key={t.value}
                  className={`un-theme-option ${color === t.value ? 'un-theme-option--active' : ''}`}
                  onClick={() => setColor(t.value)}
                >
                  <View className='un-theme-circle' style={{ backgroundColor: t.color }}>
                    {color === t.value && <LucideIcon name='check' size={14} color='rgba(0,0,0,0.6)' />}
                  </View>
                  <Text className='un-theme-name'>{t.label}</Text>
                </View>
              ))}
            </View>
          </View>

          <View className='un-actions-row'>
            {onHighlightOnly && (
              <View className='un-btn un-btn--secondary' onClick={handleHighlightOnly}>
                <Text className='un-btn-text'>仅高亮</Text>
              </View>
            )}
            <View className='un-btn un-btn--primary' onClick={handleSave}>
              <Text className='un-btn-text un-btn-text--primary'>保存笔记</Text>
            </View>
          </View>
        </View>
      </View>
    </View>
  )
})

export default UserNoteSheet

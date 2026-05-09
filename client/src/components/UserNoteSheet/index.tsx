import { View, Text, Textarea } from '@tarojs/components'
import { memo, useState, useEffect } from 'react'
import LucideIcon from '../LucideIcon'
import './index.scss'

interface Props {
  visible: boolean
  initialColor?: string
  initialNote?: string
  onClose: () => void
  onSave: (color: string, note: string) => void
  onDelete?: () => void
}

const THEMES = [
  { value: 'warm_yellow', color: '#FCD34D' },
  { value: 'soft_blue', color: '#93C5FD' },
  { value: 'sage_green', color: '#86EFAC' },
]

const UserNoteSheet = memo(function UserNoteSheet({
  visible,
  initialColor = 'warm_yellow',
  initialNote = '',
  onClose,
  onSave,
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
          <Text className='un-title'>添加笔记</Text>
          <View className='un-actions un-actions--right'>
            <View className='un-icon-btn un-icon-btn--primary' onClick={handleSave}>
              <LucideIcon name='check' size={20} color='#FFFFFF' />
            </View>
          </View>
        </View>

        <View className='un-body'>
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
                  className={`un-theme-circle ${color === t.value ? 'un-theme-circle--active' : ''}`}
                  style={{ backgroundColor: t.color }}
                  onClick={() => setColor(t.value)}
                >
                  {color === t.value && <LucideIcon name='check' size={14} color='rgba(0,0,0,0.6)' />}
                </View>
              ))}
            </View>
          </View>
        </View>
      </View>
    </View>
  )
})

export default UserNoteSheet

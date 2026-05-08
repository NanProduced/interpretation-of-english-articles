import { useState, useEffect, useRef } from 'react'
import { View, Text } from '@tarojs/components'
import LucideIcon from '../LucideIcon'
import type { AcademicSentenceEntryType } from '../../types/view/render-scene.vm'
import './index.scss'

type NoteVariant = 'term' | 'logic' | 'interpretation'

interface GroupedNoteItem {
  id: string
  markId: string
  variant: NoteVariant
  title: string
  content: string
}

interface AcademicNoteGroupProps {
  items: GroupedNoteItem[]
  initiallyExpanded?: boolean
  onToggle?: (expanded: boolean, activeMarkIds: string[]) => void
  onActiveChange?: (activeMarkIds: string[]) => void
}

const VARIANT_LABEL: Record<NoteVariant, string> = {
  term: '术语',
  logic: '论证',
  interpretation: '阐释',
}

export default function AcademicNoteGroup({
  items,
  initiallyExpanded = false,
  onToggle,
  onActiveChange,
}: AcademicNoteGroupProps) {
  const [isExpanded, setIsExpanded] = useState(initiallyExpanded)
  const [activeItemId, setActiveItemId] = useState<string | null>(null)

  if (!items || items.length === 0) return null

  const handleToggle = () => {
    const next = !isExpanded
    setIsExpanded(next)
    if (next) {
      const ids = items.map(item => item.markId)
      onToggle?.(true, ids)
      onActiveChange?.(ids)
    } else {
      setActiveItemId(null)
      onToggle?.(false, [])
      onActiveChange?.([])
    }
  }

  const handleItemToggle = (itemId: string) => {
    const nextActive = activeItemId === itemId ? null : itemId
    setActiveItemId(nextActive)
    if (nextActive) {
      const item = items.find(i => i.id === itemId)
      onActiveChange?.(item ? [item.markId] : [])
    } else {
      onActiveChange?.(isExpanded ? items.map(i => i.markId) : [])
    }
  }

  return (
    <View className={`academic-note-group ${isExpanded ? 'is-expanded' : 'is-collapsed'} ${activeItemId ? 'has-active-item' : ''}`}>
      <View className='group-header' onClick={handleToggle}>
        <View className='group-chips'>
          {items.map((item, idx) => (
            <View key={item.id} className={`group-chip variant-${item.variant} ${activeItemId === item.id ? 'is-item-active' : ''}`}>
              <Text className='chip-type'>{VARIANT_LABEL[item.variant]}</Text>
              <Text className='chip-sep'>·</Text>
              <Text className='chip-title' numberOfLines={1}>{item.title}</Text>
              {idx < items.length - 1 && <Text className='chip-divider'>/</Text>}
            </View>
          ))}
        </View>
        <View className={`group-chevron ${isExpanded ? 'is-open' : ''}`}>
          <LucideIcon name='chevron-right' size={14} color='var(--reader-muted)' />
        </View>
      </View>

      <View className={`group-body ${isExpanded ? 'show' : 'hide'}`}>
        <View className='group-items'>
          {items.map(item => (
            <View
              key={item.id}
              className={`group-item ${activeItemId === item.id ? 'is-active' : ''}`}
              onClick={() => handleItemToggle(item.id)}
            >
              <View className='item-label-row'>
                <Text className='item-variant'>{VARIANT_LABEL[item.variant]}</Text>
                <Text className='item-sep'>·</Text>
                <Text className='item-title'>{item.title}</Text>
                <View className={`item-chevron ${activeItemId === item.id ? 'is-open' : ''}`}>
                  <LucideIcon name='chevron-down' size={12} color='var(--reader-subtle)' />
                </View>
              </View>
              <View className={`item-content ${activeItemId === item.id ? 'show' : 'hide'}`}>
                <View className='item-text-container'>
                  <Text className='item-text'>{item.content}</Text>
                </View>
              </View>
            </View>
          ))}
        </View>
      </View>
    </View>
  )
}

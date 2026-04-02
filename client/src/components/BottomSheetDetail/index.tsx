import { View, Text, ScrollView } from '@tarojs/components'
import { SentenceEntryModel } from '../../types/render-scene'
import { parseMarkdown } from '../../utils/parseMarkdown'
import LucideIcon from '../LucideIcon'
import './index.scss'

interface BottomSheetDetailProps {
  visible: boolean
  entry: SentenceEntryModel | null
  onClose: () => void
}

/**
 * 渲染 Markdown 内容片段
 */
function renderMarkdownSegment(segment: ReturnType<typeof parseMarkdown>[number], index: number) {
  const { text, bold, italic, code, list, quote, header } = segment

  // Extract base classes
  const classes = []
  if (quote) classes.push('quote-segment')
  if (header) classes.push('header-segment')

  const style: Record<string, string> = {}
  if (bold) style.fontWeight = 'bold'
  if (italic) style.fontStyle = 'italic'
  if (code) {
    style.backgroundColor = '#f3f4f6'
    style.padding = '2rpx 8rpx'
    style.borderRadius = '8rpx'
    style.fontFamily = 'var(--font-mono)'
    style.color = '#e11d48'
  }

  // For spacing, if it's the end of a line (we inserted \n in the parser)
  // Or handle line breaks natively
  return (
    <Text
      key={index}
      className={classes.join(' ')}
      style={Object.keys(style).length > 0 ? style : undefined}
    >
      {text}{list && text.trim() ? '\n' : ''}
    </Text>
  )
}

export default function BottomSheetDetail({ visible, entry, onClose }: BottomSheetDetailProps) {
  if (!visible || !entry) return null

  const contentSegments = parseMarkdown(entry.content)

  return (
    <View className='bottom-sheet-overlay' onClick={onClose}>
      <View className='bottom-sheet-container' onClick={(e) => e.stopPropagation()}>
        <View className='sheet-drag-handle' />
        <View className='sheet-header'>
          <View className='header-left'>
            <Text className='sheet-title'>{entry.title || entry.label}</Text>
            {entry.label && <Text className='sheet-type-tag'>{entry.label}</Text>}
          </View>
          <View className='sheet-close-btn' onClick={onClose}>
            <LucideIcon name='x' size={24} color='var(--text-muted)' />
          </View>
        </View>

        <ScrollView className='sheet-scroll-content' scrollY>
          <View className='markdown-body'>
            {contentSegments.map(renderMarkdownSegment)}
          </View>
        </ScrollView>

        <View className='sheet-footer-actions safe-area-bottom'>
          <View className='footer-action-btn secondary'>
            <LucideIcon name='star' size={18} color='var(--text-sub)' />
            <Text className='btn-text'>收藏此项</Text>
          </View>
          <View className='footer-action-btn primary'>
            <LucideIcon name='thumbsUp' size={18} color='#fff' />
            <Text className='btn-text'>非常有帮助</Text>
          </View>
        </View>
      </View>
    </View>
  )
}

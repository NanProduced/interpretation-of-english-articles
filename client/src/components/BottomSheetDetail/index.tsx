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
        <View className='sheet-header'>
          <View className='drag-handle' />
          <View className='header-content'>
            <Text className='sheet-title'>{entry.title || entry.label}</Text>
            <View className='close-btn' onClick={onClose}>
              <LucideIcon name='x' size={20} color='#666' />
            </View>
          </View>
        </View>

        <ScrollView className='sheet-content' scrollY>
          <Text className='content-text'>
            {contentSegments.map(renderMarkdownSegment)}
          </Text>
        </ScrollView>

        <View className='sheet-footer'>
          <View className='footer-btn'>
            <LucideIcon name='bookmark' size={16} color='#666' />
            <Text>收藏</Text>
          </View>
          <View className='footer-btn primary'>
            <LucideIcon name='thumbsUp' size={16} color='#fff' />
            <Text>有帮助</Text>
          </View>
        </View>
      </View>
    </View>
  )
}

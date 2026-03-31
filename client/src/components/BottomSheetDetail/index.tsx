import { View, Text, ScrollView } from '@tarojs/components'
import { SentenceTailEntryModel } from '../../types/v2-render'
import { parseMarkdown } from '../../utils/parseMarkdown'
import LucideIcon from '../LucideIcon'
import './index.scss'

interface BottomSheetDetailProps {
  visible: boolean
  entry: SentenceTailEntryModel | null
  onClose: () => void
}

/**
 * 渲染 Markdown 内容片段
 */
function renderMarkdownSegment(segment: ReturnType<typeof parseMarkdown>[number], index: number) {
  const { text, bold, italic, code, list } = segment

  const style: Record<string, string> = {}
  if (bold) style.fontWeight = 'bold'
  if (italic) style.fontStyle = 'italic'
  if (code) {
    style.backgroundColor = '#f3f4f6'
    style.padding = '2rpx 8rpx'
    style.borderRadius = '4rpx'
  }

  return (
    <Text
      key={index}
      style={Object.keys(style).length > 0 ? style : undefined}
    >
      {text}{list ? '\n' : ''}
    </Text>
  )
}

export default function BottomSheetDetail({ visible, entry, onClose }: BottomSheetDetailProps) {
  if (!visible || !entry) return null

  // content 必填，直接解析
  const contentSegments = parseMarkdown(entry.content)

  return (
    <View className='bottom-sheet-overlay' onClick={onClose}>
      <View className='bottom-sheet-container' onClick={(e) => e.stopPropagation()}>
        {/* 头部 */}
        <View className='sheet-header'>
          <View className='drag-handle' />
          <View className='header-content'>
            {/* title 存在时使用，否则用 label */}
            <Text className='sheet-title'>{entry.title || entry.label}</Text>
            <View className='close-btn' onClick={onClose}>
              <LucideIcon name='x' size={20} color='#666' />
            </View>
          </View>
        </View>

        {/* 内容 - 从 entry.content 读取，支持 Markdown */}
        <ScrollView className='sheet-content' scrollY>
          <Text className='content-text'>
            {contentSegments.map(renderMarkdownSegment)}
          </Text>
        </ScrollView>

        {/* 底部操作 */}
        <View className='sheet-footer'>
          <View className='footer-btn primary'>
            <LucideIcon name='thumbs-up' size={16} color='#fff' />
            <Text>有帮助</Text>
          </View>
          <View className='footer-btn'>
            <LucideIcon name='bookmark' size={16} color='#666' />
            <Text>收藏</Text>
          </View>
        </View>
      </View>
    </View>
  )
}

import { View, Text } from '@tarojs/components'
import LucideIcon from '../LucideIcon'
import './index.scss'

interface AnalysisCardProps {
  card: any // V2.1 中已弃用 Card 能力，仅保留组件结构
}

/**
 * @deprecated V2.1 已移除卡片能力，本组件仅保留用于兼容旧代码或未来扩展
 */
export default function AnalysisCard({ card }: AnalysisCardProps) {
  if (!card) return null

  return (
    <View className='analysis-card'>
      <View className='card-header'>
        <LucideIcon name='info' size={16} color='#4285f4' />
        <Text className='card-title'>{card.title}</Text>
      </View>
      <View className='card-content'>
        <Text className='content-text'>{card.content}</Text>
      </View>
    </View>
  )
}

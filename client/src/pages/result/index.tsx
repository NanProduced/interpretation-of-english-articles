import { View, Text, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useArticleStore } from '../../stores/article'
import './index.scss'

export default function Result() {
  const { isLoading, currentAnalysis } = useArticleStore()

  const handleBack = () => {
    Taro.navigateBack()
  }

  return (
    <View className='result-container'>
      <View className='loading-state'>
        <Text className='status-text'>
          {isLoading ? 'AI 正在深度解析文章结构...' : '等待解析结果...'}
        </Text>
        <Text className='tip'>解析长文通常需要 30-60 秒，请稍候</Text>
      </View>

      <View className='action-bar'>
        <Button className='back-btn' onClick={handleBack}>
          返回修改内容
        </Button>
      </View>
    </View>
  )
}

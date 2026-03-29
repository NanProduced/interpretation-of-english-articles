import { View, Text, Button, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import './index.scss'

export default function Home() {
  const navigateToInput = () => {
    Taro.navigateTo({ url: '/pages/input/index' })
  }

  const navigateToHistory = () => {
    Taro.navigateTo({ url: '/pages/history/index' })
  }

  // 模拟每日推荐文章数据
  const dailyRecommendations = [
    { id: 1, title: 'The Future of AI in Education', summary: 'How artificial intelligence is reshaping the way we learn...' },
    { id: 2, title: 'Sustainable Living: A Practical Guide', summary: 'Simple steps to reduce your carbon footprint...' }
  ]

  return (
    <View className='home-container'>
      <View className='header'>
        <Text className='title'>AI 英语解读</Text>
        <Text className='subtitle'>深度解读英文文章，教你读懂英语</Text>
      </View>

      <View className='action-area'>
        <Button className='primary-btn' onClick={navigateToInput}>
          <Text>开始解读新文章</Text>
        </Button>
      </View>

      <View className='section-title'>
        <Text>每日推荐</Text>
      </View>

      <ScrollView scrollY className='recommendation-list'>
        {dailyRecommendations.map(item => (
          <View key={item.id} className='recommendation-card'>
            <Text className='card-title'>{item.title}</Text>
            <Text className='card-summary'>{item.summary}</Text>
          </View>
        ))}
      </ScrollView>

      <View className='footer'>
        <Button className='secondary-btn' onClick={navigateToHistory}>
          <Text>查看历史记录</Text>
        </Button>
      </View>
    </View>
  )
}

import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import './index.scss'

export default function HistoryPage() {
  const historyList = [
    {
      id: "1",
      title: "Why We Sleep: The New Science of Sleep and Dreams",
      date: "今天 10:24",
      config: "CET-4",
    },
    {
      id: "2",
      title: "How to Build a Startup: The Y Combinator Method",
      date: "昨天 15:30",
      config: "考研",
    }
  ]

  const goToResult = () => {
    Taro.navigateTo({ url: '/pages/result/index' })
  }

  return (
    <View className='history-page'>
      <View className='header'>
        <Text className='title'>历史解读</Text>
      </View>

      <ScrollView scrollY className='list-area'>
        {historyList.map(item => (
          <View key={item.id} className='history-card' onClick={() => goToResult()}>
            <View className='card-header'>
              <Text className='item-title'>{item.title}</Text>
            </View>
            <View className='item-footer'>
              <Text className='date-text'>{item.date}</Text>
              <Text className='config-tag'>{item.config}</Text>
            </View>
          </View>
        ))}

        {historyList.length === 0 && (
          <View className='empty-state'>
            <Text className='empty-text'>暂无解读记录</Text>
            <Text className='empty-sub'>去首页贴一篇文章试试吧</Text>
          </View>
        )}
      </ScrollView>
    </View>
  )
}

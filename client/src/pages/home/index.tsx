import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import NavBar from '../../components/NavBar'
import TabBar from '../../components/TabBar'
import LucideIcon from '../../components/LucideIcon'
import { useLayoutStore } from '../../stores/layout'
import './index.scss'

export default function Home() {
  const { navBarHeight } = useLayoutStore()
  
  const navigateToInput = () => {
    Taro.navigateTo({ url: '/pages/input/index' })
  }

  // 动态问候语
  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return '早上好'
    if (hour < 18) return '下午好'
    return '晚上好'
  }

  const recommendations = [
    {
      id: "1",
      title: "Why We Sleep: The New Science of Sleep and Dreams",
      source: "Scientific American",
      difficulty: "CET-6",
      readTime: "5 min",
      cover: "https://images.unsplash.com/photo-1541480601022-2308c0f02487?q=80&w=400&auto=format&fit=crop",
      type: "blue"
    },
    {
      id: "2",
      title: "The Great Resignation: How Employers Drive Away Their Best People",
      source: "HBR",
      difficulty: "IELTS",
      readTime: "8 min",
      cover: "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=400&auto=format&fit=crop",
      type: "orange"
    },
    {
      id: "3",
      title: "A Brief History of Time",
      source: "Wikipedia",
      difficulty: "GRE",
      readTime: "12 min",
      cover: "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=400&auto=format&fit=crop",
      type: "purple"
    }
  ];

  return (
    <View className='home-page'>
      <NavBar title='Interpret' />
      <View className='nav-placeholder' style={{ height: navBarHeight + 'px' }} />
      
      <ScrollView scrollY className='recommendation-list' enhanced showScrollbar={false}>
        <View className='header-section'>
          <View className='greeting-row'>
            <Text className='greeting'>{getGreeting()}</Text>
            <View className='user-avatar' />
          </View>
          <Text className='sub-greeting'>准备好开启今天的深度阅读了吗？</Text>
        </View>

        {/* 重构：极简解读入口 */}
        <View className='interpretation-trigger' onClick={navigateToInput}>
          <View className='trigger-inner'>
            <LucideIcon name='pen-tool' size={20} color='var(--text-muted)' />
            <Text className='trigger-placeholder'>粘贴文章，开启深度解析...</Text>
            <View className='trigger-action'>
              <Text>开始</Text>
            </View>
          </View>
        </View>

        <View className='section-header'>
          <Text className='section-title'>每日精选</Text>
          <Text className='section-more'>更多</Text>
        </View>

        <View className='feed-content'>
          {recommendations.map((item) => (
            <View key={item.id} className='feed-card' onClick={() => {}} role='button'>
              <View className='card-cover-box'>
                <View className='card-cover' style={{ backgroundImage: `url(${item.cover})` }} />
                <View className='card-badge'>{item.difficulty}</View>
              </View>
              <View className='card-info'>
                <Text className='item-title'>{item.title}</Text>
                <View className='item-meta'>
                  <Text className='meta-text'>{item.source}</Text>
                  <View className='meta-dot' />
                  <Text className='meta-text'>{item.readTime}</Text>
                </View>
              </View>
            </View>
          ))}
        </View>
        <View className='list-footer' />
      </ScrollView>

      <TabBar current='home' />
    </View>
  )
}

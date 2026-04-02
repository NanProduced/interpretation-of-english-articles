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

  const navigateToV2Experiment = () => {
    Taro.navigateTo({ url: '/pages/result/index' })
  }

  const recommendations = [
    {
      id: "1",
      title: "Why We Sleep: The New Science of Sleep and Dreams",
      source: "Scientific American",
      difficulty: "CET-6",
      readTime: "5 min",
      tags: ["Science", "Health"],
      type: "blue"
    },
    {
      id: "2",
      title: "The Great Resignation: How Employers Drive Away Their Best People",
      source: "Harvard Business Review",
      difficulty: "IELTS",
      readTime: "8 min",
      tags: ["Business", "Workplace"],
      type: "orange"
    },
    {
      id: "3",
      title: "A Brief History of Time",
      source: "Wikipedia",
      difficulty: "考研",
      readTime: "12 min",
      tags: ["Physics", "History"],
      type: "purple"
    }
  ];

  return (
    <View className='home-page'>
      <NavBar title='AI 英语解读' />
      <View className='nav-placeholder' style={{ height: navBarHeight + 'px' }} />
      
      <ScrollView scrollY className='recommendation-list'>
        <View className='header'>
          <Text className='greeting'>早上好</Text>
          <Text className='sub-greeting'>今天想读点什么？</Text>
        </View>

        <View className='main-action' onClick={navigateToInput}>
          <View className='action-card'>
            <View className='icon-box'>
              <LucideIcon name='plus' size={24} color='#fff' />
            </View>
            <View className='text-info'>
              <Text className='action-title'>粘贴文章</Text>
              <Text className='action-desc'>自动解析语法、翻译与生词</Text>
            </View>
          </View>
        </View>

        <View className='section-header'>
          <LucideIcon name='sparkles' size={18} color='#030213' />
          <Text className='section-title'>每日精读推荐</Text>
        </View>

        {/* V2 实验场入口 */}
        <View className='v2-entry-card' onClick={navigateToV2Experiment}>
          <View className='v2-badge'>
            <Text className='v2-badge-text'>V2</Text>
          </View>
          <View className='v2-content'>
            <Text className='v2-title'>实验结果页</Text>
            <Text className='v2-desc'>体验新一代标注渲染组件</Text>
          </View>
          <LucideIcon name='chevronRight' size={18} color='#8b5cf6' />
        </View>

        <View className='list-content'>
          {recommendations.map((item) => (
            <View key={item.id} className={`recommend-card card-${item.type}`}>
              <Text className='item-title'>{item.title}</Text>
              <View className='item-meta'>
                <View className='meta-info'>
                  <Text className='meta-text'>{item.source}</Text>
                  <Text className='meta-tag'>{item.difficulty}</Text>
                </View>
              </View>
              <View className='tag-group'>
                {item.tags.map(tag => (
                  <Text key={tag} className='tag-item'>{tag}</Text>
                ))}
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

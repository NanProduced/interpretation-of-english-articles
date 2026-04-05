import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState, useEffect } from 'react'
import { useConfigStore } from '../../stores/config'
import { getAllRecords, getVocabulary } from '../../services/storage'
import './index.scss'

export default function ProfilePage() {
  const { purpose } = useConfigStore()
  const [articleCount, setArticleCount] = useState(0)
  const [wordCount, setWordCount] = useState(0)

  useEffect(() => {
    const records = getAllRecords()
    setArticleCount(records.length)
    const vocab = getVocabulary()
    setWordCount(vocab.length)
  }, [])

  const purposeMap = {
    'daily': '日常阅读',
    'exam': 'CET-4 备考',
    'academic': '学术/专业'
  }

  const menuGroups = [
    {
      title: "学习管理",
      items: [
        { label: "当前模式配置", value: purposeMap[purpose] || "未设置", icon: 'settings', url: '/pages/onboarding/index', color: 'blue' },
        { label: "我的生词本", value: wordCount > 0 ? `${wordCount}词` : "暂无生词", icon: 'bookmark', color: 'yellow' },
      ]
    },
    {
      title: "关于与合规",
      items: [
        { label: "用户协议与隐私政策", icon: 'file', color: 'gray' },
        { label: "关于我们", icon: 'info', color: 'gray' },
      ]
    }
  ]

  const handleMenuClick = (item) => {
    if (item.url) {
      Taro.navigateTo({ url: item.url })
    }
  }

  return (
    <View className='profile-page'>
      <View className='header'>
        <Text className='title'>我的</Text>
      </View>

      {/* User Card */}
      <View className='user-card'>
        <View className='avatar'>M</View>
        <View className='user-info'>
          <Text className='nickname'>微信用户</Text>
          <Text className='stats'>
            {articleCount > 0 ? `已累计阅读 ${articleCount} 篇文章` : '暂无阅读记录'}
          </Text>
        </View>
      </View>

      <View className='menu-list'>
        {menuGroups.map((group, gIdx) => (
          <View key={gIdx} className='menu-group'>
            <Text className='group-title'>{group.title}</Text>
            <View className='group-box'>
              {group.items.map((item, iIdx) => (
                <View key={iIdx} className='menu-item' onClick={() => handleMenuClick(item)}>
                  <View className='item-left'>
                    <View className={`icon-box ${item.color}`}>
                      <View className={`icon-${item.icon}`} />
                    </View>
                    <Text className='label'>{item.label}</Text>
                  </View>
                  <View className='item-right'>
                    {item.value && <Text className='value-tag'>{item.value}</Text>}
                    <View className='arrow-icon' />
                  </View>
                </View>
              ))}
            </View>
          </View>
        ))}
      </View>

      <View className='version-tag'>
        <Text>AI Reader v1.0.0</Text>
      </View>
    </View>
  )
}

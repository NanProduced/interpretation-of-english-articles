import { useState, useEffect, useCallback } from 'react'
import { Image, Text, View } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import NavBar from '../../components/NavBar'
import TabBar from '../../components/TabBar'
import LucideIcon from '../../components/LucideIcon'
import { useLayoutStore } from '../../stores/layout'
import { useAuthStore } from '../../stores/auth'
import { ensureLoggedIn } from '../../services/auth'
import './index.scss'

const ANONYMOUS_DAILY_TRIAL_LIMIT = 3

function HomeView({ placeholders }: { placeholders: string[] }) {
  const [placeholderIndex, setPlaceholderIndex] = useState(0)
  const { navBarHeight } = useLayoutStore()
  const { isLoggedIn, userInfo } = useAuthStore()

  // 匿名用户试用 banner 状态
  const [guestTrials, setGuestTrials] = useState<number | null>(null)

  useEffect(() => {
    const timer = setInterval(() => {
      setPlaceholderIndex((i) => (i + 1) % placeholders.length)
    }, 3000)

    return () => clearInterval(timer)
  }, [placeholders.length])

  // 获取匿名用户剩余试用次数
  const fetchGuestTrials = useCallback(() => {
    if (isLoggedIn) return
    const anonymousId = Taro.getStorageSync('anonymous_id') as string | undefined
    if (!anonymousId) return

    Taro.request({
      url: `${process.env.TARO_APP_API_BASE || 'http://localhost:8000'}/api/me/quota/anonymous`,
      method: 'GET',
      data: { anonymous_id: anonymousId },
      header: { 'Content-Type': 'application/json' },
    })
      .then((res) => {
        if (res.statusCode === 200 && res.data) {
          setGuestTrials(res.data.remaining_trials)
        }
      })
      .catch(() => {})
  }, [isLoggedIn])

  useEffect(() => {
    fetchGuestTrials()
  }, [fetchGuestTrials])

  useDidShow(() => {
    fetchGuestTrials()
  })

  const getGreetingConfig = () => {
    const hour = new Date().getHours()
    if (hour >= 0 && hour < 5) {
      return { main: '夜深了', sub: '还在挑灯夜读吗？阅读之余也请早点休息。' }
    }
    if (hour >= 5 && hour < 11) {
      return { main: '早上好', sub: '又是元气满满的一天，来读点有深度的内容吧。' }
    }
    if (hour >= 11 && hour < 13) {
      return { main: '中午好', sub: '午间的小憩，也可以是心灵的补给。' }
    }
    if (hour >= 13 && hour < 18) {
      return { main: '下午好', sub: '一杯茶，一段文字，享受此刻的静谧。' }
    }
    return { main: '晚上好', sub: '在忙碌的一天结束前，沉浸在文字的呼吸中。' }
  }

  const greeting = getGreetingConfig()

  // 渲染右上角头像/用户图标
  const renderAvatar = () => {
    if (isLoggedIn) {
      const avatarUrl = userInfo?.avatar_url
      const nickname = userInfo?.nickname || ''
      const initial = nickname ? nickname.charAt(0).toUpperCase() : 'U'

      if (avatarUrl) {
        return (
          <Image
            className='user-avatar-img'
            src={avatarUrl}
            mode='aspectFill'
            onClick={() => Taro.navigateTo({ url: '/pages/profile/index' })}
          />
        )
      }
      return (
        <View
          className='user-avatar logged'
          onClick={() => Taro.navigateTo({ url: '/pages/profile/index' })}
        >
          <Text className='avatar-initial'>{initial}</Text>
        </View>
      )
    }

    // 未登录：显示游客图标
    return (
      <View
        className='user-avatar guest'
        onClick={async () => {
          const result = await ensureLoggedIn()
          if (result.success && result.isFirstLogin) {
            Taro.navigateTo({ url: '/pages/profile/index' })
          }
        }}
      >
        <Text className='avatar-guest-icon'>U</Text>
      </View>
    )
  }

  const recommendations = [
    {
      id: '1',
      title: 'Why We Sleep: The New Science of Sleep and Dreams',
      source: 'Scientific American',
      difficulty: 'CET-6',
      readTime: '5 min',
      cover:
        'https://images.unsplash.com/photo-1541480601022-2308c0f02487?q=80&w=400&auto=format&fit=crop',
    },
    {
      id: '2',
      title: 'The Great Resignation: How Employers Drive Away Their Best People',
      source: 'HBR',
      difficulty: 'IELTS',
      readTime: '8 min',
      cover:
        'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=400&auto=format&fit=crop',
    },
    {
      id: '3',
      title: 'A Brief History of Time',
      source: 'Wikipedia',
      difficulty: 'GRE',
      readTime: '12 min',
      cover:
        'https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=400&auto=format&fit=crop',
    },
  ]

  return (
    <View className='home-page'>
      <NavBar title='Claread透读' />
      <View className='nav-placeholder' style={{ height: `${navBarHeight}px` }} />
      <View className='recommendation-list'>

        {/* 游客试用 Banner */}
        {!isLoggedIn && guestTrials !== null && (
          <View
            className='guest-banner'
            onClick={async () => {
              const result = await ensureLoggedIn()
              if (result.success && result.isFirstLogin) {
                Taro.navigateTo({ url: '/pages/profile/index' })
              }
            }}
          >
            <View className='guest-banner-dot' />
            <Text className='guest-banner-text'>
              剩余 {guestTrials} 次试用
              <Text className='guest-banner-link'> · 登录解锁更多</Text>
            </Text>
          </View>
        )}

        <View className='header-section'>
          <View className='greeting-row'>
            <Text className='greeting'>{greeting.main}</Text>
            {renderAvatar()}
          </View>
          <Text className='sub-greeting'>{greeting.sub}</Text>
        </View>

        <View className='light-portal' onClick={() => Taro.navigateTo({ url: '/pages/input/index' })}>
          <View className='portal-inner'>
            <View className='portal-text-area'>
              <Text className='portal-label'>输入文本</Text>
              <View className='placeholder-wrapper'>
                <Text className='well-placeholder' key={placeholderIndex}>
                  {placeholders[placeholderIndex]}
                </Text>
                <View className='typing-cursor' />
              </View>
            </View>
            <View className='portal-action-btn'>
              <LucideIcon name='plus' size={24} color='#fff' />
            </View>
          </View>
        </View>

        <View className='section-header'>
          <Text className='section-title'>每日精选</Text>
          <Text className='section-more'>更多</Text>
        </View>

        <View className='feed-content'>
          {recommendations.map((item) => (
            <View key={item.id} className='feed-card'>
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
      </View>
      <TabBar current='home' />
    </View>
  )
}

export default function Home() {
  const placeholders = [
    '粘贴一段《经济学人》社论...',
    '粘贴你的 GRE 阅读真题...',
    '导入一段雅思大作文练习...',
    '粘贴今日份的纽约时报摘要...',
  ]

  return <HomeView placeholders={placeholders} />
}

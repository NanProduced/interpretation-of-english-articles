import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import LucideIcon from '../LucideIcon'
import './index.scss'

interface TabBarProps {
  current: string;
}

export default function TabBar({ current }: TabBarProps) {
  const tabs = [
    { key: 'home', text: '首页', icon: 'home' as const, path: '/pages/home/index' },
    { key: 'history', text: '记录', icon: 'history' as const, path: '/pages/history/index' },
    { key: 'profile', text: '我的', icon: 'user' as const, path: '/pages/profile/index' },
  ]

  const switchTab = (path: string) => {
    Taro.reLaunch({ url: path })
  }

  return (
    <View className='custom-tabbar-container safe-area-bottom' role='tablist'>
      {tabs.map(tab => {
        const isActive = current === tab.key
        return (
          <View 
            key={tab.key} 
            className={`tab-item ${isActive ? 'active' : ''}`}
            onClick={() => switchTab(tab.path)}
            role='tab'
            aria-selected={isActive}
            aria-label={tab.text}
          >
            <LucideIcon 
              name={tab.icon} 
              size={22} 
              color={isActive ? 'var(--color-ink)' : 'var(--text-sub)'} 
              strokeWidth={isActive ? 2.5 : 2} 
            />
            <Text className='tab-text'>{tab.text}</Text>
          </View>
        )
      })}
    </View>
  )
}

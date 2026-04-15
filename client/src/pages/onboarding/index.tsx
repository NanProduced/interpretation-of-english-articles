import { useState, useEffect, useCallback } from 'react'
import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useConfigStore, UserPurpose } from '../../stores/config'
import ConfigEditor from '../../components/ConfigEditor'
import './index.scss'

export default function Onboarding() {
  const router = Taro.useRouter()
  const [isReady, setIsReady] = useState(false)
  const { purpose, setPurpose, level, setLevel } = useConfigStore()

  const skip = useCallback(() => {
    Taro.setStorageSync('user_configured', true)
    Taro.reLaunch({ url: '/pages/home/index' })
  }, [])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        skip()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [skip])

  useEffect(() => {
    const fromProfile = router.params.from === 'profile'
    const hasConfig = Taro.getStorageSync('user_configured')
    
    if (hasConfig && !fromProfile) {
      Taro.reLaunch({ url: '/pages/home/index' })
      return
    }
    setIsReady(true)
  }, [router.params.from])

  const finishOnboarding = (selectedPurpose: UserPurpose, selectedLevel: string | null) => {
    setPurpose(selectedPurpose)
    setLevel(selectedLevel)
    Taro.setStorageSync('user_configured', true)
    
    Taro.showToast({ title: '配置已更新', icon: 'success', duration: 1000 })
    setTimeout(() => {
      Taro.reLaunch({ url: '/pages/home/index' })
    }, 1000)
  }

  if (!isReady) return null

  return (
    <View className='onboarding-page fade-in'>
      {/* Header */}
      <View className='header-nav'>
        <View className='nav-left'>
          <Text className='brand-motto'>Claread 透读</Text>
        </View>
        <Text className='skip-btn' onClick={skip}>跳过</Text>
      </View>

      <View className='content-area'>
        <ConfigEditor 
          mode='detailed'
          initialGoal={purpose as UserPurpose}
          initialLevel={level}
          showSubmit
          submitText='开始体验'
          onComplete={(g, l) => finishOnboarding(g as UserPurpose, l)}
        />
      </View>
    </View>
  )
}

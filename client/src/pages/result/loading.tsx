import { useEffect, useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import './index.scss'

export default function LoadingPage() {
  const [step, setStep] = useState(0)

  const steps = [
    { text: "正在扫描文章词汇...", icon: 'book' },
    { text: "正在拆解长难句...", icon: 'layer' },
    { text: "生成中英文对照...", icon: 'brain' },
    { text: "提取篇章结构...", icon: 'sparkle' }
  ]

  useEffect(() => {
    const timer1 = setTimeout(() => setStep(1), 1500)
    const timer2 = setTimeout(() => setStep(2), 3000)
    const timer3 = setTimeout(() => setStep(3), 4500)
    const timer4 = setTimeout(() => Taro.redirectTo({ url: '/pages/result/index' }), 6000)

    return () => {
      clearTimeout(timer1)
      clearTimeout(timer2)
      clearTimeout(timer3)
      clearTimeout(timer4)
    }
  }, [])

  return (
    <View className='loading-page'>
      {/* Background Decor */}
      <View className='bg-decor'>
        <View className='blur-circle blue' />
        <View className='blur-circle purple' />
      </View>

      <View className='loader-content'>
        <View className='main-spinner'>
          <View className='spinner-outer' />
          <View className='spinner-inner' />
          <View className='sparkle-icon' />
        </View>

        <View className='status-switcher'>
          <View className='status-item fade-in-up' key={step}>
            <View className={`icon-${steps[step].icon}`} />
            <Text className='status-text'>{steps[step].text}</Text>
          </View>
        </View>

        <View className='progress-bar-container'>
          <View 
            className='progress-fill' 
            style={{ width: `${((step + 1) / steps.length) * 100}%` }} 
          />
        </View>

        <Text className='gen-tag'>AI GENERATING...</Text>
      </View>
    </View>
  )
}

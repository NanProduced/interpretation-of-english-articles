import { useState, useEffect } from 'react'
import { View, Text } from '@tarojs/components'
import clareadLoadingAnimation from '../../assets/animations/claread-loading'
import LottieAnimation from '../LottieAnimation'
import './index.scss'

const LOADING_STEPS = [
  '正在构建文章骨架...',
  '深度解析复杂语法...',
  '智能提取核心词汇...',
  '注入语境解读语义...',
  '最后打磨排版细节...'
]

export default function ActiveLoading() {
  const [step, setStep] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setStep((s) => (s + 1) % LOADING_STEPS.length)
    }, 2800)
    return () => clearInterval(timer)
  }, [])

  return (
    <View className='active-loading-container'>
      {/* 背景装饰线 */}
      <View className='ambient-bg'>
        <View className='bg-line line-1' />
        <View className='bg-line line-2' />
        <View className='bg-line line-3' />
      </View>

      <View className='loading-content'>
        {/* Lottie 动画区域 */}
        <View className='lottie-wrapper'>
          <LottieAnimation
            className='analysis-lottie'
            animationData={clareadLoadingAnimation}
            loop={true}
            autoplay={true}
            fallback={
              <View className='lottie-fallback'>
                <View className='fallback-ring' />
              </View>
            }
          />
        </View>

        {/* 状态文案 */}
        <View className='status-panel'>
          <Text className='step-label'>Step 0{step + 1}</Text>
          <Text className='step-text'>{LOADING_STEPS[step]}</Text>
        </View>
      </View>

      <View className='loading-footer'>
        <Text className='footer-text'>AI 深度解析中 · 喝杯咖啡稍候</Text>
      </View>
    </View>
  )
}

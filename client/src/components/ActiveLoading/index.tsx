import { useState, useEffect } from 'react'
import { View, Text } from '@tarojs/components'
import './index.scss'

const LOADING_KEYWORDS = [
  'STRUCTURE',
  'SYNTAX',
  'VOCABULARY',
  'CONTEXT',
  'INSIGHTS'
]

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
      setStep((s) => (s + 1) % LOADING_KEYWORDS.length)
    }, 2800)
    return () => clearInterval(timer)
  }, [])

  return (
    <View className='active-loading-container'>
      {/* 背景抽象装饰线 */}
      <View className='abstract-bg'>
        <View className='bg-line line-1' />
        <View className='bg-line line-2' />
        <View className='bg-line line-3' />
      </View>

      <View className='loading-main'>
        {/* 中心品牌字母脉冲 */}
        <View className='brand-pulse'>
          <Text className='brand-char'>C</Text>
          <View className='pulse-ring' />
        </View>

        {/* 抽象排版层 */}
        <View className='typography-layer'>
          <View className='keyword-wrapper'>
            {LOADING_KEYWORDS.map((kw, i) => (
              <Text 
                key={kw} 
                className={`keyword ${i === step ? 'active' : ''}`}
              >
                {kw}
              </Text>
            ))}
          </View>
          
          <View className='step-message-wrapper'>
            <Text className='step-label'>Step 0{step + 1}</Text>
            <Text className='step-text'>{LOADING_STEPS[step]}</Text>
          </View>
        </View>

        {/* 动态扫描光带 */}
        <View className='glimmer-bar' />
      </View>

      <View className='loading-footer'>
        <Text className='footer-text'>AI 深度解析中 · 喝杯咖啡稍候</Text>
      </View>
    </View>
  )
}

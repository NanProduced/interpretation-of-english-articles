import { useState, useEffect } from 'react'
import { View, Text, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useConfigStore, UserPurpose } from '../../stores/config'
import './index.scss'

export default function Onboarding() {
  const [step, setStep] = useState<1 | 2>(1)
  const { purpose, setPurpose, level, setLevel } = useConfigStore()

  // 记忆逻辑：如果已有配置且不是从 Profile 进来（此处简化判断），直达首页
  useEffect(() => {
    const hasConfig = Taro.getStorageSync('user_configured')
    if (hasConfig) {
      Taro.reLaunch({ url: '/pages/home/index' })
    }
  }, [])

  const handleNext = () => {
    if (step === 1) {
      if (purpose === 'academic') {
        finishOnboarding()
      } else {
        setStep(2)
      }
    } else {
      finishOnboarding()
    }
  }

  const finishOnboarding = () => {
    Taro.setStorageSync('user_configured', true)
    Taro.reLaunch({ url: '/pages/home/index' })
  }

  const skip = () => {
    finishOnboarding()
  }

  const purposes = [
    { id: 'exam', title: '考试备考', desc: '四六级、考研、雅思托福等', icon: 'book' },
    { id: 'daily', title: '日常阅读提升', desc: '新闻、博客、小说等外刊', icon: 'coffee' },
    { id: 'academic', title: '学术/专业阅读', desc: '论文、行业报告、技术文档', icon: 'grad' },
  ]

  const levelsMap: Record<string, { id: string; label: string }[]> = {
    exam: [
      { id: 'gaokao', label: '高考英语' },
      { id: 'cet4', label: 'CET-4 四级' },
      { id: 'cet6', label: 'CET-6 六级' },
      { id: 'kaoyan', label: '考研英语' },
      { id: 'ielts', label: '雅思 IELTS' },
      { id: 'toefl', label: '托福 TOEFL' },
    ],
    daily: [
      { id: 'beginner', label: '刚开始读英文文章' },
      { id: 'intermediate', label: '能读大部分但有些词不认识' },
      { id: 'advanced', label: '想精读提升，攻克长难句' },
    ],
  }

  return (
    <View className='onboarding-page'>
      {/* Header */}
      <View className='header-nav'>
        {step === 2 ? (
          <View className='back-btn' onClick={() => setStep(1)} />
        ) : <View className='empty-spacer' />}
        
        <View className='progress-dots'>
          <View className={`dot ${step === 1 ? 'active' : ''}`} />
          <View className={`dot ${step === 2 ? 'active' : ''}`} />
        </View>

        <Text className='skip-btn' onClick={skip}>跳过</Text>
      </View>

      <View className='content-area'>
        {step === 1 ? (
          <View className='step-box fade-in'>
            <View className='title-section'>
              <Text className='main-title'>你主要用它来读什么？</Text>
              <Text className='sub-title'>我们会根据你的目的，自动调整 AI 的解读重点</Text>
            </View>

            <View className='option-list'>
              {purposes.map((p) => {
                const isSelected = purpose === p.id
                return (
                  <View
                    key={p.id}
                    className={`option-card ${isSelected ? 'selected' : ''}`}
                    onClick={() => setPurpose(p.id as UserPurpose)}
                  >
                    <View className='icon-circle'>
                      <View className={`icon-${p.icon}`} />
                    </View>
                    <View className='text-group'>
                      <Text className='card-title'>{p.title}</Text>
                      <Text className='card-desc'>{p.desc}</Text>
                    </View>
                  </View>
                )
              })}
            </View>
          </View>
        ) : (
          <View className='step-box fade-in'>
            <View className='title-section'>
              <Text className='main-title'>
                {purpose === 'exam' ? '你的备考目标是？' : '你的当前水平大概在？'}
              </Text>
              <Text className='sub-title'>帮助 AI 更精准地为你过滤掉太简单的单词</Text>
            </View>

            <View className='level-list'>
              {(purpose && purpose !== 'academic' ? levelsMap[purpose] : []).map((l) => {
                const isSelected = level === l.id
                return (
                  <View
                    key={l.id}
                    className={`level-item ${isSelected ? 'selected' : ''}`}
                    onClick={() => setLevel(l.id)}
                  >
                    <Text className='level-label'>{l.label}</Text>
                  </View>
                )
              })}
            </View>
          </View>
        )}
      </View>

      {/* Footer */}
      <View className='footer-area safe-area-bottom'>
        <Button
          className={`next-btn ${(step === 1 && !purpose) || (step === 2 && !level) ? 'disabled' : ''}`}
          onClick={handleNext}
        >
          <Text>{step === 1 && purpose !== 'academic' ? '下一步' : '开始体验'}</Text>
          <View className='arrow-icon' />
        </Button>
      </View>
    </View>
  )
}

import { useState } from 'react'
import { View, Text, Textarea, Switch } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useConfigStore } from '../../stores/config'
import './index.scss'

export default function InputPage() {
  const [content, setContent] = useState('')
  const [isPaidEnabled, setIsPaidEnabled] = useState(false)
  const { purpose } = useConfigStore()

  // 简单的单词计数（按空格拆分）
  const wordsCount = content.trim().split(/\s+/).filter(Boolean).length

  const handleBack = () => {
    Taro.navigateBack()
  }

  const navigateToProfile = () => {
    Taro.navigateTo({ url: '/pages/profile/index' })
  }

  const handleSubmit = () => {
    if (wordsCount < 10) {
      Taro.showToast({ title: '最少输入10个单词', icon: 'none' })
      return
    }
    Taro.navigateTo({ url: '/pages/result/loading' })
  }

  // 映射目的到显示文本
  const purposeMap = {
    'daily': '日常阅读提升',
    'exam': 'CET/IELTS 备考',
    'academic': '学术/专业文献'
  }

  return (
    <View className='input-page'>
      {/* Header */}
      <View className='header-bar'>
        <View className='back-btn' onClick={handleBack} />
        <Text className='page-title'>输入文章</Text>
        <View className='settings-btn' onClick={navigateToProfile} />
      </View>

      {/* Configuration Status */}
      <View className='config-status' onClick={navigateToProfile}>
        <View className='status-left'>
          <View className='sparkle-icon-box'>
            <View className='sparkle-icon' />
          </View>
          <View className='status-info'>
            <Text className='status-label'>当前解读模式</Text>
            <Text className='status-value'>{purposeMap[purpose] || '日常阅读'}</Text>
          </View>
        </View>
        <Text className='edit-btn'>修改</Text>
      </View>

      {/* Input Area */}
      <View className='scroll-input-area'>
        <Textarea
          className='content-textarea'
          placeholder='在此粘贴或输入英文文章内容...'
          maxlength={5000}
          value={content}
          onInput={(e) => setContent(e.detail.value)}
          autoHeight
        />
      </View>

      {/* Bottom Actions */}
      <View className='bottom-panel safe-area-bottom'>
        <View className='paid-toggle'>
          <View className='toggle-label'>
            <View className='diamond-icon' />
            <Text className='toggle-text'>开启深度篇章分析</Text>
          </View>
          <Switch 
            color='#9333ea' 
            checked={isPaidEnabled} 
            onChange={(e) => setIsPaidEnabled(e.detail.value)}
          />
        </View>

        <View className='action-row'>
          <View className='stats-info'>
            <Text className={`word-count ${wordsCount > 0 ? 'active' : ''}`}>
              {wordsCount} words
            </Text>
            {wordsCount > 0 && wordsCount < 10 && (
              <View className='error-tip'>
                <View className='alert-icon' />
                <Text className='error-text'>最少输入10个单词</Text>
              </View>
            )}
          </View>

          <View 
            className={`submit-btn ${wordsCount >= 10 ? '' : 'disabled'}`}
            onClick={handleSubmit}
          >
            <Text className='btn-text'>解读</Text>
            <View className='arrow-icon' />
          </View>
        </View>
      </View>
    </View>
  )
}

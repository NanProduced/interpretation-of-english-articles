import { useState, useEffect } from 'react'
import { View, Text, Textarea, Switch } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useConfigStore } from '../../stores/config'
import { useArticleStore } from '../../stores/article'
import { saveDraft, getDraft, clearDraft } from '../../services/storage'
import { track } from '../../services/analytics'
import './index.scss'

/** 目的 -> API 参数映射 */
function mapPurposeToApiParams(purpose: 'exam' | 'academic' | 'daily'): {
  reading_goal: 'exam' | 'daily_reading' | 'academic'
  reading_variant: 'gaokao' | 'cet' | 'gre' | 'ielts_toefl' | 'beginner_reading' | 'intermediate_reading' | 'intensive_reading' | 'academic_general'
} {
  switch (purpose) {
    case 'exam':
      return { reading_goal: 'exam', reading_variant: 'cet' }
    case 'academic':
      return { reading_goal: 'academic', reading_variant: 'academic_general' }
    case 'daily':
    default:
      return { reading_goal: 'daily_reading', reading_variant: 'intermediate_reading' }
  }
}

export default function InputPage() {
  const [content, setContent] = useState('')
  const [isPaidEnabled, setIsPaidEnabled] = useState(false)
  const [clipboardContent, setClipboardContent] = useState('')
  const [showClipboardToast, setShowClipboardToast] = useState(false)
  const { purpose } = useConfigStore()
  const analyze = useArticleStore((s) => s.analyze)

  // 简单的单词计数（按空格拆分）
  const wordsCount = content.trim().split(/\s+/).filter(Boolean).length

  // === 剪贴板检测逻辑 ===
  const checkClipboard = async () => {
    try {
      const res = await Taro.getClipboardData()
      const text = res.data?.trim() || ''
      
      // 判定逻辑：长度 > 20 且 包含英文字符 且 与当前内容不同
      const isEnglish = /[a-zA-Z]{5,}/.test(text)
      if (text.length > 20 && isEnglish && text !== content) {
        setClipboardContent(text)
        setShowClipboardToast(true)
        // 3秒后自动消失
        setTimeout(() => setShowClipboardToast(false), 5000)
      }
    } catch (e) {
      console.error('Clipboard access failed', e)
    }
  }

  // === 草稿恢复 onMount ===
  useEffect(() => {
    const draft = getDraft()
    if (draft && draft.text) {
      setContent(draft.text)
    }
    
    // 首次进入检测剪贴板
    setTimeout(checkClipboard, 500)
  }, [])

  // === 监听切回前台 ===
  Taro.useDidShow(() => {
    checkClipboard()
  })

  // === 防抖保存草稿 ===
  useEffect(() => {
    if (!content) return
    const timer = setTimeout(() => {
      saveDraft({
        text: content,
        reading_goal: mapPurposeToApiParams(purpose).reading_goal,
        reading_variant: mapPurposeToApiParams(purpose).reading_variant,
        savedAt: Date.now(),
      })
    }, 500)
    return () => clearTimeout(timer)
  }, [content, purpose])

  const handleBack = () => {
    if (content.trim().length > 0) {
      Taro.showModal({
        title: '离开',
        content: '当前输入内容已自动保存，可在首页继续编辑',
        confirmText: '离开',
        cancelText: '继续编辑',
        success: (res) => {
          if (res.confirm) {
            Taro.navigateBack()
          }
        },
      })
    } else {
      Taro.navigateBack()
    }
  }

  const navigateToProfile = () => {
    Taro.navigateTo({ url: '/pages/profile/index' })
  }

  const handleSubmit = () => {
    if (wordsCount < 10) {
      Taro.showToast({ title: '最少输入10个单词', icon: 'none' })
      return
    }

    const { reading_goal, reading_variant } = mapPurposeToApiParams(purpose)

    track('submit_article', { wordCount: wordsCount, reading_goal, reading_variant })

    // 先跳结果页，再发请求（结果页承接 loading 态）
    clearDraft()
    analyze({
      text: content,
      reading_goal,
      reading_variant,
      source_type: 'user_input',
      extended: isPaidEnabled,
    })
    Taro.navigateTo({ url: '/pages/result/index' })
  }

  // 映射目的到显示文本
  const purposeMap = {
    'daily': '日常阅读提升',
    'exam': 'CET/IELTS 备考',
    'academic': '学术/专业文献'
  }

  return (
    <View className='input-page'>
      {/* Clipboard Toast */}
      {showClipboardToast && (
        <View className='clipboard-toast'>
          <View className='toast-left'>
            <View className='copy-icon' />
            <Text className='toast-text'>检测到复制的英文内容</Text>
          </View>
          <View 
            className='toast-action' 
            onClick={() => {
              setContent(clipboardContent)
              setShowClipboardToast(false)
              Taro.showToast({ title: '已粘贴', icon: 'none' })
            }}
          >
            立即粘贴
          </View>
        </View>
      )}

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

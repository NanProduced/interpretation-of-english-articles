import { useState, useEffect } from 'react'
import { View, Text, Textarea, Switch } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useConfigStore } from '../../stores/config'
import { useArticleStore } from '../../stores/article'
import { saveDraft, getDraft, clearDraft } from '../../services/storage'
import { track } from '../../services/analytics'
import LucideIcon from '../../components/LucideIcon'
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
  const [isFocused, setIsFocused] = useState(false)
  const [isPaidEnabled, setIsPaidEnabled] = useState(false)
  const [clipboardContent, setClipboardContent] = useState('')
  const [showClipboardBubble, setShowClipboardBubble] = useState(false)
  const { purpose } = useConfigStore()
  const analyze = useArticleStore((s) => s.analyze)

  // 简单的单词计数
  const wordsCount = content.trim().split(/\s+/).filter(Boolean).length

  // === 剪贴板检测逻辑 ===
  const checkClipboard = async () => {
    try {
      const res = await Taro.getClipboardData()
      const text = res.data?.trim() || ''
      const isEnglish = /[a-zA-Z]{5,}/.test(text)
      if (text.length > 20 && isEnglish && text !== content) {
        setClipboardContent(text)
        setShowClipboardBubble(true)
        setTimeout(() => setShowClipboardBubble(false), 8000)
      }
    } catch (e) {}
  }

  useEffect(() => {
    const draft = getDraft()
    if (draft?.text) setContent(draft.text)
  }, [])

  Taro.useDidShow(() => { checkClipboard() })

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
        content: '草稿已自动保存',
        confirmText: '离开',
        cancelText: '继续',
        success: (res) => { if (res.confirm) Taro.navigateBack() },
      })
    } else {
      Taro.navigateBack()
    }
  }

  const handleSubmit = () => {
    if (wordsCount < 10) {
      Taro.showToast({ title: '最少输入10个单词', icon: 'none' })
      return
    }
    const { reading_goal, reading_variant } = mapPurposeToApiParams(purpose)
    track('submit_article', { wordCount: wordsCount, reading_goal, reading_variant })
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

  const purposeMap = {
    'daily': '日常阅读',
    'exam': '考试备考',
    'academic': '学术文献'
  }

  return (
    <View className={`input-page ${isFocused ? 'is-focused' : ''}`}>
      {/* 1. 精简 Header */}
      <View className='compact-header'>
        <View className='header-left' onClick={handleBack}>
          <LucideIcon name='chevronLeft' size={24} color='var(--color-ink)' />
        </View>
        <Text className='page-title'>Claread透读</Text>
        <View className='header-right'>
          {content ? (
            <View className='clear-btn' onClick={() => setContent('')}>
              <LucideIcon name='eraser' size={20} color='var(--text-muted)' />
            </View>
          ) : (
            <View onClick={() => Taro.navigateTo({ url: '/pages/profile/index' })}>
              <LucideIcon name='settings' size={20} color='var(--text-muted)' />
            </View>
          )}
        </View>
      </View>

      {/* 2. 画布区域 */}
      <View className='canvas-area'>
        {/* 解读模式 Chip */}
        <View className='mode-chip' onClick={() => Taro.navigateTo({ url: '/pages/profile/index' })}>
          <View className='dot' />
          <Text>{purposeMap[purpose] || '日常阅读'}</Text>
        </View>

        <Textarea
          className='content-textarea'
          placeholder='在这里倾倒你感兴趣的英文篇章...'
          placeholderClass='placeholder-style'
          maxlength={10000}
          value={content}
          onInput={(e) => setContent(e.detail.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          autoFocus
          cursorSpacing={100}
        />

        {/* 墨水气泡剪贴板 */}
        {showClipboardBubble && (
          <View className='ink-bubble' onClick={() => {
            setContent(clipboardContent)
            setShowClipboardBubble(false)
            Taro.showToast({ title: '已注入内容', icon: 'none' })
          }}>
            <LucideIcon name='clipboard' size={16} color='#fff' />
            <Text className='bubble-text'>识别到剪贴板，点击注入</Text>
          </View>
        )}
      </View>

      {/* 3. 底部动态统计与操作 */}
      <View className='bottom-bar safe-area-bottom'>
        <View className='bar-top-row'>
          <View className='ink-stats'>
            <View className={`ink-bottle ${wordsCount >= 10 ? 'ready' : ''}`}>
              <View className='ink-level' style={{ height: Math.min(100, (wordsCount / 10) * 100) + '%' }} />
            </View>
            <Text className='stats-text'>{wordsCount} words</Text>
          </View>

          <View className='toggle-group'>
            <Text className='toggle-label'>深度分析</Text>
            <Switch 
              color='var(--color-ink)' 
              checked={isPaidEnabled} 
              onChange={(e) => setIsPaidEnabled(e.detail.value)}
              style={{ transform: 'scale(0.7)' }}
            />
          </View>
        </View>

        <View className={`interpret-btn ${wordsCount >= 10 ? 'active' : ''}`} onClick={handleSubmit}>
          <Text>开启深度解读</Text>
          <LucideIcon name='sparkles' size={18} color='#fff' />
        </View>
      </View>
    </View>
  )
}

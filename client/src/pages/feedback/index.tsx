import { View, Text, Input, Textarea } from '@tarojs/components'
import { useState } from 'react'
import Taro from '@tarojs/taro'
import { submitFeedback, fetchFeedbackList, FeedbackListItem } from '../../services/api/feedback.client'
import './index.scss'

const FEEDBACK_CATEGORIES = [
  { value: 'bug_report', label: 'Bug 报告' },
  { value: 'feature_request', label: '功能建议' },
  { value: 'quota_issue', label: '额度问题' },
  { value: 'input_page_issue', label: '输入页问题' },
  { value: 'ux_issue', label: '体验问题' },
  { value: 'other', label: '其他' },
]

export default function FeedbackPage() {
  const [selectedCategory, setSelectedCategory] = useState('')
  const [content, setContent] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [feedbackCount, setFeedbackCount] = useState<number | null>(null)

  useState(() => {
    fetchFeedbackList({ limit: 1 }).then(res => {
      setFeedbackCount(res.items.length)
    }).catch(() => {})
  })

  const canSubmit = selectedCategory && content.trim()

  const handleSubmit = async () => {
    if (!canSubmit || submitting) return
    setSubmitting(true)
    try {
      await submitFeedback({
        feedbackScope: 'app',
        targetId: selectedCategory,
        sentiment: 'neutral',
        feedbackType: selectedCategory,
        content: content.trim(),
        contextJson: { app_area: selectedCategory },
      })
      Taro.showToast({ title: '感谢反馈', icon: 'success', duration: 1500 })
      setSelectedCategory('')
      setContent('')
    } catch {
      Taro.showToast({ title: '提交失败', icon: 'error', duration: 1500 })
    } finally {
      setSubmitting(false)
    }
  }

  const goToMyFeedback = () => {
    Taro.navigateTo({ url: '/pages/feedback/my-feedback' })
  }

  return (
    <View className='feedback-page'>
      <View className='feedback-page__section'>
        <Text className='feedback-page__section-title'>反馈类型</Text>
        <View className='feedback-page__categories'>
          {FEEDBACK_CATEGORIES.map(cat => (
            <View
              key={cat.value}
              className={`feedback-page__chip ${selectedCategory === cat.value ? 'feedback-page__chip--active' : ''}`}
              onClick={() => setSelectedCategory(cat.value)}
            >
              {cat.label}
            </View>
          ))}
        </View>
      </View>

      <View className='feedback-page__section'>
        <Text className='feedback-page__section-title'>问题描述 *</Text>
        <Textarea
          className='feedback-page__textarea'
          value={content}
          onInput={(e) => setContent(e.detail.value)}
          placeholder='请描述你遇到的问题或建议...'
          maxlength={2000}
          autoHeight
        />
      </View>

      <View
        className={`feedback-page__submit ${!canSubmit ? 'feedback-page__submit--disabled' : ''}`}
        onClick={handleSubmit}
      >
        提交反馈
      </View>

      <View className='feedback-page__divider' />

      <View className='feedback-page__my-feedback' onClick={goToMyFeedback}>
        <Text className='feedback-page__my-feedback-label'>📋 我的反馈</Text>
        {feedbackCount !== null && (
          <Text className='feedback-page__my-feedback-count'>({feedbackCount})</Text>
        )}
        <Text className='feedback-page__my-feedback-arrow'>→</Text>
      </View>
    </View>
  )
}

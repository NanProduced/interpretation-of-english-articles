import { View, Text, Textarea } from '@tarojs/components'
import { useState } from 'react'
import { submitFeedback } from '../../services/api/feedback.client'
import { ensureLoggedIn } from '../../services/auth'
import LucideIcon from '../LucideIcon'
import Taro from '@tarojs/taro'
import './index.scss'

const NEGATIVE_OPTIONS = [
  { value: 'translation_inaccurate', label: '翻译不准确' },
  { value: 'too_few_annotations', label: '标注过少' },
  { value: 'too_many_annotations', label: '标注过多' },
  { value: 'wrong_difficulty', label: '难度不匹配' },
  { value: 'other', label: '其他' },
]

interface FeedbackWidgetProps {
  recordId: string
  cloudId?: string
  readingGoal?: string
  readingVariant?: string
  userFacingState?: string
  sourceTextLength?: number
  annotationCount?: Record<string, number>
}

export default function FeedbackWidget({
  recordId,
  cloudId,
  readingGoal,
  readingVariant,
  userFacingState,
  sourceTextLength,
  annotationCount,
}: FeedbackWidgetProps) {
  const [submitted, setSubmitted] = useState<'positive' | 'negative' | null>(null)
  const [showDetail, setShowDetail] = useState(false)
  const [selectedType, setSelectedType] = useState('')
  const [content, setContent] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleThumbsUp = async () => {
    if (submitting || submitted) return
    const loginRes = await ensureLoggedIn()
    if (!loginRes.success) return
    setSubmitting(true)
    try {
      await submitFeedback({
        feedbackScope: 'analysis_result',
        targetId: cloudId || recordId,
        analysisRecordId: cloudId || undefined,
        sentiment: 'positive',
        feedbackType: 'thumbs_up',
        contextJson: { reading_goal: readingGoal, reading_variant: readingVariant, source_text_length: sourceTextLength, annotation_count: annotationCount, user_facing_state: userFacingState },
      })
      setSubmitted('positive')
      Taro.showToast({ title: '感谢反馈', icon: 'success', duration: 1500 })
    } catch {
      Taro.showToast({ title: '提交失败', icon: 'error', duration: 1500 })
    } finally {
      setSubmitting(false)
    }
  }

  const handleThumbsDown = () => {
    if (submitted) return
    setShowDetail(true)
  }

  const handleSubmitNegative = async () => {
    if (!selectedType || submitting) return
    const loginRes = await ensureLoggedIn()
    if (!loginRes.success) return
    setSubmitting(true)
    try {
      await submitFeedback({
        feedbackScope: 'analysis_result',
        targetId: cloudId || recordId,
        analysisRecordId: cloudId || undefined,
        sentiment: 'negative',
        feedbackType: selectedType,
        content: content || undefined,
        contextJson: { reading_goal: readingGoal, reading_variant: readingVariant, source_text_length: sourceTextLength, annotation_count: annotationCount, user_facing_state: userFacingState },
      })
      setSubmitted('negative')
      setShowDetail(false)
      Taro.showToast({ title: '感谢反馈', icon: 'success', duration: 1500 })
    } catch {
      Taro.showToast({ title: '提交失败', icon: 'error', duration: 1500 })
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <View className='feedback-widget feedback-widget--submitted'>
        <Text className='feedback-widget__label'>
          {submitted === 'positive' ? '感谢认可 🎉' : '感谢反馈，我们会持续改进'}
        </Text>
      </View>
    )
  }

  return (
    <View className='feedback-widget'>
      <Text className='feedback-widget__label'>本次解读对你有帮助吗？</Text>
      <View className='feedback-widget__actions'>
        <View className={`feedback-widget__btn ${submitted === 'positive' ? 'feedback-widget__btn--active' : ''}`} onClick={handleThumbsUp}>
          <LucideIcon name='thumbsUp' size={20} color={submitted === 'positive' ? 'var(--reader-ink)' : 'var(--reader-muted)'} />
        </View>
        <View className={`feedback-widget__btn ${submitted === 'negative' ? 'feedback-widget__btn--active' : ''}`} onClick={handleThumbsDown}>
          <LucideIcon name='thumbsDown' size={20} color={submitted === 'negative' ? 'var(--reader-ink)' : 'var(--reader-muted)'} />
        </View>
      </View>

      {showDetail && (
        <View className='feedback-widget__detail'>
          {NEGATIVE_OPTIONS.map(opt => (
            <View
              key={opt.value}
              className={`feedback-widget__option ${selectedType === opt.value ? 'feedback-widget__option--active' : ''}`}
              onClick={() => setSelectedType(opt.value)}
            >
              {opt.label}
            </View>
          ))}
          <View className='feedback-widget__input-wrap'>
            <Textarea
              className='feedback-widget__input'
              value={content}
              onInput={(e) => setContent(e.detail.value)}
              placeholder='补充说明（选填）'
              maxlength={500}
              autoHeight
            />
          </View>
          <View
            className={`feedback-widget__submit ${!selectedType ? 'feedback-widget__submit--disabled' : ''}`}
            onClick={handleSubmitNegative}
          >
            提交反馈
          </View>
        </View>
      )}
    </View>
  )
}

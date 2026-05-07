import { View, Text, Textarea } from '@tarojs/components'
import { useState } from 'react'
import { submitFeedback } from '../../services/api/feedback.client'
import { ensureLoggedIn } from '../../services/auth'
import LucideIcon from '../LucideIcon'
import Taro from '@tarojs/taro'
import './index.scss'

const POSITIVE_OPTIONS = [
  { value: 'helpful', label: '有帮助' },
]

const NEGATIVE_OPTIONS = [
  { value: 'wrong_label', label: '标注有误' },
  { value: 'inaccurate', label: '释义不准确' },
  { value: 'wrong_boundary', label: '标注范围有误' },
  { value: 'should_not_annotate', label: '不该标注' },
  { value: 'other', label: '其他问题' },
]

interface AnnotationFeedbackProps {
  recordId: string
  targetId: string
  annotationType: string
  contextJson?: Record<string, unknown>
  onClose: () => void
}

export default function AnnotationFeedback({
  recordId,
  targetId,
  annotationType,
  contextJson,
  onClose,
}: AnnotationFeedbackProps) {
  const [selectedType, setSelectedType] = useState('')
  const [selectedSentiment, setSelectedSentiment] = useState<'positive' | 'negative' | ''>('')
  const [content, setContent] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSelect = (type: string, sentiment: 'positive' | 'negative') => {
    setSelectedType(type)
    setSelectedSentiment(sentiment)
  }

  const handleSubmit = async () => {
    if (!selectedType || !selectedSentiment || submitting) return
    const loginRes = await ensureLoggedIn()
    if (!loginRes.success) return
    setSubmitting(true)
    try {
      await submitFeedback({
        feedbackScope: 'annotation',
        targetId,
        analysisRecordId: recordId,
        sentiment: selectedSentiment,
        feedbackType: selectedType,
        annotationType,
        content: content || undefined,
        contextJson: contextJson || {},
      })
      Taro.showToast({ title: '感谢反馈', icon: 'success', duration: 1500 })
      onClose()
    } catch {
      Taro.showToast({ title: '提交失败', icon: 'error', duration: 1500 })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <View className='annotation-feedback' onClick={(e) => e.stopPropagation()}>
      <View className='annotation-feedback__header'>
        <Text className='annotation-feedback__title'>反馈标注</Text>
        <View className='annotation-feedback__close' onClick={onClose}>
          <LucideIcon name='x' size={18} color='var(--text-muted)' />
        </View>
      </View>

      <View className='annotation-feedback__section'>
        <Text className='annotation-feedback__section-label'>正面反馈</Text>
        {POSITIVE_OPTIONS.map(opt => (
          <View
            key={opt.value}
            className={`annotation-feedback__option ${selectedType === opt.value ? 'annotation-feedback__option--active' : ''}`}
            onClick={() => handleSelect(opt.value, 'positive')}
          >
            {opt.label}
          </View>
        ))}
      </View>

      <View className='annotation-feedback__section'>
        <Text className='annotation-feedback__section-label'>问题反馈</Text>
        {NEGATIVE_OPTIONS.map(opt => (
          <View
            key={opt.value}
            className={`annotation-feedback__option ${selectedType === opt.value ? 'annotation-feedback__option--active' : ''}`}
            onClick={() => handleSelect(opt.value, 'negative')}
          >
            {opt.label}
          </View>
        ))}
      </View>

      <View className='annotation-feedback__input-wrap'>
        <Textarea
          className='annotation-feedback__input'
          value={content}
          onInput={(e) => setContent(e.detail.value)}
          placeholder='补充说明（选填）'
          maxlength={500}
          autoHeight
        />
      </View>

      <View
        className={`annotation-feedback__submit ${!selectedType ? 'annotation-feedback__submit--disabled' : ''}`}
        onClick={handleSubmit}
      >
        提交反馈
      </View>
    </View>
  )
}

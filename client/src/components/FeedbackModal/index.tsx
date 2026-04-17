import { View, Text, Input } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState, useCallback } from 'react'
import LucideIcon from '../LucideIcon'
import {
  FeedbackType,
  FeedbackCategory,
  ResultOverallContext,
  AnnotationContext,
  VocabContext,
  GeneralContext,
  submitFeedback,
} from '../../services/api/feedbacks.client'
import './index.scss'

export type FeedbackMode =
  | 'result_overall'
  | 'grammar_note'
  | 'sentence_analysis'
  | 'vocab_entry'
  | 'general'

interface FeedbackModalProps {
  visible: boolean
  mode: FeedbackMode
  title?: string
  analysisRecordId?: string | null
  context?: ResultOverallContext | AnnotationContext | VocabContext | GeneralContext
  onClose: () => void
  onSubmitSuccess?: () => void
}

const ALL_CATEGORIES: { value: FeedbackCategory; label: string }[] = [
  { value: 'data_error', label: '数据错误' },
  { value: 'poor_quality', label: '质量差' },
  { value: 'translation_wrong', label: '翻译错误' },
  { value: 'incomplete', label: '信息不完整' },
  { value: 'irrelevant', label: '不相关' },
  { value: 'unclear', label: '表达不清楚' },
  { value: 'performance', label: '太慢了' },
  { value: 'ui_ux', label: '体验不好' },
  { value: 'other', label: '其他' },
]

const MODE_CATEGORY_CONFIG: Record<FeedbackMode, FeedbackCategory[]> = {
  result_overall: ['data_error', 'poor_quality', 'translation_wrong', 'incomplete', 'unclear', 'performance', 'ui_ux', 'other'],
  grammar_note: ['data_error', 'poor_quality', 'translation_wrong', 'incomplete', 'irrelevant', 'unclear', 'other'],
  sentence_analysis: ['data_error', 'poor_quality', 'translation_wrong', 'incomplete', 'irrelevant', 'unclear', 'other'],
  vocab_entry: ['data_error', 'poor_quality', 'translation_wrong', 'incomplete', 'irrelevant', 'unclear', 'other'],
  general: ['data_error', 'unclear', 'ui_ux', 'other'],
}

const MODE_CONFIG: Record<FeedbackMode, { 
  type: FeedbackType; 
  title: string;
  showSatisfaction: boolean;
  satisfactionQuestion?: string;
  categoryQuestion?: string;
}> = {
  result_overall: { 
    type: 'result_overall', 
    title: '本次解析',
    showSatisfaction: true,
    satisfactionQuestion: '您对本次解析是否满意？',
    categoryQuestion: '请问哪里有问题？（可多选）',
  },
  grammar_note: { 
    type: 'grammar_note', 
    title: '语法标注',
    showSatisfaction: true,
    satisfactionQuestion: '这个语法标注对您有帮助吗？',
    categoryQuestion: '请问有什么问题？（可多选）',
  },
  sentence_analysis: { 
    type: 'sentence_analysis', 
    title: '句式解析',
    showSatisfaction: true,
    satisfactionQuestion: '这个句式解析对您有帮助吗？',
    categoryQuestion: '请问有什么问题？（可多选）',
  },
  vocab_entry: { 
    type: 'vocab_entry', 
    title: '词汇释义',
    showSatisfaction: true,
    satisfactionQuestion: '这个词汇释义对您有帮助吗？',
    categoryQuestion: '请问有什么问题？（可多选）',
  },
  general: { 
    type: 'general', 
    title: '意见反馈',
    showSatisfaction: false,
    categoryQuestion: '请选择反馈类型（可多选）',
  },
}

export default function FeedbackModal({
  visible,
  mode,
  title,
  analysisRecordId,
  context,
  onClose,
  onSubmitSuccess,
}: FeedbackModalProps) {
  const [satisfaction, setSatisfaction] = useState<boolean | null>(null)
  const [selectedCategories, setSelectedCategories] = useState<FeedbackCategory[]>([])
  const [detailText, setDetailText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const config = MODE_CONFIG[mode]
  const displayTitle = title || config.title

  const resetState = useCallback(() => {
    setSatisfaction(null)
    setSelectedCategories([])
    setDetailText('')
    setSubmitting(false)
    setSubmitted(false)
  }, [])

  const handleClose = () => {
    resetState()
    onClose()
  }

  const toggleCategory = (category: FeedbackCategory) => {
    setSelectedCategories((prev) => {
      if (prev.includes(category)) {
        return prev.filter((c) => c !== category)
      }
      return [...prev, category]
    })
  }

  const handleSubmit = async () => {
    if (config.showSatisfaction && satisfaction === null) {
      Taro.showToast({ title: '请选择是否满意', icon: 'none' })
      return
    }

    setSubmitting(true)
    try {
      await submitFeedback({
        feedback_type: config.type,
        satisfaction: config.showSatisfaction ? satisfaction : null,
        category: selectedCategories.length > 0 ? selectedCategories[0] : null,
        detail_text: detailText || null,
        analysis_record_id: analysisRecordId || null,
        context_json: context || {},
        client_metadata_json: {
          app_version: '1.0.0',
          platform: 'wechat_miniprogram',
        },
      })

      setSubmitted(true)
      Taro.showToast({ title: '感谢您的反馈', icon: 'success' })

      setTimeout(() => {
        handleClose()
        onSubmitSuccess?.()
      }, 1500)
    } catch (error) {
      console.error('[FeedbackModal] submit failed:', error)
      Taro.showToast({ title: '提交失败，请重试', icon: 'none' })
    } finally {
      setSubmitting(false)
    }
  }

  const availableCategories = MODE_CATEGORY_CONFIG[mode]
    .map((cat) => ALL_CATEGORIES.find((c) => c.value === cat))
    .filter((c): c is NonNullable<typeof c> => !!c)

  if (!visible) return null

  if (submitted) {
    return (
      <View className='feedback-modal-overlay' onClick={handleClose}>
        <View className='feedback-modal-container' onClick={(e) => e.stopPropagation()}>
          <View className='feedback-success-content'>
            <View className='success-icon-wrapper'>
              <LucideIcon name='check' size={48} color='#22c55e' />
            </View>
            <Text className='success-title'>感谢您的反馈</Text>
            <Text className='success-subtitle'>您的反馈对我们很重要，将帮助我们持续改进</Text>
          </View>
        </View>
      </View>
    )
  }

  return (
    <View className='feedback-modal-overlay' onClick={handleClose}>
      <View className='feedback-modal-container' onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <View className='feedback-modal-header'>
          <Text className='feedback-modal-title'>{displayTitle}</Text>
          <View className='feedback-modal-close' onClick={handleClose}>
            <LucideIcon name='x' size={20} color='var(--text-muted)' />
          </View>
        </View>

        {/* Content */}
        <View className='feedback-modal-content'>
          {/* 满意度选择（仅在需要时显示） */}
          {config.showSatisfaction && (
            <View className='feedback-section'>
              <Text className='feedback-question'>
                {config.satisfactionQuestion || `您对${displayTitle}是否满意？`}
              </Text>
              <View className='satisfaction-buttons'>
                <View
                  className={`satisfaction-btn ${satisfaction === true ? 'active satisfied' : ''}`}
                  onClick={() => setSatisfaction(true)}
                >
                  <LucideIcon
                    name='smile'
                    size={24}
                    color={satisfaction === true ? '#22c55e' : 'var(--text-sub)'}
                  />
                  <Text
                    className='satisfaction-label'
                    style={{ color: satisfaction === true ? '#22c55e' : 'var(--text-sub)' }}
                  >
                    满意
                  </Text>
                </View>
                <View
                  className={`satisfaction-btn ${satisfaction === false ? 'active dissatisfied' : ''}`}
                  onClick={() => setSatisfaction(false)}
                >
                  <LucideIcon
                    name='frown'
                    size={24}
                    color={satisfaction === false ? '#ef4444' : 'var(--text-sub)'}
                  />
                  <Text
                    className='satisfaction-label'
                    style={{ color: satisfaction === false ? '#ef4444' : 'var(--text-sub)' }}
                  >
                    不满意
                  </Text>
                </View>
              </View>
            </View>
          )}

          {/* 问题类型选择：
              - 有满意度时：仅在不满意时显示
              - 无满意度时（如 general）：直接显示
          */}
          {(!config.showSatisfaction || satisfaction === false) && availableCategories.length > 0 && (
            <View className='feedback-section'>
              <Text className='feedback-question'>
                {config.categoryQuestion || '请问哪里有问题？（可多选）'}
              </Text>
              <View className='category-grid'>
                {availableCategories.map((cat) => (
                  <View
                    key={cat.value}
                    className={`category-tag ${selectedCategories.includes(cat.value) ? 'selected' : ''}`}
                    onClick={() => toggleCategory(cat.value)}
                  >
                    <Text className='category-label'>{cat.label}</Text>
                  </View>
                ))}
              </View>
            </View>
          )}

          {/* 详细理由输入 */}
          <View className='feedback-section'>
            <Text className='feedback-question'>
              请描述您的问题或建议 <Text className='optional'>（选填）</Text>
            </Text>
            <View className='detail-input-wrapper'>
              <Input
                className='detail-input'
                type='text'
                placeholder='请输入您的问题或建议...'
                value={detailText}
                onInput={(e) => setDetailText(e.detail.value)}
                maxlength={500}
              />
              <Text className='char-count'>{detailText.length}/500</Text>
            </View>
          </View>
        </View>

        {/* Footer */}
        <View className='feedback-modal-footer safe-area-bottom'>
          <View
            className={`submit-btn ${submitting ? 'disabled' : ''}`}
            onClick={!submitting ? handleSubmit : undefined}
          >
            {submitting ? (
              <Text className='submit-text'>提交中...</Text>
            ) : (
              <Text className='submit-text'>提交反馈</Text>
            )}
          </View>
        </View>
      </View>
    </View>
  )
}

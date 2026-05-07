import LucideIcon from '../../components/LucideIcon'
import { View, Text, Textarea } from '@tarojs/components'
import { useState } from 'react'
import Taro from '@tarojs/taro'
import { submitFeedback } from '../../services/api/feedback.client'
import { ensureLoggedIn } from '../../services/auth'
import NavBar from '../../components/NavBar'
import { useLayoutStore } from '../../stores/layout'
import FeedbackOptionGrid from '../../components/FeedbackSystem/FeedbackOptionGrid'
import FeedbackSuccessPanel from '../../components/FeedbackSystem/FeedbackSuccessPanel'
import { FEEDBACK_CONFIG_BY_SCOPE } from '../../config/feedback'
import './index.scss'

const config = FEEDBACK_CONFIG_BY_SCOPE.app

export default function FeedbackPage() {
  const [selectedCategory, setSelectedCategory] = useState('')
  const [content, setContent] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const { navBarHeight } = useLayoutStore()

  const isSubmitDisabled = !selectedCategory || !content.trim()

  /* 禁用态文案内嵌到按钮 */
  const getSubmitLabel = () => {
    if (submitting) return '提交中...'
    if (!selectedCategory) return '请先选择问题类型'
    if (!content.trim()) return '请补充问题描述'
    return '发送反馈'
  }

  const handleSubmit = async () => {
    if (isSubmitDisabled || submitting) return
    const loginRes = await ensureLoggedIn()
    if (!loginRes.success) return
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
      setSubmitted(true)
    } catch {
      Taro.showToast({ title: '提交失败，请稍后重试', icon: 'none', duration: 2000 })
    } finally {
      setSubmitting(false)
    }
  }

  const resetForm = () => {
    setSelectedCategory('')
    setContent('')
    setSubmitted(false)
  }

  return (
    <View className='feedback-page'>
      <NavBar
        title='意见反馈'
        showBack
        background='var(--reader-paper, #FAF9F6)'
        color='var(--text-primary, #111111)'
      />
      <View className='nav-spacer' style={{ height: navBarHeight + 'px' }} />

      <View className='feedback-page__content'>
        {/* Header - 衬线字体标题 */}
        <View className='feedback-page__header'>
          <Text className='feedback-page__title'>告诉我们你的想法</Text>
          <Text className='feedback-page__subtitle'>遇到问题了？有新点子？随时告诉我们，我们一起让 Claread 更好用。</Text>
        </View>

        {submitted ? (
          <View className='feedback-page__success-container'>
            <FeedbackSuccessPanel inline onDismiss={resetForm} />
          </View>
        ) : (
          <>
            {/* Category Selection - 只标可选项 */}
            <View className='feedback-page__section'>
              <View className='feedback-page__section-header'>
                <Text className='feedback-page__section-title'>问题类型</Text>
              </View>
              <FeedbackOptionGrid
                options={config.neutralOptions || []}
                selectedValues={selectedCategory ? [selectedCategory] : []}
                onChange={(vals) => setSelectedCategory(vals[0] || '')}
              />
            </View>

            {/* Description Input - 标注选填 */}
            <View className='feedback-page__section'>
              <View className='feedback-page__section-header'>
                <Text className='feedback-page__section-title'>详细描述</Text>
                <Text className='feedback-page__section-tag'>选填</Text>
              </View>
              <View className='feedback-page__input-wrap'>
                <Textarea
                  id='feedback-content'
                  className='feedback-page__textarea'
                  value={content}
                  onInput={(e) => setContent(e.detail.value)}
                  placeholder='请详细描述你的问题或建议，比如：在什么情况下出现的？你希望得到什么样的改进？'
                  maxlength={2000}
                  autoHeight
                />
              </View>
            </View>

            {/* Submit Button - 品牌主色 + 无图标 */}
            <View className='feedback-page__footer'>
              <View
                className={`feedback-page__submit ${isSubmitDisabled ? 'feedback-page__submit--disabled' : ''}`}
                onClick={handleSubmit}
              >
                <Text>{getSubmitLabel()}</Text>
              </View>
            </View>
          </>
        )}
      </View>
    </View>
  )
}

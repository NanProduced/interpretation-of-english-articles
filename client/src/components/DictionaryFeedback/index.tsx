import { View, Text, Textarea } from '@tarojs/components'
import { useState } from 'react'
import { submitFeedback } from '../../services/api/feedback.client'
import Taro from '@tarojs/taro'
import './index.scss'

const NEGATIVE_OPTIONS = [
  { value: 'wrong_definition', label: '释义错误' },
  { value: 'missing_definition', label: '释义缺失' },
  { value: 'wrong_pos', label: '词性标注有误' },
  { value: 'wrong_phonetic', label: '音标有误' },
  { value: 'bad_example', label: '例句不当' },
  { value: 'other', label: '其他问题' },
]

interface DictionaryFeedbackProps {
  word: string
  phonetic?: string
  currentMeaning?: string
  dictSource?: string
  dictEntryId?: number
  contextSentence?: string
  disambiguationChosen?: string
  readingVariant?: string
  recordId?: string
  onClose: () => void
}

export default function DictionaryFeedback({
  word,
  phonetic,
  currentMeaning,
  dictSource,
  dictEntryId,
  contextSentence,
  disambiguationChosen,
  readingVariant,
  recordId,
  onClose,
}: DictionaryFeedbackProps) {
  const [selectedType, setSelectedType] = useState('')
  const [content, setContent] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (!selectedType || submitting) return
    setSubmitting(true)
    try {
      await submitFeedback({
        feedbackScope: 'dictionary',
        targetId: dictEntryId ? String(dictEntryId) : word,
        analysisRecordId: recordId,
        sentiment: 'negative',
        feedbackType: selectedType,
        content: content || undefined,
        contextJson: {
          word,
          phonetic: phonetic || '',
          current_meaning: currentMeaning || '',
          dict_source: dictSource || '',
          dict_entry_id: dictEntryId,
          context_sentence: contextSentence || '',
          disambiguation_chosen: disambiguationChosen || '',
          reading_variant: readingVariant || '',
        },
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
    <View className='dict-feedback' onClick={(e) => e.stopPropagation()}>
      <View className='dict-feedback__header'>
        <Text className='dict-feedback__title'>反馈词典</Text>
        <View className='dict-feedback__close' onClick={onClose}>✕</View>
      </View>

      <View className='dict-feedback__word-info'>
        <Text className='dict-feedback__word'>{word}</Text>
        {phonetic && <Text className='dict-feedback__phonetic'>{phonetic}</Text>}
      </View>

      {NEGATIVE_OPTIONS.map(opt => (
        <View
          key={opt.value}
          className={`dict-feedback__option ${selectedType === opt.value ? 'dict-feedback__option--active' : ''}`}
          onClick={() => setSelectedType(opt.value)}
        >
          {opt.label}
        </View>
      ))}

      <View className='dict-feedback__input-wrap'>
        <Textarea
          className='dict-feedback__input'
          value={content}
          onInput={(e) => setContent(e.detail.value)}
          placeholder='补充说明（选填）'
          maxlength={500}
          autoHeight
        />
      </View>

      <View
        className={`dict-feedback__submit ${!selectedType ? 'dict-feedback__submit--disabled' : ''}`}
        onClick={handleSubmit}
      >
        提交反馈
      </View>
    </View>
  )
}

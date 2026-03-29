import { useState } from 'react'
import { View, Text, Button, Textarea, Radio, RadioGroup, Label } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useConfigStore, UserPurpose } from '../../stores/config'
import './index.scss'

export default function InputPage() {
  const [content, setContent] = useState('')
  const { purpose, setPurpose } = useConfigStore()

  const handlePurposeChange = (e) => {
    setPurpose(e.detail.value as UserPurpose)
  }

  const handleSubmit = () => {
    if (!content.trim()) {
      Taro.showToast({ title: '请输入文章内容', icon: 'none' })
      return
    }
    // 这里未来会调用 API
    Taro.navigateTo({ url: '/pages/result/index' })
  }

  const purposes: { value: UserPurpose, label: string, desc: string }[] = [
    { value: 'daily', label: '日常阅读', desc: '提升词汇量，适合新闻、博客' },
    { value: 'exam', label: '考试备考', desc: '侧重语法和长难句，适合 CET/IELTS' },
    { value: 'academic', label: '学术/专业', desc: '精准翻译，适合论文、专业文献' }
  ]

  return (
    <View className='input-container'>
      <View className='section-header'>
        <Text className='title'>粘贴文章</Text>
      </View>

      <View className='input-area'>
        <Textarea
          className='content-textarea'
          placeholder='在此粘贴您想要解读的英文文章内容...'
          maxlength={5000}
          value={content}
          onInput={(e) => setContent(e.detail.value)}
        />
        <Text className='char-count'>{content.length} / 5000</Text>
      </View>

      <View className='section-header'>
        <Text className='title'>选择阅读目的</Text>
      </View>

      <RadioGroup className='purpose-group' onChange={handlePurposeChange}>
        {purposes.map(item => (
          <Label key={item.value} className='purpose-label'>
            <View className='purpose-item'>
              <Radio value={item.value} checked={purpose === item.value} color='#07c160' />
              <View className='purpose-info'>
                <Text className='label-text'>{item.label}</Text>
                <Text className='desc-text'>{item.desc}</Text>
              </View>
            </View>
          </Label>
        ))}
      </RadioGroup>

      <View className='action-footer'>
        <Button className='submit-btn' onClick={handleSubmit}>
          开始智能解读
        </Button>
      </View>
    </View>
  )
}

import { useState, useEffect } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { InlineMarkModel, DictionaryResult } from '../../types/v2-render'
import LucideIcon from '../LucideIcon'
import './index.scss'

interface WordPopupProps {
  visible: boolean
  mark: InlineMarkModel | null
  word: string
  onClose: () => void
}

export default function WordPopup({ visible, mark, word, onClose }: WordPopupProps) {
  const [dictResult, setDictResult] = useState<DictionaryResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [audioPlaying, setAudioPlaying] = useState(false)

  const lookupText = mark?.lookupText || word
  const lookupKind = mark?.lookupKind
  const glossary = mark?.glossary
  const examTags = mark?.examTags

  useEffect(() => {
    if (visible && lookupText) {
      fetchDictionary(lookupText)
    }
  }, [visible, lookupText])

  const fetchDictionary = async (text: string) => {
    setLoading(true)
    setError(null)
    try {
      // 在 Mock 阶段，我们直接使用 Mock 词典数据
      await new Promise(resolve => setTimeout(resolve, 300))
      setDictResult(getMockDictionaryResult(text))
    } catch (err) {
      setError('查询失败')
    } finally {
      setLoading(false)
    }
  }

  const getMockDictionaryResult = (text: string): DictionaryResult => {
    const mockData: Record<string, DictionaryResult> = {
      'paradigm': {
        word: 'paradigm',
        phonetic: '/ˈpærədaɪm/',
        meanings: [{
          partOfSpeech: 'n.',
          definitions: [{ meaning: '范式；典范；样板', example: 'a new paradigm for scientific research' }]
        }]
      },
      'profound': {
        word: 'profound',
        phonetic: '/prəˈfaʊnd/',
        meanings: [{
          partOfSpeech: 'adj.',
          definitions: [{ meaning: '深厚的；深刻出的；渊博的' }]
        }]
      }
    }
    return mockData[text.toLowerCase()] || {
      word: text,
      phonetic: '/.../',
      meanings: [{ partOfSpeech: 'n.', definitions: [{ meaning: '（模拟词典释义）' }] }]
    }
  }

  const handlePlayAudio = () => {
    setAudioPlaying(true)
    setTimeout(() => setAudioPlaying(false), 800)
  }

  if (!visible) return null

  return (
    <View className='word-popup-overlay' onClick={onClose}>
      <View className='word-popup-container' onClick={(e) => e.stopPropagation()}>
        <View className='popup-header'>
          <View className='word-info'>
            <View className='word-text-row'>
              <Text className='word-text'>{lookupText}</Text>
              {lookupKind && <Text className='word-kind-tag'>{lookupKind}</Text>}
            </View>
            <View className='word-sub-info'>
              {dictResult?.phonetic && <Text className='word-phonetic'>{dictResult.phonetic}</Text>}
              {examTags && examTags.length > 0 && (
                <View className='exam-tags'>
                  {examTags.map(tag => (
                    <Text key={tag} className='exam-tag'>{tag}</Text>
                  ))}
                </View>
              )}
            </View>
          </View>
          <View className='header-actions'>
            <View className={`audio-btn ${audioPlaying ? 'playing' : ''}`} onClick={handlePlayAudio}>
              <LucideIcon name='volume2' size={20} color={audioPlaying ? '#4285f4' : '#666'} />
            </View>
            <View className='close-btn' onClick={onClose}>
              <LucideIcon name='x' size={20} color='#666' />
            </View>
          </View>
        </View>

        <ScrollView className='popup-content' scrollY>
          {/* 1. AI 增强层 */}
          {glossary && (
            <View className='glossary-section'>
              <View className='glossary-header'>
                <LucideIcon name='sparkles' size={14} color='#030213' />
                <Text className='glossary-title'>AI 语境精讲</Text>
              </View>
              {glossary.zh && <Text className='glossary-zh'>{glossary.zh}</Text>}
              {glossary.gloss && <Text className='glossary-gloss'>{glossary.gloss}</Text>}
              {glossary.reason && <Text className='glossary-reason'>{glossary.reason}</Text>}
            </View>
          )}

          {/* 2. 词典基础层 */}
          {loading ? (
            <View className='loading-state'><Text>正在查询词典...</Text></View>
          ) : dictResult ? (
            <View className='dict-section'>
              {dictResult.meanings.map((meaning, idx) => (
                <View key={idx} className='meaning-item'>
                  <View className='def-row'>
                    <Text className='part-of-speech'>{meaning.partOfSpeech}</Text>
                    <View className='definitions'>
                      {meaning.definitions.map((def, defIdx) => (
                        <View key={defIdx} className='definition-item'>
                          <Text className='definition-text'>{def.meaning}</Text>
                          {def.example && <Text className='example-text'>"{def.example}"</Text>}
                        </View>
                      ))}
                    </View>
                  </View>
                </View>
              ))}
            </View>
          ) : null}
        </ScrollView>

        <View className='popup-footer'>
          <View className='footer-btn'>
            <LucideIcon name='bookmark' size={16} color='#666' />
            <Text>收藏</Text>
          </View>
          <View className='footer-btn primary'>
            <LucideIcon name='bookOpen' size={16} color='#fff' />
            <Text>记入生词本</Text>
          </View>
        </View>
      </View>
    </View>
  )
}

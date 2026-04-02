import { useState, useEffect } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { InlineMarkModel, DictionaryResult } from '../../types/render-scene'
import LucideIcon from '../LucideIcon'
import './index.scss'

interface WordPopupProps {
  visible: boolean
  mode?: 'mini' | 'full'
  mark: InlineMarkModel | null
  word: string
  x?: number
  y?: number
  onClose: () => void
  onExpand?: () => void
}

export default function WordPopup({ visible, mode = 'full', mark, word, x = 0, y = 0, onClose, onExpand }: WordPopupProps) {
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

  // Mini Tooltip 模式
  if (mode === 'mini') {
    // 简易防溢出计算
    const screenWidth = Taro.getSystemInfoSync().windowWidth
    const safeLeft = x > screenWidth - 260 ? screenWidth - 280 : Math.max(20, x - 130)
    const safeTop = y > 200 ? y - 160 : y + 40

    const popupStyle: React.CSSProperties = {
      position: 'fixed',
      left: safeLeft + 'px',
      top: safeTop + 'px',
      zIndex: 1000
    }

    return (
      <View className='word-popup-overlay mini-overlay' onClick={onClose}>
        <View 
          className='mini-word-card' 
          style={popupStyle} 
          onClick={(e) => { e.stopPropagation(); onExpand?.(); }}
        >
          <View className='mini-header'>
            <View className='mini-word-info'>
              <Text className='mini-word'>{lookupText}</Text>
              {dictResult?.phonetic && <Text className='mini-phonetic'>{dictResult.phonetic}</Text>}
            </View>
            <View className='mini-actions'>
              <View 
                className={`mini-icon-btn ${audioPlaying ? 'playing' : ''}`} 
                onClick={(e) => { e.stopPropagation(); handlePlayAudio(); }}
              >
                <LucideIcon name='volume2' size={16} color={audioPlaying ? 'var(--color-info)' : 'var(--text-sub)'} />
              </View>
              <View 
                className='mini-icon-btn'
                onClick={(e) => { e.stopPropagation(); /* TODO: 收藏 */ }}
              >
                <LucideIcon name='star' size={16} color='var(--text-sub)' />
              </View>
            </View>
          </View>
          
          <View className='mini-content'>
            {loading ? (
              <Text className='mini-loading'>查询中...</Text>
            ) : dictResult && dictResult.meanings[0] ? (
              <View className='mini-def-row'>
                <Text className='mini-pos'>{dictResult.meanings[0].partOfSpeech}</Text>
                <Text className='mini-def' numberOfLines={1}>
                  {dictResult.meanings[0].definitions[0].meaning.split('；')[0]}
                </Text>
              </View>
            ) : (
              <Text className='mini-loading'>未找到释义</Text>
            )}
          </View>

          <View className='mini-footer'>
            <Text className='mini-hint'>点击查看详情</Text>
            <LucideIcon name='chevronRight' size={12} color='var(--text-muted)' />
          </View>
        </View>
      </View>
    )
  }

  // Full Bottom Sheet 模式
  return (
    <View className='word-popup-overlay' onClick={onClose}>
      <View className='word-popup-container' onClick={(e) => e.stopPropagation()}>
        <View className='popup-drag-handle' />
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
          <View className='header-right-actions'>
            <View className={`audio-btn-large ${audioPlaying ? 'playing' : ''}`} onClick={handlePlayAudio}>
              <LucideIcon name='volume2' size={24} color={audioPlaying ? 'var(--color-info)' : 'var(--text-main)'} />
            </View>
            <View className='popup-close-btn' onClick={onClose}>
              <LucideIcon name='x' size={24} color='var(--text-muted)' />
            </View>
          </View>
        </View>

        <ScrollView className='popup-scroll-content' scrollY>
          {/* 1. AI 增强层 */}
          {glossary && (
            <View className='glossary-card'>
              <View className='glossary-card-header'>
                <LucideIcon name='sparkles' size={16} color='var(--color-ink)' />
                <Text className='glossary-card-title'>AI 深度解析</Text>
              </View>
              <View className='glossary-card-body'>
                {glossary.zh && <Text className='glossary-zh'>{glossary.zh}</Text>}
                {glossary.gloss && <Text className='glossary-gloss'>{glossary.gloss}</Text>}
                {glossary.reason && <Text className='glossary-reason'>{glossary.reason}</Text>}
              </View>
            </View>
          )}

          {/* 2. 词典基础层 */}
          {loading ? (
            <View className='popup-loading-state'><Text>正在检索词库...</Text></View>
          ) : dictResult ? (
            <View className='dict-entries'>
              {dictResult.meanings.map((meaning, idx) => (
                <View key={idx} className='meaning-block'>
                  <View className='pos-tag'>{meaning.partOfSpeech}</View>
                  <View className='definition-list'>
                    {meaning.definitions.map((def, defIdx) => (
                      <View key={defIdx} className='def-item'>
                        <Text className='def-zh'>{def.meaning}</Text>
                        {def.example && <Text className='def-en-example'>"{def.example}"</Text>}
                      </View>
                    ))}
                  </View>
                </View>
              ))}
            </View>
          ) : null}
        </ScrollView>

        <View className='popup-footer-actions safe-area-bottom'>
          <View className='footer-action-btn secondary'>
            <LucideIcon name='star' size={18} color='var(--text-sub)' />
            <Text className='btn-text'>收藏</Text>
          </View>
          <View className='footer-action-btn primary'>
            <LucideIcon name='plus' size={18} color='#fff' />
            <Text className='btn-text'>记入生词本</Text>
          </View>
        </View>
      </View>
    </View>
  )
}

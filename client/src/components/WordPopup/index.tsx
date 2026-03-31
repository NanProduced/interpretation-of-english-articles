import { useState, useEffect } from 'react'
import { View, Text, Image } from '@tarojs/components'
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
  const [activeTab, setActiveTab] = useState<'dict' | 'ai'>('dict')
  const [dictResult, setDictResult] = useState<DictionaryResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [audioPlaying, setAudioPlaying] = useState(false)

  // 优先使用 mark 中的结构化字段
  const lookupText = mark?.lookupText || word
  const lookupKind = mark?.lookupKind
  const aiTitle = mark?.aiTitle
  const aiBody = mark?.aiBody

  useEffect(() => {
    if (visible && lookupText) {
      fetchDictionary(lookupText)
    }
  }, [visible, lookupText])

  const fetchDictionary = async (word: string) => {
    setLoading(true)
    setError(null)
    setDictResult(null)

    try {
      // 使用有道词典网页版 API 获取数据
      const url = `https://dict.youdao.com/w/eng/${encodeURIComponent(word)}/`
      const response = await Taro.request({
        url,
        method: 'GET',
        header: {
          'Accept': 'text/html',
        }
      })

      if (response.statusCode === 200 && response.data) {
        // 解析 HTML 获取词典数据
        const result = parseYoudaoHtml(response.data as string, word)
        setDictResult(result)
      } else {
        throw new Error('请求失败')
      }
    } catch (err) {
      console.error('词典查询失败:', err)
      // 使用 mock 数据作为后备
      setDictResult(getMockDictionaryResult(word))
    } finally {
      setLoading(false)
    }
  }

  const parseYoudaoHtml = (html: string, word: string): DictionaryResult => {
    // 简化解析，实际项目中应使用更健壮的解析库
    const result: DictionaryResult = {
      word,
      meanings: [],
    }

    // 尝试提取音标
    const phoneticMatch = html.match(/class="phonetic_text">\[([^\]]+)\]/)
    if (phoneticMatch) {
      result.phonetic = phoneticMatch[1]
    }

    // 尝试提取释义
    const transMatch = html.match(/class="trans">(.*?)<\/div>/s)
    if (transMatch) {
      const transText = transMatch[1].replace(/<[^>]+>/g, '').trim()
      if (transText) {
        result.meanings.push({
          partOfSpeech: 'n.',
          definitions: [{ meaning: transText }],
        })
      }
    }

    // 如果解析失败，使用 mock
    if (result.meanings.length === 0) {
      return getMockDictionaryResult(word)
    }

    return result
  }

  const getMockDictionaryResult = (word: string): DictionaryResult => {
    const mockData: Record<string, DictionaryResult> = {
      'paradigm': {
        word: 'paradigm',
        phonetic: '/ˈpærədaɪm/',
        meanings: [
          {
            partOfSpeech: 'n.',
            definitions: [
              { meaning: '范式；典范；样板', example: 'a new paradigm for scientific research', exampleTranslation: '科学研究的新范式' },
            ],
          },
        ],
      },
      'comprehensive': {
        word: 'comprehensive',
        phonetic: '/ˌkɒmprɪˈhensɪv/',
        meanings: [
          {
            partOfSpeech: 'adj.',
            definitions: [
              { meaning: '综合的；全面的；广泛的', example: 'a comprehensive review of the evidence', exampleTranslation: '对证据的全面审查' },
            ],
          },
        ],
      },
      'leverage': {
        word: 'leverage',
        phonetic: '/ˈliːvərɪdʒ/',
        meanings: [
          {
            partOfSpeech: 'v.',
            definitions: [
              { meaning: '利用；杠杆效应', example: 'to leverage technology to improve efficiency', exampleTranslation: '利用技术提高效率' },
            ],
          },
        ],
      },
      'paradigmatic': {
        word: 'paradigmatic',
        phonetic: '/ˌpærədɪɡˈmætɪk/',
        meanings: [
          {
            partOfSpeech: 'adj.',
            definitions: [
              { meaning: '典范的；范式的', example: 'paradigmatic shifts in scientific thinking', exampleTranslation: '科学思维中的范式转变' },
            ],
          },
        ],
      },
    }

    return mockData[word.toLowerCase()] || {
      word,
      phonetic: `/${word.charAt(0)}/`,
      meanings: [
        {
          partOfSpeech: 'n.',
          definitions: [
            { meaning: '（该词在 mock 数据中）', example: 'Example sentence', exampleTranslation: '例句翻译' },
          ],
        },
      ],
    }
  }

  const handlePlayAudio = () => {
    if (word) {
      setAudioPlaying(true)
      Taro.showToast({ title: `播放 ${word} 发音`, icon: 'none' })
      // 模拟播放完成
      setTimeout(() => setAudioPlaying(false), 1000)
      // 实际项目中可以调用真实音频 API
    }
  }

  if (!visible) return null

  return (
    <View className='word-popup-overlay' onClick={onClose}>
      <View className='word-popup-container' onClick={(e) => e.stopPropagation()}>
        {/* 头部 */}
        <View className='popup-header'>
          <View className='word-info'>
            <View className='word-text-row'>
              <Text className='word-text'>{lookupText}</Text>
              {lookupKind && (
                <Text className='word-kind-tag'>{lookupKind}</Text>
              )}
            </View>
            {dictResult?.phonetic && (
              <Text className='word-phonetic'>{dictResult.phonetic}</Text>
            )}
          </View>
          <View className='header-actions'>
            <View
              className={`audio-btn ${audioPlaying ? 'playing' : ''}`}
              onClick={handlePlayAudio}
            >
              <LucideIcon
                name='volume-2'
                size={20}
                color={audioPlaying ? '#4285f4' : '#666'}
              />
            </View>
            <View className='close-btn' onClick={onClose}>
              <LucideIcon name='x' size={20} color='#666' />
            </View>
          </View>
        </View>

        {/* Tab 切换 */}
        <View className='popup-tabs'>
          <View
            className={`tab ${activeTab === 'dict' ? 'active' : ''}`}
            onClick={() => setActiveTab('dict')}
          >
            <Text>词典</Text>
          </View>
          <View
            className={`tab ${activeTab === 'ai' ? 'active' : ''}`}
            onClick={() => setActiveTab('ai')}
          >
            <Text>AI 补充</Text>
          </View>
        </View>

        {/* 内容区 */}
        <View className='popup-content'>
          {loading ? (
            <View className='loading-state'>
              <Text>加载中...</Text>
            </View>
          ) : error ? (
            <View className='error-state'>
              <Text>{error}</Text>
            </View>
          ) : activeTab === 'dict' && dictResult ? (
            <View className='dict-content'>
              {dictResult.meanings.map((meaning, idx) => (
                <View key={idx} className='meaning-item'>
                  <Text className='part-of-speech'>{meaning.partOfSpeech}</Text>
                  {meaning.definitions.map((def, defIdx) => (
                    <View key={defIdx} className='definition-item'>
                      <Text className='definition-text'>{def.meaning}</Text>
                      {def.example && (
                        <View className='example-section'>
                          <Text className='example-text'>{def.example}</Text>
                          {def.exampleTranslation && (
                            <Text className='example-translation'>{def.exampleTranslation}</Text>
                          )}
                        </View>
                      )}
                    </View>
                  ))}
                </View>
              ))}
            </View>
          ) : activeTab === 'ai' ? (
            <View className='ai-content'>
              {aiTitle || aiBody ? (
                <>
                  {aiTitle && <Text className='ai-title'>{aiTitle}</Text>}
                  {aiBody && <Text className='ai-note'>{aiBody}</Text>}
                </>
              ) : mark?.aiNote ? (
                <Text className='ai-note'>{mark.aiNote}</Text>
              ) : (
                <View className='empty-ai'>
                  <Text>暂无 AI 补充说明</Text>
                  <Text className='ai-hint'>点击上方「词典」查看释义</Text>
                </View>
              )}
            </View>
          ) : null}
        </View>

        {/* 底部操作 */}
        <View className='popup-footer'>
          <View className='footer-btn'>
            <LucideIcon name='heart' size={16} color='#666' />
            <Text>收藏</Text>
          </View>
          <View className='footer-btn'>
            <LucideIcon name='book-open' size={16} color='#666' />
            <Text>加入生词本</Text>
          </View>
        </View>
      </View>
    </View>
  )
}

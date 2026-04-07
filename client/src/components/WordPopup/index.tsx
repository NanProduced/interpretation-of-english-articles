import { useState, useEffect } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { InlineMarkModel, type DictionaryEntryPayload, type DictionaryResult } from '../../types/view/render-scene.vm'
import { fetchDict, fetchDictEntry } from '../../services/api/client'
import { dictResponseDtoToVm } from '../../services/api/adapters/dict.adapter'
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
  onAddVocab?: (word: string, dictResult: DictionaryResult | null) => void
  onFavorite?: (word: string) => void
}

function getEntrySummary(entry: DictionaryEntryPayload | null | undefined): string {
  if (!entry?.meanings?.length) return ''
  // 仅取首个义项的所有释义，分号拼接
  return entry.meanings[0]?.definitions
    ?.map((d) => d.meaning)
    .filter(Boolean)
    .join('；') || ''
}

export default function WordPopup({
  visible, mode = 'full', mark, word, x = 0, y = 0,
  onClose, onExpand, onAddVocab, onFavorite,
}: WordPopupProps) {
  const [dictResult, setDictResult] = useState<DictionaryResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [screenWidth, setScreenWidth] = useState(375)

  const lookupText = mark?.lookupText || word
  const lookupKind = mark?.lookupKind
  const glossary = mark?.glossary
  const examTags = mark?.examTags
  const entry = dictResult?.resultType === 'entry' ? dictResult.entry : null
  const detailMeanings = entry?.meanings || []
  const miniMeaning = getEntrySummary(entry)

  const shouldSkipDictFetch = mark?.annotationType === 'phrase_gloss' && glossary?.zh

  useEffect(() => {
    if (!visible || !lookupText) return
    if (shouldSkipDictFetch) return
    void fetchDictionary(lookupText)
  }, [visible, lookupText, shouldSkipDictFetch])

  useEffect(() => {
    Taro.getSystemInfo({}).then((info) => setScreenWidth(info.windowWidth || 375))
  }, [])

  const fetchDictionary = async (text: string) => {
    setLoading(true)
    setDictResult(null) // 清空旧数据，防止词头残留
    try {
      const dto = await fetchDict(text)
      setDictResult(dictResponseDtoToVm(dto))
    } catch (err) {
      console.error('[dict] fetch error', err)
      setDictResult(null)
    } finally {
      setLoading(false)
    }
  }

  const fetchEntryDetail = async (entryId: number, expand = false) => {
    setLoading(true)
    setDictResult(null) // 清空旧数据，防止词头残留
    try {
      const dto = await fetchDictEntry(entryId)
      setDictResult(dictResponseDtoToVm(dto))
      if (expand) onExpand?.()
    } catch {
      Taro.showToast({ title: '词条详情获取失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const handlePlayAudio = () => {
    Taro.showToast({ title: '暂无发音', icon: 'none' })
  }

  if (!visible) return null

  const isEntryResult = dictResult?.resultType === 'entry'
  const isDisambiguationResult = dictResult?.resultType === 'disambiguation'

  if (mode === 'mini') {
    const safeLeft = x > screenWidth - 260 ? screenWidth - 280 : Math.max(20, x - 130)
    const safeTop = y > 200 ? y - 160 : y + 40

    const popupStyle: React.CSSProperties = {
      position: 'fixed',
      left: `${safeLeft}px`,
      top: `${safeTop}px`,
      zIndex: 1000,
    }

    return (
      <View className='word-popup-overlay mini-overlay' onClick={onClose}>
        <View
          className='mini-word-card'
          style={popupStyle}
          onClick={(e) => {
            e.stopPropagation()
            // 无论是 entry 还是 disambiguation，点击卡片都允许展开
            onExpand?.()
          }}
        >
          <View className='mini-header'>
            <View className='mini-word-info'>
              <Text className='mini-word'>{entry?.word || lookupText}</Text>
              {entry?.phonetic && <Text className='mini-phonetic'>{entry.phonetic}</Text>}
            </View>
            <View className='mini-actions'>
              <View
                className='mini-icon-btn'
                onClick={(e) => {
                  e.stopPropagation()
                  handlePlayAudio()
                }}
              >
                <LucideIcon name='volume2' size={16} color='var(--text-sub)' />
              </View>
              <View
                className='mini-icon-btn'
                onClick={(e) => {
                  e.stopPropagation()
                  onFavorite?.(lookupText)
                  Taro.showToast({ title: '已收藏', icon: 'success', duration: 1200 })
                }}
              >
                <LucideIcon name='star' size={16} color='var(--text-sub)' />
              </View>
            </View>
          </View>

          <View className='mini-content'>
            {loading ? (
              <Text className='mini-loading'>查询中...</Text>
            ) : isEntryResult && entry && detailMeanings[0] ? (
              <View className='mini-def-row'>
                <Text className='mini-pos'>{detailMeanings[0].partOfSpeech}</Text>
                <Text className='mini-def' numberOfLines={1}>
                  {miniMeaning}
                </Text>
              </View>
            ) : isDisambiguationResult && dictResult.candidates.length ? (
              <View className='mini-disambiguation-list'>
                {dictResult.candidates.slice(0, 4).map((candidate) => (
                  <View
                    key={candidate.entryId}
                    className='mini-candidate-item'
                    onClick={(e) => {
                      e.stopPropagation()
                      void fetchEntryDetail(candidate.entryId, true)
                    }}
                  >
                    <View className='mini-candidate-header'>
                      <Text className='mini-candidate-label'>{candidate.label}</Text>
                      {candidate.partOfSpeech && <Text className='mini-pos'>{candidate.partOfSpeech}</Text>}
                    </View>
                    {candidate.preview && (
                      <Text className='mini-candidate-preview' numberOfLines={1}>
                        {candidate.preview}
                      </Text>
                    )}
                  </View>
                ))}
              </View>
            ) : (
              <Text className='mini-loading'>未找到释义</Text>
            )}
          </View>

          <View className='mini-footer'>
            <Text className='mini-hint'>
              {isDisambiguationResult 
                ? (dictResult.candidates.length > 4 ? '查看更多选项' : '选择词义') 
                : '点击查看详情'}
            </Text>
            <LucideIcon name='chevronRight' size={12} color='var(--text-muted)' />
          </View>
        </View>
      </View>
    )
  }

  return (
    <View className='word-popup-overlay' onClick={onClose}>
      <View className='word-popup-container' onClick={(e) => e.stopPropagation()}>
        <View className='popup-drag-handle' />
        <View className='popup-header'>
          <View className='word-info'>
            <View className='word-text-row'>
              <Text className='word-text'>{entry?.word || lookupText}</Text>
              {lookupKind && <Text className='word-kind-tag'>{lookupKind}</Text>}
            </View>
            <View className='word-sub-info'>
              {entry?.phonetic && <Text className='word-phonetic'>{entry.phonetic}</Text>}
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
            <View className='audio-btn-large' onClick={handlePlayAudio}>
              <LucideIcon name='volume2' size={24} color='var(--text-main)' />
            </View>
            <View className='popup-close-btn' onClick={onClose}>
              <LucideIcon name='x' size={24} color='var(--text-muted)' />
            </View>
          </View>
        </View>

        <ScrollView className='popup-scroll-content' scrollY>
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

          {loading ? (
            <View className='popup-loading-state'><Text>正在检索词库...</Text></View>
          ) : isDisambiguationResult ? (
            <View className='dict-entries'>
              <View className='disambiguation-title'>
                <Text className='disambiguation-text'>该词有多个义项，请选择：</Text>
              </View>
              {dictResult.candidates.map((candidate) => (
                <View
                  key={candidate.entryId}
                  className='meaning-block clickable'
                  onClick={() => void fetchEntryDetail(candidate.entryId)}
                >
                  <View className='pos-tag'>{candidate.partOfSpeech || candidate.entryKind}</View>
                  <View className='definition-list'>
                    <View className='def-item'>
                      <Text className='def-en-example'>{candidate.label}</Text>
                      {candidate.preview && <Text className='def-zh'>{candidate.preview}</Text>}
                    </View>
                  </View>
                  <LucideIcon name='chevronRight' size={16} color='#ccc' />
                </View>
              ))}
            </View>
          ) : isEntryResult && entry ? (
            <View className='dict-entries'>
              {detailMeanings.map((meaning, idx) => (
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
              {entry.examples.length ? (
                <View className='meaning-block'>
                  <View className='pos-tag'>例句</View>
                  <View className='definition-list'>
                    {entry.examples.map((example, idx) => (
                      <View key={idx} className='def-item'>
                        <Text className='def-en-example'>"{example.example}"</Text>
                        {example.exampleTranslation && (
                          <Text className='def-zh'>{example.exampleTranslation}</Text>
                        )}
                      </View>
                    ))}
                  </View>
                </View>
              ) : null}
              {entry.phrases.length ? (
                <View className='meaning-block'>
                  <View className='pos-tag'>短语</View>
                  <View className='definition-list'>
                    {entry.phrases.map((phrase, idx) => (
                      <View key={idx} className='def-item'>
                        <Text className='def-en-example'>{phrase.phrase}</Text>
                        {phrase.meaning && <Text className='def-zh'>{phrase.meaning}</Text>}
                      </View>
                    ))}
                  </View>
                </View>
              ) : null}
            </View>
          ) : !loading && (
            <View className='popup-empty-state'>
              <LucideIcon name='searchX' size={48} color='var(--text-muted)' />
              <Text className='empty-text'>未找到词条释义</Text>
            </View>
          )}
        </ScrollView>

        <View className='popup-footer-actions safe-area-bottom'>
          <View
            className='footer-action-btn secondary'
            onClick={() => {
              onFavorite?.(entry?.word || lookupText)
              Taro.showToast({ title: '已收藏', icon: 'success', duration: 1200 })
            }}
          >
            <LucideIcon name='star' size={18} color='var(--text-sub)' />
            <Text className='btn-text'>收藏</Text>
          </View>
          {isEntryResult && entry && entry.id > 0 ? (
            <View
              className='footer-action-btn primary'
              onClick={() => {
                onAddVocab?.(entry.word, dictResult)
                Taro.showToast({ title: '已记入生词本', icon: 'success', duration: 1500 })
              }}
            >
              <LucideIcon name='plus' size={18} color='#fff' />
              <Text className='btn-text'>记入生词本</Text>
            </View>
          ) : null}
        </View>
      </View>
    </View>
  )
}

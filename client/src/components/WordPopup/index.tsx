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
  return entry.meanings[0]?.definitions
    ?.map((d) => d.meaning)
    .filter(Boolean)
    .join('；') || ''
}

const TONE_META: Record<VisualTone, { label: string; color: string; bg: string }> = {
  vocab: { label: '核心词汇', color: '#B45309', bg: '#FFD166' },
  phrase: { label: '核心短语', color: '#6D28D9', bg: '#B2A4FF' },
  context: { label: '语境释义', color: '#0369A1', bg: '#90E0EF' },
  grammar: { label: '语法解析', color: '#047857', bg: '#6EE7B7' },
}

export default function WordPopup({
  visible, mode = 'mini', mark, word, x = 0, y = 0,
  onClose, onExpand, onAddVocab, onFavorite,
}: WordPopupProps) {
  const [dictResult, setDictResult] = useState<DictionaryResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [screenWidth, setScreenWidth] = useState(375)

  const lookupText = mark?.lookupText || word
  const glossary = mark?.glossary
  const toneMeta = mark ? TONE_META[mark.visualTone] : null
  const entry = dictResult?.resultType === 'entry' ? dictResult.entry : null
  const detailMeanings = entry?.meanings || []
  const miniMeaning = glossary?.zh || glossary?.gloss || getEntrySummary(entry)

  const isLLMAnnotated = !!glossary

  useEffect(() => {
    if (!visible || !lookupText) return
    // 如果是短语且已有 AI 释义，仍建议拉取词典以备展开查看更多例句
    void fetchDictionary(lookupText)
  }, [visible, lookupText])

  useEffect(() => {
    Taro.getSystemInfo({}).then((info) => setScreenWidth(info.windowWidth || 375))
  }, [])

  const fetchDictionary = async (text: string) => {
    setLoading(true)
    setDictResult(null)
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
    setDictResult(null)
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
    // 定位逻辑优化：强制居中于点击点上方，处理边缘溢出
    const popupWidth = 240
    const popupHeight = 120
    const offset = 12

    let left = x - popupWidth / 2
    let top = y - popupHeight - offset
    let isFlipped = false

    // 边缘处理
    if (left < 10) left = 10
    if (left + popupWidth > screenWidth - 10) left = screenWidth - popupWidth - 10
    
    // 如果上方不够（考虑状态栏和导航栏高度，通常 80px 足够），翻转到下方
    if (top < 80) {
      top = y + offset
      isFlipped = true
    }

    const popupStyle: React.CSSProperties = {
      position: 'fixed',
      left: `${left}px`,
      top: `${top}px`,
      zIndex: 1000,
    }

    return (
      <View className='word-popup-overlay mini-overlay' onClick={onClose}>
        <View
          className={`mini-word-card ${isLLMAnnotated ? 'is-ai' : ''} ${isFlipped ? 'is-flipped' : ''}`}
          style={popupStyle}
          onClick={(e) => {
            e.stopPropagation()
            onExpand?.()
          }}
        >
          <View className='mini-header'>
            <View className='mini-word-info'>
              <Text className='mini-word'>{entry?.word || lookupText}</Text>
              {isLLMAnnotated && toneMeta && (
                <View 
                  className='ai-tag' 
                  style={{ backgroundColor: toneMeta.bg, color: toneMeta.color }}
                >
                  {toneMeta.label.slice(0, 2)}
                </View>
              )}
            </View>
            <LucideIcon name='chevron-right' size={14} color='var(--text-muted)' />
          </View>

          <View className='mini-content'>
            {loading && !miniMeaning ? (
              <Text className='mini-loading'>查询中...</Text>
            ) : miniMeaning ? (
              <View className='mini-def-row'>
                {!isLLMAnnotated && entry?.primaryPos && <Text className='mini-pos'>{entry.primaryPos}</Text>}
                <Text 
                  className={`mini-def ${isLLMAnnotated ? 'is-ai-def' : ''}`} 
                  style={isLLMAnnotated && toneMeta ? { color: toneMeta.color } : {}}
                  numberOfLines={2}
                >
                  {miniMeaning}
                </Text>
              </View>
            ) : isDisambiguationResult ? (
              <View className='mini-disambiguation-hint'>
                <LucideIcon name='list' size={12} color='var(--color-primary)' />
                <Text className='mini-def'>该词有多个义项，点击查看</Text>
              </View>
            ) : (
              <Text className='mini-loading'>未找到释义</Text>
            )}
          </View>
          
          <View 
            className='mini-arrow' 
            style={{ 
              left: `${Math.max(20, Math.min(popupWidth - 20, x - left))}px`
            }} 
          />
        </View>
      </View>
    )
  }

  return (
    <View className='word-popup-overlay full-overlay' onClick={onClose}>
      <View className='word-popup-container' onClick={(e) => e.stopPropagation()}>
        <View className='popup-drag-handle' />
        <View className='popup-header'>
          <View className='word-info'>
            <View className='word-text-row'>
              <Text className='word-text'>{entry?.word || lookupText}</Text>
              {isLLMAnnotated && toneMeta && (
                <View 
                  className='ai-badge'
                  style={{ backgroundColor: `color-mix(in srgb, ${toneMeta.bg}, transparent 80%)`, color: toneMeta.color, borderColor: toneMeta.bg }}
                >
                  {toneMeta.label}
                </View>
              )}
            </View>
            <View className='word-sub-info'>
              {entry?.phonetic && (
                <View className='phonetic-row'>
                  <LucideIcon name='volume-2' size={14} color='var(--text-muted)' />
                  <Text className='word-phonetic'>/{entry.phonetic}/</Text>
                </View>
              )}
            </View>
          </View>
          <View className='header-right-actions'>
            <View className='popup-close-btn' onClick={onClose}>
              <LucideIcon name='x' size={24} color='var(--text-muted)' />
            </View>
          </View>
        </View>

        <ScrollView className='popup-scroll-content' scrollY>
          {glossary && (
            <View 
              className='glossary-section highlighted-ai'
              style={{ '--ai-accent': toneMeta?.color ?? 'var(--color-primary)' } as any}
            >
              <View className='section-title'>
                <LucideIcon name='sparkles' size={14} color={toneMeta?.color ?? 'var(--color-primary)'} />
                <Text>{toneMeta ? `AI ${toneMeta.label}` : 'AI 解析'}</Text>
              </View>
              <View className='glossary-content'>
                <Text className='glossary-zh' style={{ color: toneMeta?.color }}>{glossary.zh || glossary.gloss}</Text>
                {glossary.reason && <Text className='glossary-reason'>{glossary.reason}</Text>}
              </View>
            </View>
          )}

          <View className='dict-section'>
            <View className='section-title'>
              <LucideIcon name='book' size={14} color='var(--text-sub)' />
              <Text>词典详细释义</Text>
            </View>

            {loading ? (
              <View className='popup-loading-state'><Text>正在检索词库...</Text></View>
            ) : isDisambiguationResult ? (
              <View className='disambiguation-list'>
                {dictResult.candidates.map((candidate) => (
                  <View
                    key={candidate.entryId}
                    className='candidate-item'
                    onClick={() => void fetchEntryDetail(candidate.entryId)}
                  >
                    <View className='candidate-main'>
                      <Text className='candidate-label'>{candidate.label}</Text>
                      {candidate.partOfSpeech && <Text className='candidate-pos'>{candidate.partOfSpeech}</Text>}
                    </View>
                    {candidate.preview && <Text className='candidate-preview'>{candidate.preview}</Text>}
                    <LucideIcon name='chevron-right' size={16} color='#ccc' />
                  </View>
                ))}
              </View>
            ) : isEntryResult && entry ? (
              <View className='meanings-list'>
                {detailMeanings.map((meaning, idx) => (
                  <View key={idx} className='meaning-item'>
                    <Text className='pos-tag'>{meaning.partOfSpeech}</Text>
                    <View className='definitions'>
                      {meaning.definitions.map((def, defIdx) => (
                        <View key={defIdx} className='def-row'>
                          <Text className='def-text'>{def.meaning}</Text>
                          {def.example && (
                            <View className='def-example-block'>
                              <Text className='def-example-en'>{def.example}</Text>
                              {def.exampleTranslation && <Text className='def-example-zh'>{def.exampleTranslation}</Text>}
                            </View>
                          )}
                        </View>
                      ))}
                    </View>
                  </View>
                ))}
              </View>
            ) : !loading && (
              <View className='popup-empty-state'>
                <Text className='empty-text'>未找到更多词条释义</Text>
              </View>
            )}
          </View>
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
            <Text>收藏</Text>
          </View>
          {isEntryResult && entry && entry.id > 0 ? (
            <View
              className='footer-action-btn primary'
              onClick={() => {
                onAddVocab?.(entry.word, dictResult)
              }}
            >
              <LucideIcon name='plus' size={18} color='var(--color-white)' />
              <Text>记入生词本</Text>
            </View>
          ) : null}
        </View>
      </View>
    </View>
  )
}

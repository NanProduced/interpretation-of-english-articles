import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { AnyInlineMarkModel, type VisualTone, type AcademicVisualTone, type InlineGlossary, type AcademicInlineGlossary, type DictionaryEntryPayload, type DictionaryResult } from '../../types/view/render-scene.vm'
import { fetchDict, fetchDictEntry } from '../../services/api/client'
import { dictResponseDtoToVm } from '../../services/api/adapters/dict.adapter'
import { getDictCache, setDictCache, getEntryCache, setEntryCache } from '../../services/dictCache'
import { filterExamTags } from '../../config/purpose'
import LucideIcon from '../LucideIcon'
import AnnotationGlyph from '../AnnotationGlyph'
import DictionaryFeedback from '../DictionaryFeedback'
import { getLookupSaveState, getSaveActionCopy } from './lookupSaveState'
import './index.scss'

interface WordPopupProps {
  visible: boolean
  mode?: 'mini' | 'full'
  mark: AnyInlineMarkModel | null
  word: string
  contextSentence?: string
  occurrence?: number
  x?: number
  y?: number
  readingVariant?: string
  readingGoal?: string
  cloudId?: string
  isSaved?: boolean
  savedMasteryStatus?: string
  onClose: () => void
  onExpand?: () => void
  onAddVocab?: (word: string, dictResult: DictionaryResult | null) => void
}

interface AudioVariant {
  label: string
  url: string
}

type HeightTier = 'compact' | 'standard' | 'rich' | 'expanded'

function getEntrySummary(entry: DictionaryEntryPayload | null | undefined): string {
  if (!entry?.meanings?.length) {
    if (entry?.entryKind === 'fragment' && entry.baseWord) {
      return `派生词，详见 ${entry.baseWord}`
    }
    return ''
  }
  return entry.meanings
    .map((m) => {
      const firstDef = m.definitions?.[0]?.meaning
      if (!firstDef) return null
      return m.partOfSpeech ? `${m.partOfSpeech} ${firstDef}` : firstDef
    })
    .filter(Boolean)
    .join('；')
}

function isLearningGlossary(g: InlineGlossary | AcademicInlineGlossary | undefined): g is InlineGlossary {
  return !!g && ('gloss' in g || 'reason' in g || 'phraseType' in g)
}

const TONE_META: Record<VisualTone | AcademicVisualTone, { label: string; color: string; bg: string }> = {
  vocab: { label: '词汇', color: 'var(--tone-vocab-color)', bg: 'var(--tone-vocab-bg)' },
  phrase: { label: '短语', color: 'var(--tone-phrase-color)', bg: 'var(--tone-phrase-bg)' },
  context: { label: '语境', color: 'var(--tone-context-color)', bg: 'var(--tone-context-bg)' },
  grammar: { label: '语法', color: 'var(--tone-grammar-color)', bg: 'var(--tone-grammar-bg)' },
  term: { label: '术语', color: 'var(--tone-term-color)', bg: 'var(--tone-term-bg)' },
  logic: { label: '逻辑', color: 'var(--tone-logic-color)', bg: 'var(--tone-logic-bg)' },
}

const PHRASE_KIND_LABELS: Record<string, string> = {
  phrase: '短语',
  collocation: '固定搭配',
  phrasal_verb: '动词短语',
  idiom: '习语',
  proper_noun: '专有名词',
  compound: '复合概念',
}

const MINI_LABEL_MAP: Record<string, string> = {
  vocab: '词汇',
  context: '语境',
  phrase: '短语',
  collocation: '搭配',
  phrasal_verb: '短语',
  idiom: '习语',
  proper_noun: '专名',
  compound: '复合',
  term: '术语',
  logic: '逻辑',
}

function WordLookupSlip({
  lookupText,
  dictResult,
  loading,
  miniMeaning,
  miniLabel,
  isLLMAnnotated,
  isDisambiguationResult,
  isSavedState,
  saveBtnCopy,
  mark,
  x,
  y,
  screenWidth,
  screenHeight,
  audioVariants,
  audioPlayingUrl,
  onPlayAudio,
  onClose,
  onExpand,
  onAddVocab,
}: {
  lookupText: string
  dictResult: DictionaryResult | null
  loading: boolean
  miniMeaning?: string
  miniLabel: string
  isLLMAnnotated: boolean
  isDisambiguationResult: boolean
  isSavedState: boolean
  saveBtnCopy: string
  mark: AnyInlineMarkModel | null
  x: number
  y: number
  screenWidth: number
  screenHeight: number
  audioVariants: AudioVariant[]
  audioPlayingUrl: string | null
  onPlayAudio: (url: string) => void
  onClose: () => void
  onExpand?: () => void
  onAddVocab?: (word: string, dictResult: DictionaryResult | null) => void
}) {
  const popupWidth = (screenWidth * 408) / 750
  const offset = 18
  let left = x - popupWidth / 2
  let top = y + offset
  let isFlipped = false

  if (left < 20) left = 20
  if (left + popupWidth > screenWidth - 20) left = screenWidth - popupWidth - 20
  
  if (y + 300 > screenHeight) {
    top = y - offset
    isFlipped = true
  }

  const popupStyle: React.CSSProperties = {
    position: 'fixed',
    left: `${left}px`,
    top: `${top}px`,
    zIndex: 1000,
    width: `${popupWidth}px`,
    transform: isFlipped ? 'translateY(-100%)' : 'none',
  }

  const entry = dictResult?.resultType === 'entry' ? dictResult.entry : null
  const headword = entry?.word || lookupText

  return (
    <View className='word-popup-overlay mini-overlay' onClick={onClose} catchMove>
      <View
        className={`mini-word-card ${isLLMAnnotated ? 'is-ai' : ''} ${isFlipped ? 'is-flipped' : ''}`}
        style={popupStyle}
      >
        <View className='mini-main-content' onClick={(e) => {
          e.stopPropagation()
          onExpand?.()
        }}>
          <View className='mini-header'>
            <Text className='mini-word'>{headword}</Text>
          </View>
          
          {(entry?.phonetic || audioVariants.length > 0 || (isLLMAnnotated && mark)) && (
            <View className='mini-sub-info'>
              {(entry?.phonetic || audioVariants.length > 0) && (
                <View className='mini-phonetic-row'>
                  {entry?.phonetic && (
                    <Text className='mini-phonetic'>/{entry.phonetic}/</Text>
                  )}
                  {audioVariants.map((v) => (
                    <View
                      key={v.url}
                      className={`mini-audio-btn ${audioPlayingUrl === v.url ? 'is-playing' : ''}`}
                      onClick={(e) => {
                        e.stopPropagation()
                        onPlayAudio(v.url)
                      }}
                    >
                      <LucideIcon name={audioPlayingUrl === v.url ? 'volume-1' : 'volume-2'} size={14} color='var(--reader-muted)' />
                      {v.label && <Text className='mini-audio-label'>{v.label}</Text>}
                    </View>
                  ))}
                </View>
              )}
              {isLLMAnnotated && mark && (
                <View className='ai-tag'>
                  <AnnotationGlyph type={mark.visualTone as any} size='sm' state='active' />
                  <Text className='ai-tag-text'>{miniLabel}</Text>
                </View>
              )}
            </View>
          )}

          <View className='mini-content'>
            {loading && !miniMeaning ? (
              <View>
                <View className='mini-skeleton-line' />
                <View className='mini-skeleton-line' />
              </View>
            ) : (
              <View className='mini-def-row'>
                <Text 
                  className={`mini-def ${isLLMAnnotated ? 'is-ai-def' : ''}`} 
                  numberOfLines={2}
                >
                  {miniMeaning || (isDisambiguationResult ? '多个义项，点击查看' : '暂未找到稳定释义，查看上下文')}
                </Text>
              </View>
            )}
          </View>
        </View>

        {entry && entry.id > 0 && (
          <View 
            className={`mini-action-bar ${isSavedState ? 'saved' : 'not-saved'}`}
            onClick={(e) => {
              e.stopPropagation()
              onAddVocab?.(entry.word, dictResult)
            }}
          >
            <View className='mini-action-left'>
              <AnnotationGlyph type='saved_vocab' size={24} state={isSavedState ? 'active' : 'default'} />
              <Text className='mini-action-text'>{saveBtnCopy}</Text>
            </View>
            <LucideIcon name='chevron-right' size={14} color={isSavedState ? 'var(--reader-subtle)' : 'var(--reader-muted)'} />
          </View>
        )}

        <View className='mini-arrow' style={{ left: `${Math.max(20, Math.min(popupWidth - 20, x - left))}px` }} />
      </View>
    </View>
  )
}

function DictionaryNoteSheet({
  lookupText,
  dictResult,
  loading,
  glossary,
  mark,
  professionalLabel,
  contextSentence,
  readingGoal,
  readingVariant,
  activeTab,
  isSavedState,
  saveBtnCopy,
  audioVariants,
  audioPlayingUrl,
  onPlayAudio,
  setActiveTab,
  onClose,
  onAddVocab,
  onSelectEntry,
  setShowDictFeedback,
  renderContextExcerpt,
}: {
  lookupText: string
  dictResult: DictionaryResult | null
  loading: boolean
  glossary: InlineGlossary | AcademicInlineGlossary | undefined
  mark: AnyInlineMarkModel | null
  professionalLabel: string
  contextSentence?: string
  readingGoal?: string
  readingVariant?: string
  activeTab: string
  isSavedState: boolean
  saveBtnCopy: string
  audioVariants: AudioVariant[]
  audioPlayingUrl: string | null
  onPlayAudio: (url: string) => void
  setActiveTab: (tab: 'meanings' | 'phrases' | 'examples') => void
  onClose: () => void
  onAddVocab?: (word: string, dictResult: DictionaryResult | null) => void
  onSelectEntry?: (entryId: number) => void
  setShowDictFeedback: (v: boolean) => void
  renderContextExcerpt: () => React.ReactNode
}) {
  const entry = dictResult?.resultType === 'entry' ? dictResult.entry : null
  const detailMeanings = entry?.meanings || []
  const isDisambiguationResult = dictResult?.resultType === 'disambiguation'
  const isEntryResult = dictResult?.resultType === 'entry'

  // Gesture state for swipe-to-close
  const [dragY, setDragY] = useState(0)
  const startYRef = useRef(0)
  const isDraggingRef = useRef(false)

  const handleTouchStart = (e: any) => {
    startYRef.current = e.touches[0].clientY
    isDraggingRef.current = true
  }

  const handleTouchMove = (e: any) => {
    if (!isDraggingRef.current) return
    const currentY = e.touches[0].clientY
    const deltaY = currentY - startYRef.current
    if (deltaY > 0) {
      setDragY(deltaY)
    }
  }

  const handleTouchEnd = () => {
    if (!isDraggingRef.current) return
    isDraggingRef.current = false
    if (dragY > 80) {
      onClose()
    } else {
      setDragY(0)
    }
  }

  // Tier Logic: Calculate preferred initial height based on content
  const heightTier: HeightTier = useMemo(() => {
    if (loading) return 'compact'
    if (isDisambiguationResult) return 'compact'
    if (!entry) return 'compact'
    
    let score = 0
    if (contextSentence) score += 2
    if (glossary) score += 3
    if (entry.meanings?.length) score += entry.meanings.length * 2
    if (entry.phrases?.length) score += 2
    if (entry.examples?.length) score += 2
    
    if (score <= 4) return 'compact'
    if (score <= 10) return 'standard'
    return 'rich'
  }, [entry, loading, isDisambiguationResult, contextSentence, glossary])

  const showFooter = isEntryResult && entry && entry.id > 0

  return (
    <View className='word-popup-overlay full-overlay' onClick={onClose} catchMove>
      <View 
        className={`word-popup-container tier-${heightTier}`}
        onClick={(e) => e.stopPropagation()}
        style={{ 
          transform: dragY > 0 ? `translateY(${dragY}px)` : '',
          transition: dragY > 0 ? 'none' : 'transform 0.28s var(--ease-reader-out)'
        }}
      >
        <View 
          className='popup-header-touch-area'
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        >
          <View className='popup-drag-handle' />
          <View className='popup-header'>
            <View className='word-info'>
              <View className='word-text-row'>
                <Text className='word-text'>{entry?.word || lookupText}</Text>
              </View>
              <View className='word-sub-info'>
                {entry?.phonetic && (
                  <View className='phonetic-row'>
                    <Text className='word-phonetic'>/{entry.phonetic}/</Text>
                  </View>
                )}
                {audioVariants.length > 0 && (
                  <View className='audio-variants-row'>
                    {audioVariants.map((v) => (
                      <View
                        key={v.url}
                        className={`audio-variant-btn ${audioPlayingUrl === v.url ? 'is-playing' : ''}`}
                        onClick={() => onPlayAudio(v.url)}
                      >
                        <LucideIcon name={audioPlayingUrl === v.url ? 'volume-1' : 'volume-2'} size={16} color='var(--reader-muted)' />
                        {v.label && <Text className='audio-variant-label'>{v.label}</Text>}
                      </View>
                    ))}
                  </View>
                )}
                {readingGoal === 'exam' && entry?.tags && entry.tags.length > 0 && (() => {
                  const filtered = filterExamTags(entry.tags, readingVariant)
                  return filtered.length > 0 ? (
                    <View className='exam-tags-row'>
                      {filtered.map(tag => (
                        <Text key={tag} className='exam-tag-pill'>{tag}</Text>
                      ))}
                    </View>
                  ) : null
                })()}
              </View>
            </View>
            <View className='header-right-actions'>
              <View className='popup-close-btn' onClick={onClose}>
                <LucideIcon name='x' size={24} color='var(--reader-ink)' />
              </View>
            </View>
          </View>
        </View>

        <ScrollView className='popup-scroll-content' scrollY style={{ flex: 1, height: '1px' }}>
          
          {contextSentence && (
            <View className='context-section'>
              <View className='section-title'>
                <LucideIcon name='bookOpen' size={24} color='var(--reader-muted)' />
                <Text>来源语境</Text>
              </View>
              {renderContextExcerpt()}
            </View>
          )}

          {glossary && (
            <View className='glossary-section'>
              <View className='section-title'>
                <AnnotationGlyph type={mark?.visualTone as any || 'context'} size='sm' state='active' />
                <Text>语境解析 · {professionalLabel}</Text>
              </View>
              <View className='glossary-content'>
                <View className='glossary-main-zh'>
                  <Text className='zh-text'>{glossary.zh || (isLearningGlossary(glossary) ? glossary.gloss : '')}</Text>
                </View>
                {isLearningGlossary(glossary) && glossary.reason && (
                  <View className='glossary-reason-box'>
                    <Text className='reason-text'>{glossary.reason}</Text>
                  </View>
                )}
              </View>
            </View>
          )}

          <View className='dict-section'>
            <View className='section-title-row'>
              <View className='section-title'>
                <Text>通用释义</Text>
              </View>
              {isEntryResult && entry && (entry.phrases?.length > 0 || entry.examples?.length > 0) && (
                <View className='dict-tabs'>
                  <View className={`dict-tab ${activeTab === 'meanings' ? 'active' : ''}`} onClick={() => setActiveTab('meanings')}>释义</View>
                  {entry.phrases?.length > 0 && <View className={`dict-tab ${activeTab === 'phrases' ? 'active' : ''}`} onClick={() => setActiveTab('phrases')}>短语</View>}
                  {entry.examples?.length > 0 && <View className={`dict-tab ${activeTab === 'examples' ? 'active' : ''}`} onClick={() => setActiveTab('examples')}>例句</View>}
                </View>
              )}
            </View>

            {loading && !isDisambiguationResult ? (
              <View className='popup-loading-state'>
                <View className='sheet-skeleton-line' style={{ width: '60%', marginBottom: '16rpx' }} />
                <View className='sheet-skeleton-line' style={{ width: '100%', marginBottom: '16rpx' }} />
                <View className='sheet-skeleton-line' style={{ width: '80%' }} />
              </View>
            ) : isDisambiguationResult ? (
              <View className='disambiguation-list'>
                {loading && (
                  <View className='disambiguation-loading-overlay'>
                    <View className='loading-spinner' />
                  </View>
                )}
                {dictResult.candidates.map((candidate) => (
                  <View
                    key={candidate.entryId}
                    className={`candidate-item ${loading ? 'is-loading' : ''}`}
                    onClick={() => {
                      if (loading) return
                      onSelectEntry?.(candidate.entryId)
                    }}
                  >
                    <View className='candidate-main'>
                      <View className='candidate-title-row'>
                        <Text className='candidate-label'>{candidate.label}</Text>
                        {candidate.partOfSpeech && <Text className='candidate-pos'>{candidate.partOfSpeech}</Text>}
                      </View>
                      {candidate.preview && <View className='candidate-preview'>{candidate.preview}</View>}
                    </View>
                    <LucideIcon name='chevron-right' size={16} color='var(--reader-muted)' />
                  </View>
                ))}
              </View>
            ) : isEntryResult && entry ? (
              <View className='dict-content-area'>
                {activeTab === 'meanings' && (
                  <View className='meanings-list'>
                    {detailMeanings.map((meaning, idx) => (
                      <View key={`${meaning.partOfSpeech}-${idx}`} className='meaning-item'>
                        <View className='pos-column'>
                          {meaning.partOfSpeech && <Text className='pos-tag'>{meaning.partOfSpeech}</Text>}
                        </View>
                        <View className='definitions'>
                          {meaning.definitions.map((def, defIdx) => (
                            <View key={`${def.meaning?.slice(0, 20)}-${defIdx}`} className='def-row'>
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
                )}
                {activeTab === 'phrases' && (
                  <View className='phrases-list'>
                    {entry.phrases.map((p, idx) => (
                      <View key={p.phrase} className='phrase-item'>
                        <View className='phrase-text'>{p.phrase}</View>
                        {p.meaning && <View className='phrase-meaning'>{p.meaning}</View>}
                      </View>
                    ))}
                  </View>
                )}
                {activeTab === 'examples' && (
                  <View className='examples-list'>
                    {entry.examples.map((ex, idx) => (
                      <View key={`${ex.example?.slice(0, 20)}-${idx}`} className='example-item'>
                        <View className='example-en'>{ex.example}</View>
                        {ex.exampleTranslation && <View className='example-zh'>{ex.exampleTranslation}</View>}
                      </View>
                    ))}
                  </View>
                )}
              </View>
            ) : !loading && (
              <View className='popup-empty-state'>
                <Text className='empty-text'>
                  {entry?.entryKind === 'fragment' ? '派生词，查看主词条' : '未找到词条释义'}
                </Text>
              </View>
            )}
          </View>
        </ScrollView>

        <View className={`popup-footer-actions safe-area-bottom ${showFooter ? 'has-footer' : 'no-footer'}`}>
          <View className='footer-action-btn secondary' onClick={() => setShowDictFeedback(true)}>
            <AnnotationGlyph type='feedback' size={32} state='default' />
            <Text>反馈</Text>
          </View>
          {showFooter && (
            <View 
              className={`footer-action-btn ${isSavedState ? 'saved' : 'primary'}`} 
              onClick={() => onAddVocab?.(entry!.word, dictResult)}
            >
              <AnnotationGlyph type='saved_vocab' size={36} state={isSavedState ? 'active' : 'default'} className={isSavedState ? '' : 'white-glyph'} />
              <Text>{saveBtnCopy}</Text>
            </View>
          )}
        </View>
      </View>
    </View>
  )
}

export default function WordPopup({
  visible, mode = 'mini', mark, word, contextSentence, occurrence, x = 0, y = 0, readingVariant, readingGoal,
  cloudId, isSaved = false, savedMasteryStatus, onClose, onExpand, onAddVocab,
}: WordPopupProps) {
  const [dictResult, setDictResult] = useState<DictionaryResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [screenWidth, setScreenWidth] = useState(375)
  const [screenHeight, setScreenHeight] = useState(667)
  const [activeTab, setActiveTab] = useState<'meanings' | 'phrases' | 'examples'>('meanings')
  const [showDictFeedback, setShowDictFeedback] = useState(false)
  const fetchVersionRef = useRef(0)
  const [audioVariants, setAudioVariants] = useState<AudioVariant[]>([])
  const [audioPlayingUrl, setAudioPlayingUrl] = useState<string | null>(null)
  const innerAudioRef = useRef<ReturnType<typeof Taro.createInnerAudioContext> | null>(null)

  const lookupText = mark?.lookupText || word
  const glossary = mark?.glossary
  const toneMeta = mark ? TONE_META[mark.visualTone] : null

  const effectivePhraseKind = isLearningGlossary(glossary) ? glossary.phraseType : undefined
  const effectiveLookupKind = 'lookupKind' in (mark ?? {}) ? mark!.lookupKind : undefined
  const professionalLabel = ((effectivePhraseKind || effectiveLookupKind) && PHRASE_KIND_LABELS[effectivePhraseKind || effectiveLookupKind || ''])
    ? PHRASE_KIND_LABELS[effectivePhraseKind || effectiveLookupKind || '']
    : (toneMeta?.label || 'AI 解析')

  const miniLabel = (effectivePhraseKind && MINI_LABEL_MAP[effectivePhraseKind])
    ? MINI_LABEL_MAP[effectivePhraseKind]
    : (mark ? MINI_LABEL_MAP[mark.visualTone] : 'AI')

  const entry = dictResult?.resultType === 'entry' ? dictResult.entry : null
  const miniMeaning = glossary?.zh || (isLearningGlossary(glossary) ? glossary.gloss : undefined) || getEntrySummary(entry)
  const isLLMAnnotated = !!glossary

  const renderContextExcerpt = () => {
    if (!contextSentence || !lookupText) return null
    const escaped = lookupText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const parts = contextSentence.split(new RegExp(`(${escaped})`, 'gi'))
    return (
      <View className='source-context-excerpt'>
        {parts.map((part, i) => 
          part.toLowerCase() === lookupText.toLowerCase() 
            ? <Text key={i} className='excerpt-highlight'>{part}</Text> 
            : <Text key={i}>{part}</Text>
        )}
      </View>
    )
  }

  const saveState = getLookupSaveState(lookupText, isSaved, undefined, savedMasteryStatus ? [{ status: savedMasteryStatus }] : undefined)
  const saveBtnCopy = getSaveActionCopy(saveState)
  const isSavedState = saveState !== 'not_saved'

  useEffect(() => {
    if (!visible) {
      setDictResult(null)
      setAudioVariants([])
      setAudioPlayingUrl(null)
      if (innerAudioRef.current) {
        innerAudioRef.current.destroy()
        innerAudioRef.current = null
      }
      return
    }
    if (!lookupText) return
    fetchVersionRef.current += 1
    const version = fetchVersionRef.current
    void fetchDictionary(lookupText, version)
  }, [visible, lookupText, contextSentence, occurrence])

  useEffect(() => {
    Taro.getSystemInfo({}).then((info) => {
      setScreenWidth(info.windowWidth || 375)
      setScreenHeight(info.windowHeight || 667)
    })
  }, [])

  const loadAudio = useCallback(async (wordToFetch: string) => {
    if (!wordToFetch || wordToFetch.trim().includes(' ')) return
    const audioVersion = fetchVersionRef.current
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000)
      const res = await fetch(`https://api.dictionaryapi.dev/api/v2/entries/en/${encodeURIComponent(wordToFetch)}`, {
        signal: controller.signal,
      })
      clearTimeout(timeoutId)
      if (audioVersion !== fetchVersionRef.current) return
      if (!res.ok) return
      const data = await res.json()
      if (audioVersion !== fetchVersionRef.current) return
      const phonetics = Array.isArray(data) ? data[0]?.phonetics : []
      if (!Array.isArray(phonetics)) return
      const variants: AudioVariant[] = []
      const seen = new Set<string>()
      for (const p of phonetics) {
        if (!p.audio || p.audio.trim() === '') continue
        let url = p.audio as string
        if (url.startsWith('//')) url = 'https:' + url
        if (seen.has(url)) continue
        seen.add(url)
        let label = 'US'
        if (url.includes('-uk.')) label = 'UK'
        else if (url.includes('-us.')) label = 'US'
        else if (url.includes('-au.')) label = 'AU'
        else label = ''
        variants.push({ label, url })
      }
      if (audioVersion !== fetchVersionRef.current) return
      if (variants.length > 0) {
        setAudioVariants(variants)
      }
    } catch {
      // silent fail
    }
  }, [])

  useEffect(() => {
    const isEntryResult = dictResult?.resultType === 'entry'
    if (isEntryResult && entry) {
      if (activeTab === 'phrases' && !entry.phrases?.length) setActiveTab('meanings')
      if (activeTab === 'examples' && !entry.examples?.length) setActiveTab('meanings')
    }
    if (isEntryResult && entry && audioVariants.length === 0) {
      loadAudio(entry.word)
    }
  }, [dictResult, activeTab, entry, audioVariants.length, loadAudio])

  const fetchDictionary = async (text: string, version: number) => {
    const type = text.trim().includes(' ') ? 'phrase' : 'word'
    const cached = getDictCache(text, type, contextSentence, occurrence)
    if (cached) {
      setDictResult(cached)
      setLoading(false)
      return
    }
    setLoading(true)
    setDictResult(null)
    try {
      const dto = await fetchDict(text, type, contextSentence, occurrence)
      if (version !== fetchVersionRef.current) return
      const vm = dictResponseDtoToVm(dto)
      setDictResult(vm)
      setDictCache(text, type, vm, contextSentence, occurrence)
    } catch (err) {
      if (version !== fetchVersionRef.current) return
      console.error('[dict] fetch error', err)
      setDictResult(null)
    } finally {
      if (version === fetchVersionRef.current) {
        setLoading(false)
      }
    }
  }

  const fetchEntryDetail = async (entryId: number, expand = false) => {
    const cached = getEntryCache(entryId)
    if (cached) {
      setDictResult(cached)
      if (expand) onExpand?.()
      return
    }
    setLoading(true)
    try {
      const dto = await fetchDictEntry(entryId)
      const vm = dictResponseDtoToVm(dto)
      setDictResult(vm)
      setEntryCache(entryId, vm)
      if (expand) onExpand?.()
    } catch {
      Taro.showToast({ title: '词条详情获取失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const playAudio = (url: string) => {
    if (audioPlayingUrl) return
    setAudioPlayingUrl(url)
    if (innerAudioRef.current) {
      innerAudioRef.current.destroy()
      innerAudioRef.current = null
    }
    const innerAudio = Taro.createInnerAudioContext()
    innerAudioRef.current = innerAudio
    innerAudio.src = url
    innerAudio.onEnded(() => {
      setAudioPlayingUrl(null)
      innerAudio.destroy()
      innerAudioRef.current = null
    })
    innerAudio.onError(() => {
      setAudioPlayingUrl(null)
      innerAudio.destroy()
      innerAudioRef.current = null
    })
    innerAudio.play()
  }

  if (!visible) return null

  const isDisambiguationResult = dictResult?.resultType === 'disambiguation'

  if (mode === 'mini') {
    return (
      <WordLookupSlip
        lookupText={lookupText}
        dictResult={dictResult}
        loading={loading}
        miniMeaning={miniMeaning}
        miniLabel={miniLabel}
        isLLMAnnotated={isLLMAnnotated}
        isDisambiguationResult={isDisambiguationResult}
        isSavedState={isSavedState}
        saveBtnCopy={saveBtnCopy}
        mark={mark}
        x={x}
        y={y}
        screenWidth={screenWidth}
        screenHeight={screenHeight}
        audioVariants={audioVariants}
        audioPlayingUrl={audioPlayingUrl}
        onPlayAudio={playAudio}
        onClose={onClose}
        onExpand={onExpand}
        onAddVocab={onAddVocab}
        onSelectEntry={fetchEntryDetail}
      />
    )
  }

  return (
    <>
      <DictionaryNoteSheet
        lookupText={lookupText}
        dictResult={dictResult}
        loading={loading}
        glossary={glossary}
        mark={mark}
        professionalLabel={professionalLabel}
        contextSentence={contextSentence}
        readingGoal={readingGoal}
        readingVariant={readingVariant}
        activeTab={activeTab}
        isSavedState={isSavedState}
        saveBtnCopy={saveBtnCopy}
        audioVariants={audioVariants}
        audioPlayingUrl={audioPlayingUrl}
        onPlayAudio={playAudio}
        setActiveTab={setActiveTab}
        onClose={onClose}
        onAddVocab={onAddVocab}
        onSelectEntry={fetchEntryDetail}
        setShowDictFeedback={setShowDictFeedback}
        renderContextExcerpt={renderContextExcerpt}
      />

      {showDictFeedback && (
        <View className='popup-feedback-overlay' onClick={() => setShowDictFeedback(false)}>
          <DictionaryFeedback
            word={lookupText}
            phonetic={entry?.phonetic}
            currentMeaning={getEntrySummary(entry) || undefined}
            dictSource='tecd3'
            dictEntryId={entry?.id}
            contextSentence={contextSentence}
            readingVariant={readingVariant}
            recordId={cloudId}
            onClose={() => setShowDictFeedback(false)}
          />
        </View>
      )}
    </>
  )
}

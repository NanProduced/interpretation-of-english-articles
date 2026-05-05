import { useState, useEffect } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { AnyInlineMarkModel, type VisualTone, type AcademicVisualTone, type InlineGlossary, type AcademicInlineGlossary, type DictionaryEntryPayload, type DictionaryResult } from '../../types/view/render-scene.vm'
import { fetchDict, fetchDictEntry } from '../../services/api/client'
import { dictResponseDtoToVm } from '../../services/api/adapters/dict.adapter'
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
  isSaved?: boolean
  onClose: () => void
  onExpand?: () => void
  onAddVocab?: (word: string, dictResult: DictionaryResult | null) => void
  onFavorite?: (word: string) => void
}

function getEntrySummary(entry: DictionaryEntryPayload | null | undefined): string {
  if (!entry?.meanings?.length) return ''
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

const TERM_CATEGORY_LABELS: Record<string, string> = {
  technical: '专业术语',
  sub_technical: '半技术词汇',
  abbreviation: '缩写',
  notation: '符号引用',
  concept_opposition: '概念对立',
}

const LOGIC_TYPE_LABELS: Record<string, string> = {
  contrast: '对比转折',
  causation: '因果关系',
  concession: '让步',
  condition: '条件假设',
  evidence: '证据支撑',
  elaboration: '阐释展开',
  transition: '过渡衔接',
  limitation: '限定',
  hypothesis: '假设',
  conclusion: '结论',
}

export default function WordPopup({
  visible, mode = 'mini', mark, word, contextSentence, occurrence, x = 0, y = 0, readingVariant,
  isSaved = false, onClose, onExpand, onAddVocab, onFavorite,
}: WordPopupProps) {
  const [dictResult, setDictResult] = useState<DictionaryResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [screenWidth, setScreenWidth] = useState(375)
  const [activeTab, setActiveTab] = useState<'meanings' | 'phrases' | 'examples'>('meanings')
  const [showDictFeedback, setShowDictFeedback] = useState(false)

  const lookupText = mark?.lookupText || word
  const glossary = mark?.glossary
  const toneMeta = mark ? TONE_META[mark.visualTone] : null

  const handleFavorite = () => {
    onFavorite?.(entry?.word || lookupText)
    Taro.showToast({ title: '已收藏', icon: 'success', duration: 1200 })
  }
  
  const effectivePhraseKind = isLearningGlossary(glossary) ? glossary.phraseType : undefined
  const effectiveLookupKind = 'lookupKind' in (mark ?? {}) ? mark!.lookupKind : undefined
  const professionalLabel = ((effectivePhraseKind || effectiveLookupKind) && PHRASE_KIND_LABELS[effectivePhraseKind || effectiveLookupKind || ''])
    ? PHRASE_KIND_LABELS[effectivePhraseKind || effectiveLookupKind || '']
    : (toneMeta?.label || 'AI 解析')

  const miniLabel = (effectivePhraseKind && MINI_LABEL_MAP[effectivePhraseKind])
    ? MINI_LABEL_MAP[effectivePhraseKind]
    : (mark ? MINI_LABEL_MAP[mark.visualTone] : 'AI')

  const entry = dictResult?.resultType === 'entry' ? dictResult.entry : null
  const detailMeanings = entry?.meanings || []
  const miniMeaning = glossary?.zh || (isLearningGlossary(glossary) ? glossary.gloss : undefined) || getEntrySummary(entry)
  const isLLMAnnotated = !!glossary

  // Render context excerpt with highlight
  const renderContextExcerpt = () => {
    if (!contextSentence || !lookupText) return null
    const parts = contextSentence.split(new RegExp(`(${lookupText})`, 'gi'))
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

  const saveState = getLookupSaveState(lookupText, isSaved)
  const saveBtnCopy = getSaveActionCopy(saveState)
  const isSavedState = saveState !== 'not_saved'

  // Hooks must ALWAYS be called in the same order. 
  // Conditional return must happen AFTER all hook declarations.

  useEffect(() => {
    if (!visible || !lookupText) return
    void fetchDictionary(lookupText)
  }, [visible, lookupText, contextSentence, occurrence])

  useEffect(() => {
    Taro.getSystemInfo({}).then((info) => setScreenWidth(info.windowWidth || 375))
  }, [])

  useEffect(() => {
    const isEntryResult = dictResult?.resultType === 'entry'
    if (isEntryResult && entry) {
      if (activeTab === 'phrases' && !entry.phrases?.length) setActiveTab('meanings')
      if (activeTab === 'examples' && !entry.examples?.length) setActiveTab('meanings')
    }
  }, [dictResult, activeTab]) // Fixed dependency

  const fetchDictionary = async (text: string) => {
    setLoading(true)
    setDictResult(null)
    try {
      const type = text.trim().includes(' ') ? 'phrase' : 'word'
      const dto = await fetchDict(text, type, contextSentence, occurrence)
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

  if (!visible) return null

  const isEntryResult = dictResult?.resultType === 'entry'
  const isDisambiguationResult = dictResult?.resultType === 'disambiguation'

  if (mode === 'mini') {
    const popupWidth = (screenWidth * 440) / 750
    const offset = 12
    let left = x - popupWidth / 2
    let top = y - offset
    let isFlipped = false

    if (left < 10) left = 10
    if (left + popupWidth > screenWidth - 10) left = screenWidth - popupWidth - 10
    if (y < 150) {
      top = y + offset
      isFlipped = true
    }

    const popupStyle: React.CSSProperties = {
      position: 'fixed',
      left: `${left}px`,
      top: `${top}px`,
      zIndex: 1000,
      width: `${popupWidth}px`,
      transform: isFlipped ? 'none' : 'translateY(-100%)',
    }

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
              <Text className='mini-word'>{entry?.word || lookupText}</Text>
              <LucideIcon name='chevron-right' size={16} color='var(--reader-muted)' />
            </View>
            
            {(entry?.phonetic || (isLLMAnnotated && mark)) && (
              <View className='mini-sub-info'>
                {entry?.phonetic && (
                  <View className='mini-phonetic-row'>
                    <LucideIcon name='volume-2' size={14} color='var(--reader-muted)' />
                    <Text className='mini-phonetic'>/{entry.phonetic}/</Text>
                  </View>
                )}
                {isLLMAnnotated && mark && (
                  <View className='ai-tag'>
                    {mark.visualTone === 'vocab' && <AnnotationGlyph type='vocab' size={16} state='active' />}
                    {mark.visualTone === 'phrase' && <AnnotationGlyph type='phrase' size={16} state='active' />}
                    {mark.visualTone === 'context' && <AnnotationGlyph type='context' size={16} state='active' />}
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
              ) : miniMeaning ? (
                <View className='mini-def-row'>
                  <Text 
                    className={`mini-def ${isLLMAnnotated ? 'is-ai-def' : ''}`} 
                    numberOfLines={2}
                  >
                    {miniMeaning}
                  </Text>
                </View>
              ) : isDisambiguationResult ? (
                <View className='mini-disambiguation-hint'>
                  <LucideIcon name='list' size={14} color='var(--reader-muted)' />
                  <Text className='mini-def'>多个义项，点击查看</Text>
                </View>
              ) : (
                <Text className='mini-loading'>未找到释义</Text>
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
                {!isSavedState && <LucideIcon name='bookmark' size={14} color='var(--reader-ink)' />}
                {isSavedState && <LucideIcon name='check' size={14} color='var(--reader-ink)' />}
                <Text className='mini-action-text'>{saveBtnCopy}</Text>
              </View>
              <LucideIcon name='chevron-right' size={14} color={isSavedState ? 'var(--reader-ink)' : 'var(--reader-muted)'} />
            </View>
          )}

          <View className='mini-arrow' style={{ left: `${Math.max(20, Math.min(popupWidth - 20, x - left))}px` }} />
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
            </View>
            <View className='word-sub-info'>
              {entry?.phonetic && (
                <View className='phonetic-row'>
                  <Text className='word-phonetic'>/{entry.phonetic}/</Text>
                </View>
              )}
            </View>
          </View>
          <View className='header-right-actions'>
            <View className='popup-close-btn' onClick={onClose}>
              <LucideIcon name='x' size={24} color='var(--reader-ink)' />
            </View>
          </View>
        </View>

        <ScrollView className='popup-scroll-content' scrollY style={{ flex: 1, height: '1px' }}>
          
          {contextSentence && renderContextExcerpt()}

          {glossary && (
            <View className='glossary-section'>
              <View className='section-title'>
                {mark?.visualTone === 'phrase' ? <AnnotationGlyph type='phrase' size={16} /> : <AnnotationGlyph type='context' size={16} />}
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

            {loading ? (
              <View className='popup-loading-state'>
                <View className='loading-spinner' />
              </View>
            ) : isDisambiguationResult ? (
              <View className='disambiguation-list'>
                {dictResult.candidates.map((candidate) => (
                  <View key={candidate.entryId} className='candidate-item' onClick={() => void fetchEntryDetail(candidate.entryId)}>
                    <View className='candidate-main'>
                      <View className='candidate-title-row'>
                        <Text className='candidate-label'>{candidate.label}</Text>
                        {candidate.partOfSpeech && <Text className='candidate-pos'>{candidate.partOfSpeech}</Text>}
                      </View>
                      {candidate.preview && <View className='candidate-preview'>{candidate.preview}</View>}
                    </View>
                  </View>
                ))}
              </View>
            ) : isEntryResult && entry ? (
              <View className='dict-content-area'>
                {activeTab === 'meanings' && (
                  <View className='meanings-list'>
                    {detailMeanings.map((meaning, idx) => (
                      <View key={idx} className='meaning-item'>
                        {meaning.partOfSpeech && <Text className='pos-tag'>{meaning.partOfSpeech}</Text>}
                        <View className='definitions'>
                          {meaning.definitions.map((def, defIdx) => (
                            <View key={defIdx} className='def-row'>
                              <View className='def-text'>{def.meaning}</View>
                              {def.example && (
                                <View className='def-example-block'>
                                  <View className='def-example-en'>{def.example}</View>
                                  {def.exampleTranslation && <View className='def-example-zh'>{def.exampleTranslation}</View>}
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
                      <View key={idx} className='phrase-item'>
                        <View className='phrase-text'>{p.phrase}</View>
                        {p.meaning && <View className='phrase-meaning'>{p.meaning}</View>}
                      </View>
                    ))}
                  </View>
                )}
                {activeTab === 'examples' && (
                  <View className='examples-list'>
                    {entry.examples.map((ex, idx) => (
                      <View key={idx} className='example-item'>
                        <View className='example-en'>{ex.example}</View>
                        {ex.exampleTranslation && <View className='example-zh'>{ex.exampleTranslation}</View>}
                      </View>
                    ))}
                  </View>
                )}
              </View>
            ) : !loading && (
              <View className='popup-empty-state'>
                <Text className='empty-text'>未找到词条释义</Text>
              </View>
            )}
          </View>
        </ScrollView>

        <View className='popup-footer-actions safe-area-bottom'>
          <View className='footer-action-btn secondary' onClick={() => setShowDictFeedback(true)}>
            <LucideIcon name='messageSquare' size={18} color='var(--reader-ink)' />
            <Text>反馈</Text>
          </View>
          {isEntryResult && entry && entry.id > 0 && (
            <View 
              className={`footer-action-btn ${isSavedState ? 'saved' : 'primary'}`} 
              onClick={() => onAddVocab?.(entry.word, dictResult)}
            >
              {!isSavedState && <LucideIcon name='plus' size={18} color='var(--reader-paper)' />}
              {isSavedState && <AnnotationGlyph type='saved_vocab' size={16} />}
              <Text>{saveBtnCopy}</Text>
            </View>
          )}
        </View>

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
              onClose={() => setShowDictFeedback(false)}
            />
          </View>
        )}
      </View>
    </View>
  )
}

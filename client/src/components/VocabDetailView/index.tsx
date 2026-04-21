import { View, Text, ScrollView } from '@tarojs/components'
import { useState, useEffect, useCallback } from 'react'
import Taro from '@tarojs/taro'
import type { VocabEntry, SourceRef } from '../../types/view/vocabulary.vm'
import type { DictionaryEntryPayload, DictionaryMeaning } from '../../types/view/render-scene.vm'
import { fetchDictEntry } from '../../services/api/client'
import { dictResponseDtoToVm } from '../../services/api/adapters/dict.adapter'
import { getRecord } from '../../services/storage'
import LucideIcon from '../LucideIcon'
import './index.scss'

interface VocabDetailViewProps {
  visible: boolean
  entry: VocabEntry | null
  onClose: () => void
  onGoToResult: (recordId: string, sentenceId?: string) => void
  onToggleMastery?: (entry: VocabEntry) => void
}

type DictTab = 'meanings' | 'phrases' | 'examples'

export default function VocabDetailView({
  visible,
  entry,
  onClose,
  onGoToResult,
  onToggleMastery,
}: VocabDetailViewProps) {
  const [dictEntry, setDictEntry] = useState<DictionaryEntryPayload | null>(null)
  const [dictLoading, setDictLoading] = useState(false)
  const [dictTab, setDictTab] = useState<DictTab>('meanings')
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [audioPlaying, setAudioPlaying] = useState(false)
  const [contextIndex, setContextIndex] = useState(0)

  const loadDictEntry = useCallback(async () => {
    if (!entry?.dictEntryId) {
      setDictEntry(null)
      return
    }
    setDictLoading(true)
    try {
      const dto = await fetchDictEntry(entry.dictEntryId)
      const vm = dictResponseDtoToVm(dto)
      if (vm.resultType === 'entry') {
        setDictEntry(vm.entry)
      }
    } catch {
      setDictEntry(null)
    } finally {
      setDictLoading(false)
    }
  }, [entry?.dictEntryId])

  const loadAudio = useCallback(async () => {
    if (!entry) return
    if (entry.audioUrl) {
      setAudioUrl(entry.audioUrl)
      return
    }
    const word = entry.lemma || entry.word
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000)
      const res = await fetch(`https://api.dictionaryapi.dev/api/v2/entries/en/${encodeURIComponent(word)}`, {
        signal: controller.signal,
      })
      clearTimeout(timeoutId)
      if (!res.ok) return
      const data = await res.json()
      const phonetics = Array.isArray(data) ? data[0]?.phonetics : []
      const withAudio = phonetics?.find((p: { audio?: string }) => p.audio && p.audio.trim() !== '')
      if (withAudio?.audio) {
        let url = withAudio.audio as string
        if (url.startsWith('//')) url = 'https:' + url
        setAudioUrl(url)
      }
    } catch (e) {
      console.error('VocabDetailView: audio fetch failed', e)
    }
  }, [entry])

  useEffect(() => {
    if (!visible || !entry) {
      setDictEntry(null)
      setAudioUrl(null)
      setContextIndex(0)
      setDictTab('meanings')
      return
    }
    loadDictEntry()
    loadAudio()
  }, [visible, entry, loadDictEntry, loadAudio])

  const playAudio = () => {
    if (!audioUrl || audioPlaying) return
    setAudioPlaying(true)
    const innerAudio = Taro.createInnerAudioContext()
    innerAudio.src = audioUrl
    innerAudio.onEnded(() => setAudioPlaying(false))
    innerAudio.onError(() => setAudioPlaying(false))
    innerAudio.play()
  }

  const handleGoToResult = (ref: SourceRef) => {
    if (!ref.clientRecordId) return
    const record = getRecord(ref.clientRecordId)
    if (!record || record.tombstone) {
      Taro.showToast({ title: '原文记录已删除或不可用', icon: 'none' })
      return
    }
    onGoToResult(ref.clientRecordId, ref.sourceSentenceId)
    onClose()
  }

  if (!visible || !entry) return null

  const sourceRefs = entry.sourceRefs || []
  const collectedForms = entry.collectedForms || []
  const displayMeanings: DictionaryMeaning[] =
    dictEntry?.meanings ||
    entry.detailMeanings?.map(m => ({
      partOfSpeech: m.pos,
      definitions: m.definitions.map(d => ({ meaning: d })),
    })) ||
    []

  const hasPhrases = dictEntry && dictEntry.phrases && dictEntry.phrases.length > 0
  const hasExamples = dictEntry && dictEntry.examples && dictEntry.examples.length > 0

  return (
    <View className='vocab-detail-overlay' onClick={onClose}>
      <View className='vocab-detail-container' onClick={(e) => e.stopPropagation()}>
        <View className='detail-drag-handle' onClick={onClose} />

        <ScrollView className='detail-scroll-content' scrollY enhanced showScrollbar={false}>

          {/* Hero */}
          <View className='detail-hero'>
            <View className='word-title-row'>
              <Text className='hero-word'>{entry.word}</Text>
              <View className='hero-actions'>
                {audioUrl && (
                  <View className='action-btn audio-btn' onClick={playAudio}>
                    <LucideIcon name={audioPlaying ? 'pause' : 'volume2'} size={22} color='var(--color-primary)' />
                  </View>
                )}
                <View className='action-btn' onClick={onClose}>
                  <LucideIcon name='x' size={24} color='var(--text-muted)' />
                </View>
              </View>
            </View>

            {(entry.phonetic || entry.lemma) && (
              <View className='hero-meta-row'>
                {entry.phonetic && <Text className='phonetic'>/{entry.phonetic}/</Text>}
                {entry.lemma && entry.lemma.toLowerCase() !== entry.word.toLowerCase() && (
                  <Text className='lemma'>原型: {entry.lemma}</Text>
                )}
              </View>
            )}

            {collectedForms.length > 0 && (
              <View className='hero-collected-forms'>
                <Text className='forms-label'>收藏形态:</Text>
                {collectedForms.map(f => (
                  <Text key={f} className='form-tag'>{f}</Text>
                ))}
              </View>
            )}

            {((entry.tags && entry.tags.length > 0) || (entry.exchange && entry.exchange.length > 0)) && (
              <View className='hero-tags'>
                {entry.tags?.map(t => (
                  <Text key={t} className='tag outline-tag'>{t}</Text>
                ))}
                {entry.exchange?.map(e => (
                  <Text key={e} className='tag gray-tag'>{e}</Text>
                ))}
              </View>
            )}
          </View>

          {/* Context Section */}
          {sourceRefs.length > 0 && (
            <View className='context-section'>
              <View className='section-header'>
                <Text className='section-label'>语境来源</Text>
                {sourceRefs.length > 1 && (
                  <Text className='context-counter'>{contextIndex + 1}/{sourceRefs.length}</Text>
                )}
              </View>

              <ScrollView
                className='context-cards-scroll'
                scrollX
                enhanced
                showScrollbar={false}
                scrollIntoView={`ctx-${contextIndex}`}
                scrollWithAnimation
              >
                {sourceRefs.map((ref, idx) => (
                  <View
                    key={`${ref.clientRecordId}-${ref.sourceSentenceId || idx}`}
                    id={`ctx-${idx}`}
                    className={`context-card ${idx === contextIndex ? 'is-active' : ''}`}
                    onClick={() => setContextIndex(idx)}
                  >
                    {ref.sourceSentence && (
                      <Text className='context-sentence'>"{ref.sourceSentence}"</Text>
                    )}
                    <View className='context-card-footer'>
                      {ref.collectedAt && (
                        <Text className='context-date'>
                          {new Date(ref.collectedAt).toLocaleDateString('zh-CN')}
                        </Text>
                      )}
                      {ref.clientRecordId && (
                        <View
                          className='context-goto-btn'
                          onClick={(e) => { e.stopPropagation(); handleGoToResult(ref) }}
                        >
                          <LucideIcon name='bookOpen' size={14} color='var(--color-primary)' />
                          <Text className='goto-text'>查看原文</Text>
                        </View>
                      )}
                    </View>
                  </View>
                ))}
              </ScrollView>

              {sourceRefs.length > 1 && (
                <View className='context-dots'>
                  {sourceRefs.map((_, idx) => (
                    <View
                      key={idx}
                      className={`dot ${idx === contextIndex ? 'is-active' : ''}`}
                      onClick={() => setContextIndex(idx)}
                    />
                  ))}
                </View>
              )}
            </View>
          )}

          {/* Fallback: single sentence (old data without sourceRefs) */}
          {!sourceRefs.length && entry.sentence && (
            <View className='memory-hook-section'>
              <Text className='section-label'>来源原文</Text>
              <View className='memory-box'>
                <Text className='memory-sentence'>"{entry.sentence}"</Text>
              </View>
            </View>
          )}

          {/* Dictionary Section */}
          <View className='dictionary-section'>
            <Text className='section-label'>词典释义</Text>

            {(hasPhrases || hasExamples) && (
              <View className='dict-tabs'>
                <View
                  className={`dict-tab ${dictTab === 'meanings' ? 'is-active' : ''}`}
                  onClick={() => setDictTab('meanings')}
                >
                  <Text>释义</Text>
                </View>
                {hasPhrases && (
                  <View
                    className={`dict-tab ${dictTab === 'phrases' ? 'is-active' : ''}`}
                    onClick={() => setDictTab('phrases')}
                  >
                    <Text>短语</Text>
                  </View>
                )}
                {hasExamples && (
                  <View
                    className={`dict-tab ${dictTab === 'examples' ? 'is-active' : ''}`}
                    onClick={() => setDictTab('examples')}
                  >
                    <Text>例句</Text>
                  </View>
                )}
              </View>
            )}

            {dictLoading ? (
              <View className='dict-loading'>
                <Text className='loading-text'>加载中...</Text>
              </View>
            ) : dictTab === 'meanings' ? (
              <View className='meanings-list'>
                {displayMeanings.length > 0 ? displayMeanings.map((m, idx) => (
                  <View key={idx} className='meaning-group'>
                    <View className='pos-badge'>
                      <Text className='pos-text'>{m.partOfSpeech}</Text>
                    </View>
                    <View className='definitions'>
                      {m.definitions.map((def, dIdx) => (
                        <View key={dIdx} className='def-item'>
                          <Text className='def-text'>
                            {m.definitions.length > 1 ? `${dIdx + 1}. ` : ''}{def.meaning}
                          </Text>
                          {'example' in def && def.example && (
                            <Text className='def-example'>{def.example}</Text>
                          )}
                        </View>
                      ))}
                    </View>
                  </View>
                )) : (
                  <View className='meaning-group fallback-meaning'>
                    {entry.partOfSpeech && (
                      <View className='pos-badge'>
                        <Text className='pos-text'>{entry.partOfSpeech}</Text>
                      </View>
                    )}
                    <View className='definitions'>
                      <Text className='def-text'>{entry.meaning}</Text>
                    </View>
                  </View>
                )}
              </View>
            ) : dictTab === 'phrases' && dictEntry?.phrases ? (
              <View className='phrases-list'>
                {dictEntry.phrases.map((p, idx) => (
                  <View key={idx} className='phrase-item'>
                    <Text className='phrase-text'>{p.phrase}</Text>
                    {p.meaning && <Text className='phrase-meaning'>{p.meaning}</Text>}
                  </View>
                ))}
              </View>
            ) : dictTab === 'examples' && dictEntry?.examples ? (
              <View className='examples-list'>
                {dictEntry.examples.map((ex, idx) => (
                  <View key={idx} className='example-item'>
                    <Text className='example-text'>{ex.example}</Text>
                    {ex.exampleTranslation && (
                      <Text className='example-translation'>{ex.exampleTranslation}</Text>
                    )}
                  </View>
                ))}
              </View>
            ) : null}
          </View>

          <View className='vocab-detail-bottom-spacer' />
        </ScrollView>

        {/* Footer Actions */}
        <View className='detail-footer safe-area-bottom'>
          <View
            className={`footer-btn mastery-btn ${entry.mastered ? 'is-mastered' : ''}`}
            onClick={() => onToggleMastery?.(entry)}
          >
            <LucideIcon name='checkCircle2' size={20} color={entry.mastered ? 'var(--color-success)' : 'var(--text-main)'} />
            <Text>{entry.mastered ? '已掌握' : '标为已掌握'}</Text>
          </View>

          {sourceRefs.length > 0 && sourceRefs[0].clientRecordId && (
            <View
              className='footer-btn source-btn'
              onClick={() => handleGoToResult(sourceRefs[0])}
            >
              <LucideIcon name='bookOpen' size={20} color='var(--color-white)' />
              <Text>查看原文</Text>
            </View>
          )}
        </View>

      </View>
    </View>
  )
}

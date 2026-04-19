import { View, Text, ScrollView } from '@tarojs/components'
import { VocabEntry } from '../../types/view/vocabulary.vm'
import LucideIcon from '../LucideIcon'
import './index.scss'

interface VocabDetailViewProps {
  visible: boolean
  entry: VocabEntry | null
  onClose: () => void
  onGoToResult: (recordId: string) => void
  onToggleMastery?: (entry: VocabEntry) => void
}

export default function VocabDetailView({
  visible,
  entry,
  onClose,
  onGoToResult,
  onToggleMastery
}: VocabDetailViewProps) {
  if (!visible || !entry) return null

  return (
    <View className='vocab-detail-overlay' onClick={onClose}>
      <View className='vocab-detail-container' onClick={(e) => e.stopPropagation()}>
        <View className='detail-drag-handle' onClick={onClose} />
        
        <ScrollView className='detail-scroll-content' scrollY enhanced showScrollbar={false}>
          
          {/* Header: Hero Word */}
          <View className='detail-hero'>
            <View className='word-title-row'>
              <Text className='hero-word'>{entry.word}</Text>
              <View className='hero-actions'>
                <View className='action-btn' onClick={onClose}>
                  <LucideIcon name='x' size={24} color='var(--text-muted)' />
                </View>
              </View>
            </View>
            
            {(entry.phonetic || entry.lemma) && (
              <View className='hero-meta-row'>
                {entry.phonetic && <Text className='phonetic'>/{entry.phonetic}/</Text>}
                {entry.lemma && entry.lemma !== entry.word && (
                  <Text className='lemma'>原型: {entry.lemma}</Text>
                )}
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

          {/* Memory Hook: User's Context Sentence */}
          {entry.sentence && (
            <View className='memory-hook-section'>
              <Text className='section-label'>来源原文</Text>
              <View className='memory-box'>
                <Text className='memory-sentence'>"{entry.sentence}"</Text>
              </View>
            </View>
          )}

          {/* Dictionary: Detailed Meanings */}
          <View className='dictionary-section'>
            <Text className='section-label'>词典释义</Text>
            
            {entry.detailMeanings && entry.detailMeanings.length > 0 ? (
              <View className='meanings-list'>
                {entry.detailMeanings.map((m, idx) => (
                  <View key={idx} className='meaning-group'>
                    <View className='pos-badge'>
                      <Text className='pos-text'>{m.pos}</Text>
                    </View>
                    <View className='definitions'>
                      {m.definitions.map((def, dIdx) => (
                        <Text key={dIdx} className='def-text'>
                          {m.definitions.length > 1 ? `${dIdx + 1}. ` : ''}{def}
                        </Text>
                      ))}
                    </View>
                  </View>
                ))}
              </View>
            ) : (
              /* Fallback if no detailed meanings exist (e.g. old data) */
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
          
          <View style={{ height: '200rpx' }} />
        </ScrollView>

        {/* Footer Actions */}
        <View className='detail-footer safe-area-bottom'>
          <View 
            className={`footer-btn mastery-btn ${entry.mastered ? 'is-mastered' : ''}`}
            onClick={() => onToggleMastery?.(entry)}
          >
            <LucideIcon name='checkCircle2' size={20} color={entry.mastered ? '#10b981' : 'var(--text-main)'} />
            <Text>{entry.mastered ? '已掌握' : '标为已掌握'}</Text>
          </View>
          
          {entry.recordId && (
            <View className='footer-btn source-btn' onClick={() => onGoToResult(entry.recordId)}>
              <LucideIcon name='bookOpen' size={20} color='var(--color-primary)' />
              <Text>回看全文</Text>
            </View>
          )}
        </View>

      </View>
    </View>
  )
}

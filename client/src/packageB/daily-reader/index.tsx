import { View, Text } from '@tarojs/components'
import { useCallback, useEffect, useState } from 'react'
import Taro, { usePageScroll, useShareAppMessage } from '@tarojs/taro'
import { ROUTES } from '../../config/routes'
import { useDailyReaderStore } from '../../stores/daily-reader'
import DailyReaderHeader from '../../components/DailyReaderHeader'
import DailyReaderBody from '../../components/DailyReaderBody'
import DailyReaderFooterAnalysis from '../../components/DailyReaderFooterAnalysis'
import DailyReaderProgress from '../../components/DailyReaderProgress'
import WordPopup from '../../components/WordPopup'
import { highlightToInlineMark } from '../../services/api/adapters/daily-reader-highlight.adapter'
import type { DailyReaderHighlight } from '../../types/view/daily-reader.vm'
import type { InlineMarkModel, DictionaryResult } from '../../types/view/render-scene.vm'
import { isFavorited, saveFavorite, removeFavorite, saveVocabEntry } from '../../services/storage'
import { CloudSyncService } from '../../services/cloudSync.service'
import { track } from '../../services/analytics'
import type { VocabEntry } from '../../types/view/vocabulary.vm'
import type { FavoriteRecord } from '../../types/view/favorites.vm'
import LucideIcon from '../../components/LucideIcon'
import shareFallback from '../../assets/images/share-fallback.jpg'
import './index.scss'

export default function DailyReaderPage() {
  const {
    currentArticle: article,
    loading,
    error,
    fetchArticle,
  } = useDailyReaderStore()

  const [popupVisible, setPopupVisible] = useState(false)
  const [popupMode, setPopupMode] = useState<'mini' | 'full'>('mini')
  const [activeMark, setActiveMark] = useState<InlineMarkModel | null>(null)
  const [activeWord, setActiveWord] = useState('')
  const [contextSentence, setContextSentence] = useState<string | undefined>()
  const [tapPosition, setTapPosition] = useState({ x: 0, y: 0 })
  const [favorited, setFavorited] = useState(false)
  const [animTrigger, setAnimTrigger] = useState(0)

  useEffect(() => {
    if (article) {
      setFavorited(isFavorited(article.id))
    }
  }, [article])

  useEffect(() => {
    const params = Taro.getCurrentInstance().router?.params
    const id = params?.id
    if (id) {
      fetchArticle(id)
    }
  }, [fetchArticle])

  usePageScroll((res) => {
    Taro.eventCenter.trigger('dailyReaderPageScroll', res)
  })

  useShareAppMessage(() => {
    if (!article) return { title: 'Claread 透读', path: ROUTES.HOME, imageUrl: shareFallback }
    return {
      title: `${article.title} — Claread 每日精读`,
      path: `${ROUTES.DAILY_READER}?id=${article.id}`,
      imageUrl: shareFallback,
    }
  })

  const handleHighlightClick = useCallback((highlight: DailyReaderHighlight) => {
    const mark = highlightToInlineMark(highlight)
    setActiveMark(mark)
    setActiveWord(highlight.text)
    setPopupMode('mini')
    setPopupVisible(true)
  }, [])

  const handleWordClick = useCallback((word: string) => {
    setActiveMark(null)
    setActiveWord(word)
    setPopupMode('mini')
    setPopupVisible(true)
  }, [])

  const handleExpandPopup = useCallback(() => {
    setPopupMode('full')
  }, [])

  const handleClosePopup = useCallback(() => {
    setPopupVisible(false)
    setActiveMark(null)
    setActiveWord('')
  }, [])

  const handleAddVocab = useCallback((word: string, dictResult: DictionaryResult | null) => {
    if (!article || !dictResult || dictResult.resultType !== 'entry') return
    const detailEntry = dictResult.entry
    const detailMeanings = detailEntry.meanings
    const derivedMeaning = detailMeanings[0]?.definitions
      ?.map((d: { meaning: string }) => d.meaning)
      .filter(Boolean)
      .join('；') || ''
    const lemma = detailEntry.baseWord ?? detailEntry.word
    const vocabEntry: VocabEntry = {
      id: `${article.id}_${lemma.toLowerCase()}_${Date.now()}`,
      lemma,
      word: word,
      partOfSpeech: detailMeanings[0]?.partOfSpeech || '',
      meaning: derivedMeaning.slice(0, 200),
      addedAt: Date.now(),
      mastered: false,
      dictEntryId: detailEntry.id,
      phonetic: detailEntry.phonetic,
      provider: dictResult.provider || 'tecd3',
      sentence: contextSentence,
      detailMeanings: detailMeanings.map((m: { partOfSpeech?: string; definitions: Array<{ meaning: string }> }) => ({
        pos: m.partOfSpeech || '',
        definitions: m.definitions.map((d: { meaning: string }) => d.meaning).filter(Boolean),
      })).filter((m: { definitions: string[] }) => m.definitions.length > 0),
      exchange: detailEntry.exchange || [],
      tags: detailEntry.tags || [],
      sourceRefs: [{
        clientRecordId: article.id,
        cloudRecordId: undefined,
        sourceSentence: contextSentence || undefined,
        sourceAnchorText: word,
        sourceOccurrence: activeMark?.anchor.kind === 'text' ? activeMark.anchor.occurrence : undefined,
        collectedAt: new Date().toISOString(),
      }],
    }

    const result = saveVocabEntry(vocabEntry)
    if (result.merged) {
      Taro.showToast({
        title: `${word} 已添加到 ${lemma}`,
        icon: 'none',
        duration: 2000,
      })
    } else {
      Taro.showToast({ title: `${word} 已记入生词本`, icon: 'success' })
    }
    
    track('add_vocab', { word, merged: result.merged })
    CloudSyncService.syncVocab(result.entry)
  }, [article, contextSentence, activeMark])

  const handleFavorite = useCallback(() => {
    if (!article) return
    const isAdding = !favorited
    setAnimTrigger(prev => prev + 1)

    if (isAdding) {
      saveFavorite({ recordId: article.id, cloudId: undefined, createdAt: Date.now() } as FavoriteRecord)
      setFavorited(true)
      track('favorite', { isFavorited: true })
      Taro.showToast({ title: '已收藏全文', icon: 'success', duration: 1500 })
      CloudSyncService.syncFavorite(undefined, article.id, 'add')
    } else {
      removeFavorite(article.id)
      setFavorited(false)
      track('favorite', { isFavorited: false })
      Taro.showToast({ title: '已取消收藏', icon: 'none', duration: 1500 })
      CloudSyncService.syncFavorite(undefined, article.id, 'remove')
    }
  }, [article, favorited])

  if (loading && !article) {
    return (
      <View className='daily-page daily-page--loading'>
        <View className='daily-page__loading-dot' />
        <View className='daily-page__loading-dot' />
        <View className='daily-page__loading-dot' />
      </View>
    )
  }

  if (error || !article) {
    return (
      <View className='daily-page daily-page--error'>
        <View className='daily-page__error-text'>
          {error || '文章未找到'}
        </View>
      </View>
    )
  }

  return (
    <View className='daily-page'>
      <DailyReaderProgress />
      <DailyReaderHeader article={article} />
      <View className='daily-page__body-divider' />
      <DailyReaderBody
        body={article.body}
        highlights={article.highlights}
        onHighlightClick={handleHighlightClick}
        onWordClick={handleWordClick}
      />
      <DailyReaderFooterAnalysis
        footerAnalysis={article.footerAnalysis}
        sourceUrl={article.sourceUrl}
        source={article.source}
      />
      <View className='daily-page__end-actions'>
        <View
          className={`daily-page__action-btn ${favorited ? 'daily-page__action-btn--favorited' : ''} ${animTrigger > 0 ? 'animate-spring' : ''}`}
          onClick={handleFavorite}
        >
          <LucideIcon name='star' size={18} color={favorited ? 'var(--color-warning)' : 'var(--dr-text-sub)'} />
          <Text>{favorited ? '已收藏全文' : '收藏全文'}</Text>
        </View>
        <View
          className='daily-page__action-btn'
          onClick={() => Taro.navigateTo({ url: ROUTES.DAILY_READER_ARCHIVE })}
        >
          <LucideIcon name='archive' size={18} color='var(--dr-text-sub)' />
          <Text>往期精选</Text>
        </View>
      </View>
      <WordPopup
        visible={popupVisible}
        mode={popupMode}
        mark={activeMark}
        word={activeWord}
        contextSentence={contextSentence}
        x={tapPosition.x}
        y={tapPosition.y}
        onClose={handleClosePopup}
        onExpand={handleExpandPopup}
        onAddVocab={handleAddVocab}
        onFavorite={(w) => track('favorite_word', { word: w })}
      />
    </View>
  )
}

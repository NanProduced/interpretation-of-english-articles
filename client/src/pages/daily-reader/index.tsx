import { View } from '@tarojs/components'
import { useCallback, useEffect, useState } from 'react'
import Taro, { usePageScroll, useShareAppMessage } from '@tarojs/taro'
import { useDailyReaderStore } from '../../stores/daily-reader'
import DailyReaderHeader from '../../components/DailyReaderHeader'
import DailyReaderBody from '../../components/DailyReaderBody'
import DailyReaderFooterAnalysis from '../../components/DailyReaderFooterAnalysis'
import DailyReaderBottomSheet from '../../components/DailyReaderBottomSheet'
import DailyReaderProgress from '../../components/DailyReaderProgress'
import type { DailyReaderHighlight } from '../../types/view/daily-reader.vm'
import './index.scss'

export default function DailyReaderPage() {
  const {
    currentArticle: article,
    loading,
    error,
    fetchArticle,
  } = useDailyReaderStore()

  const [activeHighlight, setActiveHighlight] = useState<DailyReaderHighlight | null>(null)
  const [sheetVisible, setSheetVisible] = useState(false)

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
    if (!article) return { title: 'Claread 透读', path: '/pages/home/index' }
    return {
      title: `${article.title} — Claread 每日精读`,
      path: `/pages/daily-reader/index?id=${article.id}`,
    }
  })

  const handleHighlightClick = useCallback((highlight: DailyReaderHighlight) => {
    setActiveHighlight(highlight)
    setSheetVisible(true)
  }, [])

  const handleWordClick = useCallback((word: string) => {
    setActiveHighlight({
      id: `word_${word}`,
      type: 'vocab_highlight',
      text: word,
      gloss: '',
      paragraphId: '',
      start: 0,
      end: 0,
    })
    setSheetVisible(true)
  }, [])

  const handleCloseSheet = useCallback(() => {
    setSheetVisible(false)
    setActiveHighlight(null)
  }, [])

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
      <DailyReaderBottomSheet
        visible={sheetVisible}
        highlight={activeHighlight}
        onClose={handleCloseSheet}
      />
    </View>
  )
}

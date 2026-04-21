import { View, Text } from '@tarojs/components'
import { useCallback, useEffect, useState } from 'react'
import Taro, { usePageScroll, useShareAppMessage } from '@tarojs/taro'
import { useDailyReaderStore } from '../../stores/daily-reader'
import DailyReaderHeader from '../../components/DailyReaderHeader'
import DailyReaderBody from '../../components/DailyReaderBody'
import DailyReaderFooterAnalysis from '../../components/DailyReaderFooterAnalysis'
import DailyReaderProgress from '../../components/DailyReaderProgress'
import WordPopup from '../../components/WordPopup'
import { highlightToInlineMark } from '../../services/api/adapters/daily-reader-highlight.adapter'
import type { DailyReaderHighlight } from '../../types/view/daily-reader.vm'
import type { InlineMarkModel, DictionaryResult } from '../../types/view/render-scene.vm'
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

  // TODO: 上线前需为分享卡片生成自定义 imageUrl，使用 cover_theme 渐变 + 标题 + 来源绘制
  // 参见 specs/daily-reader/requirements.md Req 11.2
  useShareAppMessage(() => {
    if (!article) return { title: 'Claread 透读', path: '/pages/home/index' }
    return {
      title: `${article.title} — Claread 每日精读`,
      path: `/pages/daily-reader/index?id=${article.id}`,
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

  const handleAddVocab = useCallback((_word: string, _dictResult: DictionaryResult | null) => {
    Taro.showToast({ title: '已记入生词本', icon: 'success', duration: 1200 })
  }, [])

  const handleFavorite = useCallback((_word: string) => {
    Taro.showToast({ title: '已收藏', icon: 'success', duration: 1200 })
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
      <View
        className='daily-page__archive-entry'
        onClick={() => Taro.navigateTo({ url: '/pages/daily-reader-archive/index' })}
      >
        <Text className='daily-page__archive-text'>往期精选</Text>
        <Text className='daily-page__archive-arrow'>→</Text>
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
        onFavorite={handleFavorite}
      />
    </View>
  )
}

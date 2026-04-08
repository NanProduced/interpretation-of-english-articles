import { useState, useEffect, useRef } from 'react'
import { useArticleStore } from '../../stores/article'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useShareAppMessage } from '@tarojs/taro'
import { InlineMarkModel, PageMode, ResultPageState } from '../../types/view/render-scene.vm'
import NavBar from '../../components/NavBar'
import ParagraphBlock, { type WordClickPayload } from '../../components/ParagraphBlock'
import WordPopup from '../../components/WordPopup'
import LucideIcon from '../../components/LucideIcon'
import { LoadingIllustration, ErrorIllustration, EmptyIllustration } from '../../components/ResultIllustrations'
import { useLayoutStore } from '../../stores/layout'
import { useAuthStore } from '../../stores/auth'
import { isFavorited, saveFavorite, removeFavorite, updateRecord, saveVocabEntry } from '../../services/storage'
import { CloudSyncService } from '../../services/cloudSync.service'
import { ensureLoggedIn } from '../../services/auth'
import { track } from '../../services/analytics'
import type { FavoriteRecord } from '../../types/view/favorites.vm'
import type { VocabEntry } from '../../types/view/vocabulary.vm'
import './index.scss'

/** 阅读变体映射表 */
const VARIANT_LABELS: Record<string, string> = {
  gaokao: '高考英语',
  cet: '四六级',
  gre: 'GRE',
  ielts_toefl: '雅思/托福',
  beginner_reading: '入门阅读',
  intermediate_reading: '中级阅读',
  intensive_reading: '深度精读',
  academic_general: '学术英语',
}

/** 页面模式选项 */
const PAGE_MODE_OPTIONS = [
  { value: 'immersive', label: '原文' },
  { value: 'intensive', label: '精读' },
] as const

/** pageState → 文案映射 */
const PAGE_STATE_MESSAGES: Record<ResultPageState, { title: string; subtitle: string } | null> = {
  loading: null,
  normal: null,
  degraded_light: null,
  degraded_heavy: null,
  empty: {
    title: '未能解析出有效内容',
    subtitle: '请输入至少一段完整的英文句子（建议 3 句以上），支持常见文章格式。',
  },
  failed: {
    title: '分析失败',
    subtitle: '请稍后重试',
  },
  timeout: {
    title: '分析超时',
    subtitle: '内容较长时需要更多处理时间，请稍后重试',
  },
  network_fail: {
    title: '网络不给力',
    subtitle: '请检查网络后重新尝试',
  },
}

export default function Result() {
  const { navBarHeight } = useLayoutStore()
  const [pageMode, setPageMode] = useState<PageMode>('intensive')
  const [showSecondaryMessage, setShowSecondaryMessage] = useState(false)
  const [vocabList, setVocabList] = useState<string[]>([]) // 已加入生词本的单词列表
  const [wordPopup, setWordPopup] = useState<{
    visible: boolean
    mode: 'mini' | 'full'
    mark: InlineMarkModel | null
    word: string
    x: number
    y: number
  }>({ visible: false, mode: 'mini', mark: null, word: '', x: 0, y: 0 })
  const [activeMarkId, setActiveMarkId] = useState<string | null>(null)
  const [selectedWord, setSelectedWord] = useState<string | null>(null)
  const [loadingStep, setLoadingStep] = useState(0)

  // 从 store 获取页面状态
  const pageState = useArticleStore((s) => s.pageState)
  const sceneData = useArticleStore((s) => s.sceneData)
  const analyze = useArticleStore((s) => s.analyze)
  const loadRecord = useArticleStore((s) => s.loadRecord)
  const recordId = useArticleStore((s) => s.recordId)
  const isReplayMode = useArticleStore((s) => s.isReplayMode)

  // === 加载状态：提示语轮播 ===
  useEffect(() => {
    let interval: any
    if (pageState === 'loading') {
      interval = setInterval(() => {
        setLoadingStep(s => (s + 1) % 5) // 5 is the length of loadingSteps in render
      }, 2500)
    }
    return () => clearInterval(interval)
  }, [pageState])

  // 收藏状态
  const [favorited, setFavorited] = useState(false)

  // 同步收藏状态（recordId 变化时从 storage 读取）
  useEffect(() => {
    if (recordId) {
      setFavorited(isFavorited(recordId))
    }
  }, [recordId])

  // === 回看模式：URL 带有 recordId 时从 storage 加载 ===
  useEffect(() => {
    const pages = Taro.getCurrentPages()
    const current = pages[pages.length - 1]
    const params = (current as any).options || {}
    const { recordId: urlRecordId, mode } = params

    if (mode === 'replay' && urlRecordId) {
      loadRecord(urlRecordId)
    }
  }, [loadRecord])

  // === 加载状态：5 秒后显示次级提示 ===
  useEffect(() => {
    if (pageState === 'loading') {
      const timer = setTimeout(() => setShowSecondaryMessage(true), 5000)
      return () => clearTimeout(timer)
    } else {
      setShowSecondaryMessage(false)
    }
  }, [pageState])

  // === 分享能力 ===
  useShareAppMessage(() => {
    const state = useArticleStore.getState()
    const { recordId, sceneData } = state
    const firstSentence = sceneData?.article.sentences[0]?.text
    const title = firstSentence
      ? firstSentence.split('\n')[0].slice(0, 30) + '...'
      : 'Claread透读 - AI 英语深度解析'
    const path = recordId
      ? `/pages/result/index?recordId=${recordId}&mode=replay`
      : '/pages/result/index'
    return { title, path }
  })

  // === 事件处理 ===

  const handleWordClick = ({ word, mark, event }: WordClickPayload) => {
    const isAIAnnotated = !!(mark?.glossary)
    const initialMode = 'mini' // 始终先弹出小卡片
    setActiveMarkId(mark?.id ?? null)
    setSelectedWord(word)

    let clientX = 0
    let clientY = 0
    if (event) {
      if (event.changedTouches && event.changedTouches[0]) {
        clientX = event.changedTouches[0].clientX
        clientY = event.changedTouches[0].clientY
      } else if (event.detail && (event.detail.x !== undefined || event.detail.clientX !== undefined)) {
        clientX = event.detail.x ?? event.detail.clientX
        clientY = event.detail.y ?? event.detail.clientY
      }
    }
    setWordPopup({ visible: true, mode: initialMode, mark: mark ?? null, word, x: clientX, y: clientY })
  }

  const handleClosePopup = () => {
    setWordPopup({ ...wordPopup, visible: false })
    setActiveMarkId(null)
    setSelectedWord(null)
  }

  const handleScroll = () => {
    if (wordPopup.visible && wordPopup.mode === 'mini') {
      handleClosePopup()
    }
  }

  const handleToggleFavorite = async () => {
    if (!recordId) return
    const isAdding = !favorited

    if (isAdding) {
      // 先写本地
      saveFavorite({ recordId, createdAt: Date.now() } as FavoriteRecord)
      updateRecord(recordId, { isFavorited: true })
      setFavorited(true)
      track('favorite', { isFavorited: true })
      Taro.showToast({ title: '已收藏', icon: 'success', duration: 1500 })

      // 再同步云端（401 → 引导登录 → 重试）
      try {
        await CloudSyncService.syncFavorite(recordId, 'add')
      } catch (err: any) {
        if (err?.statusCode === 401) {
          const relogin = await ensureLoggedIn()
          if (relogin) {
            await CloudSyncService.syncFavorite(recordId, 'add')
          }
        }
        // 其他错误静默忽略
      }
    } else {
      // 取消收藏
      removeFavorite(recordId)
      updateRecord(recordId, { isFavorited: false })
      setFavorited(false)
      track('favorite', { isFavorited: false })
      Taro.showToast({ title: '已取消收藏', icon: 'none', duration: 1500 })

      try {
        await CloudSyncService.syncFavorite(recordId, 'remove')
      } catch {
        // 静默忽略删除失败的场景
      }
    }
  }

  const handleRetry = () => {
    const { pageState, requestParams, reset } = useArticleStore.getState()
    // error / timeout / network_fail / empty: 就地重试，保留用户的文章内容
    const retryableStates: ResultPageState[] = ['failed', 'timeout', 'network_fail', 'empty']
    if (retryableStates.includes(pageState) && requestParams) {
      track('retry', { pageState })
      useArticleStore.getState().analyze(requestParams)
    } else {
      // success (normal/degraded): 返回输入页
      reset()
      Taro.navigateBack()
    }
  }

  // === 通用页面外壳 ===
  const pageShell = (extraContent: React.ReactNode) => {
    const { request } = sceneData || {}
    const levelLabel = request ? VARIANT_LABELS[request.readingVariant] : ''
    const sourceLabel = request?.sourceType === 'user_input' ? '手动输入' : '每日文章'

    return (
      <View className='result-page'>
        <NavBar 
          title='Claread透读' 
          subtitle={levelLabel ? `${levelLabel} · ${sourceLabel}` : undefined}
          showBack 
          showHome 
        />
        <View style={{ height: navBarHeight + 'px', flexShrink: 0 }} />
        {extraContent}
      </View>
    )
  }

  // === 降级提示条（基于 pageState，不暴露技术细节） ===
  const renderDegradedBanner = (state: ResultPageState) => {
    if (state !== 'degraded_light' && state !== 'degraded_heavy') return null

    const isHeavy = state === 'degraded_heavy'
    const message = isHeavy
      ? '由于网络环境影响，当前为您呈现的是“极速分析”结果。部分深度解析可能暂不可用。'
      : '分析引擎正在轻量化运行，已为您精选了最重要的解读，细节稍有简化，不影响整体理解。'

    return (
      <View className={`degraded-banner ${isHeavy ? 'heavy' : ''}`}>
        <LucideIcon name='info' size={14} color='var(--color-focus)' />
        <View className='degraded-banner-content'>
          <Text className='degraded-banner-text'>{message}</Text>
        </View>
        {isHeavy && (
          <View className='degraded-retry-btn' onClick={handleRetry}>
            <Text className='degraded-retry-text'>获取深度解析</Text>
          </View>
        )}
      </View>
    )
  }

  // === 状态分支 ===

  if (pageState === 'loading') {
    const loadingSteps = [
      '正在解析文章结构...',
      '分析重点句式与语法...',
      '智能标注高阶词汇...',
      '同步你的阅读偏好...',
      '生成精读解析卡片...'
    ]
    return pageShell(
      <View className='state-container'>
        <View className='state-vertical'>
          <LoadingIllustration />
          <Text className='state-title'>{loadingSteps[loadingStep]}</Text>
          <Text className='state-subtitle'>AI 正在分析并生成解读内容</Text>
          {showSecondaryMessage && (
            <Text className='state-subtitle-secondary'>请稍候，长文章需要较多计算时间</Text>
          )}
        </View>
      </View>
    )
  }

  if (pageState === 'empty') {
    const msg = PAGE_STATE_MESSAGES.empty!
    return pageShell(
      <View className='state-container'>
        <View className='state-vertical'>
          <EmptyIllustration />
          <Text className='state-title'>{msg.title}</Text>
          <Text className='state-subtitle'>{msg.subtitle}</Text>
        </View>
        <View className='state-cta safe-area-bottom'>
          <View className='btn-primary' onClick={handleRetry}>
            <Text className='btn-primary-text'>修改重试</Text>
          </View>
        </View>
      </View>
    )
  }

  if (pageState === 'failed' || pageState === 'timeout' || pageState === 'network_fail') {
    const msg = PAGE_STATE_MESSAGES[pageState]!
    return pageShell(
      <View className='state-container'>
        <View className='state-vertical'>
          <ErrorIllustration />
          <Text className='state-title'>{msg.title}</Text>
          <Text className='state-subtitle'>{msg.subtitle}</Text>
        </View>
        <View className='state-cta safe-area-bottom'>
          <View className='btn-primary' onClick={handleRetry}>
            <Text className='btn-primary-text'>重新分析</Text>
          </View>
        </View>
      </View>
    )
  }

  // === Success 状态 ===

  // 防御：pageState 非 loading 但 sceneData 缺失 → 透明渲染（不 crash）
  if (!sceneData) {
    return pageShell(
      <View className='state-container'>
        <View className='state-vertical'>
          <LoadingIllustration />
          <Text className='state-title'>正在加载...</Text>
        </View>
      </View>
    )
  }

  const renderArticleHeader = () => {
    if (!sceneData) return null
    const { request } = sceneData
    return (
      <View className='article-header'>
        <View className='article-meta-row'>
          <Text className='source-tag'>
            {request.sourceType === 'user_input' ? '手动输入' : '每日文章'}
          </Text>
          <Text className='level-tag'>
            {request.readingVariant.toUpperCase()}
          </Text>
        </View>
      </View>
    )
  }

  const renderParagraphs = () => {
    if (!sceneData?.article?.paragraphs?.length) return null
    return sceneData!.article.paragraphs.map((paragraph) => {
      const sentences = paragraph.sentenceIds
        .map((id) => sceneData!.article.sentences.find((s) => s.sentenceId === id))
        .filter((s): s is NonNullable<typeof s> => !!s)

      return (
        <ParagraphBlock
          key={paragraph.paragraphId}
          sentences={sentences}
          translations={sceneData!.translations}
          showTranslation={pageMode === 'intensive'}
          inlineMarks={sceneData!.inlineMarks}
          activeMarkId={activeMarkId}
          selectedWord={selectedWord}
          vocabList={vocabList}
          tailEntries={sceneData!.sentenceEntries}
          pageMode={pageMode}
          onWordClick={handleWordClick}
        />
      )
    })
  }

  return pageShell(
    <>
      <View className='mode-tabs-container' role='tablist' aria-label='阅读模式切换'>
        <View className='mode-tabs'>
          {PAGE_MODE_OPTIONS.map((mode) => (
            <View
              key={mode.value}
              className={`mode-tab ${pageMode === mode.value ? 'active' : ''}`}
              onClick={() => setPageMode(mode.value as PageMode)}
              role='tab'
              aria-selected={pageMode === mode.value}
              aria-label={mode.label}
            >
              <Text className='mode-tab-label'>{mode.label}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* 降级提示条：位于 mode-tabs 下方 */}
      {renderDegradedBanner(pageState)}

      <ScrollView className='article-scroll' scrollY enhanced showScrollbar={false} onScroll={handleScroll}>
        <View className='article-container'>
          {renderParagraphs()}
          <View className='bottom-spacer' />
        </View>
      </ScrollView>

      {/* Global Bottom Action Bar */}
      <View className='global-action-bar safe-area-bottom'>
        <View className='action-bar-inner'>
          <View className={`secondary-action ${favorited ? 'favorited' : ''}`} onClick={handleToggleFavorite}>
            <LucideIcon name={favorited ? 'star' : 'star'} size={20} color={favorited ? 'var(--color-warn)' : 'var(--text-sub)'} />
            <Text className={favorited ? 'favorited-text' : ''}>{favorited ? '已收藏' : '收藏全文'}</Text>
          </View>
          <View className='primary-action' onClick={handleRetry}>
            <LucideIcon name='refresh-cw' size={18} color='#fff' />
            <Text>重新分析</Text>
          </View>
        </View>
      </View>

      <WordPopup
        visible={wordPopup.visible}
        mode={wordPopup.mode}
        mark={wordPopup.mark}
        word={wordPopup.word}
        x={wordPopup.x}
        y={wordPopup.y}
        onClose={handleClosePopup}
        onExpand={() => setWordPopup({ ...wordPopup, mode: 'full' })}
        onAddVocab={async (w, dictResult) => {
          if (!recordId || !dictResult || dictResult.resultType !== 'entry') return
          const detailEntry = dictResult.entry
          const detailMeanings = detailEntry.meanings
          // 从首个 meaning 的 definitions 拼接派生，并在快照层截断
          const derivedMeaning = detailMeanings[0]?.definitions
            ?.map((d) => d.meaning)
            .filter(Boolean)
            .join('；') || ''
          const vocabEntry: VocabEntry = {
            id: `${recordId}_${w}_${Date.now()}`,
            recordId,
            word: w,
            partOfSpeech: detailMeanings[0]?.partOfSpeech || '',
            meaning: derivedMeaning.slice(0, 200),
            addedAt: Date.now(),
            mastered: false,
            // 优先取 entry.baseWord ?? entry.word
            lemma: detailEntry.baseWord ?? detailEntry.word,
            phonetic: detailEntry.phonetic,
            provider: dictResult.provider || 'tecd3',
          }
          saveVocabEntry(vocabEntry)
          track('add_vocab', { word: w })

          // 静默同步云端（401 → 引导登录 → 重试）
          try {
            await CloudSyncService.syncVocab(vocabEntry)
          } catch (err: any) {
            if (err?.statusCode === 401) {
              const relogin = await ensureLoggedIn()
              if (relogin) {
                await CloudSyncService.syncVocab(vocabEntry)
              }
            }
          }
        }}
        onFavorite={(w) => { track('favorite_word', { word: w }) }}
      />
    </>
  )
}

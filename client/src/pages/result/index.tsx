import { useState, useEffect, useRef } from 'react'
import { useArticleStore } from '../../stores/article'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useShareAppMessage } from '@tarojs/taro'
import { InlineMarkModel, PageMode, RenderSceneVm, ResultPageState } from '../../types/view/render-scene.vm'
import NavBar from '../../components/NavBar'
import ParagraphBlock, { type WordClickPayload } from '../../components/ParagraphBlock'
import WordPopup from '../../components/WordPopup'
import LucideIcon from '../../components/LucideIcon'
import { LoadingIllustration, ErrorIllustration, EmptyIllustration } from '../../components/ResultIllustrations'
import ActiveLoading from '../../components/ActiveLoading'
import { useLayoutStore } from '../../stores/layout'
import { useAuthStore } from '../../stores/auth'
import { isFavorited, saveFavorite, removeFavorite, updateRecord, saveVocabEntry, getVocabulary } from '../../services/storage'
import { CloudSyncService } from '../../services/cloudSync.service'
import { ensureLoggedIn } from '../../services/auth'
import { track } from '../../services/analytics'
import type { FavoriteRecord } from '../../types/view/favorites.vm'
import type { VocabEntry } from '../../types/view/vocabulary.vm'
import './index.scss'

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

function hasRenderableScene(scene: RenderSceneVm | null): boolean {
  if (!scene) return false
  if (scene.article?.paragraphs?.length) return true
  return (scene.article?.sentences ?? []).some((sentence) => !!sentence.text?.trim())
}

function splitSourceParagraphs(text: string): string[] {
  return text
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
}

export default function Result() {
  const { navBarHeight } = useLayoutStore()
  const [pageMode, setPageMode] = useState<PageMode>('intensive')
  const [vocabList, setVocabList] = useState<string[]>([])
  const [wordPopup, setWordPopup] = useState<{
    visible: boolean
    mode: 'mini' | 'full'
    mark: InlineMarkModel | null
    word: string
    contextSentence?: string
    x: number
    y: number
  }>({ visible: false, mode: 'mini', mark: null, word: '', x: 0, y: 0 })
  const [activeMarkId, setActiveMarkId] = useState<string | null>(null)
  const [activeSentenceId, setActiveSentenceId] = useState<string | null>(null)
  const [selectedWord, setSelectedWord] = useState<string | null>(null)

  // 从 store 获取页面状态
  const pageState = useArticleStore((s) => s.pageState)
  const sceneData = useArticleStore((s) => s.sceneData)
  const requestParams = useArticleStore((s) => s.requestParams)
  const errorCode = useArticleStore((s) => s.errorCode)
  const errorMsg = useArticleStore((s) => s.error)
  const analyze = useArticleStore((s) => s.analyze)
  const loadRecord = useArticleStore((s) => s.loadRecord)
  const recoverActiveTask = useArticleStore((s) => s.recoverActiveTask)
  const recordId = useArticleStore((s) => s.recordId)
  const cloudId = useArticleStore((s) => s.cloudId)
  const isReplayMode = useArticleStore((s) => s.isReplayMode)



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
    // 每次页面挂载时都检查 replay 参数，确保不会因为旧 state 导致闪现旧结果
    const pages = Taro.getCurrentPages()
    const current = pages[pages.length - 1]
    const params = (current as any).options || {}
    const { recordId: urlRecordId, mode } = params

    if (mode === 'replay' && urlRecordId) {
      // 进入回看模式前先重置，避免旧数据闪现
      useArticleStore.getState().reset()
      loadRecord(urlRecordId)
    }
  }, [loadRecord])

  // === 加载生词本：提取当前文章的单词列表 ===
  useEffect(() => {
    if (!recordId) return
    const all = getVocabulary()
    const words = all
      .filter((v: { recordId: string }) => v.recordId === recordId)
      .map((v: { word: string }) => v.word.toLowerCase())
    setVocabList(words)
  }, [recordId])

  Taro.useDidShow(() => {
    // 页面展示时，如果当前处于加载中或失败状态，且没有场景数据，尝试恢复活跃任务
    // 主要是为了处理杀后台恢复或意外中断
    if ((pageState === 'loading' || pageState === 'failed') && !sceneData) {
      recoverActiveTask()
    }
  })


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

  const handleWordClick = ({ word, mark, event, contextSentence, occurrence }: WordClickPayload) => {
    console.log('[result] word clicked:', word, mark?.id)
    const initialMode = 'mini'
    setActiveMarkId(mark?.id ?? null)
    setSelectedWord(word)

    const sysInfo = Taro.getSystemInfoSync()
    const windowWidth = sysInfo.windowWidth || 375
    
    let clientX = windowWidth / 2 // 默认中线
    let clientY = 300 // 默认中部

    // 适配多端事件坐标获取
    if (event) {
      const touch = event.changedTouches?.[0] || (event.touches ? event.touches[0] : null)
      if (touch) {
        clientX = touch.clientX ?? touch.pageX
        clientY = touch.clientY ?? touch.pageY
      } else if (event.detail && (event.detail.x !== undefined || event.detail.clientX !== undefined)) {
        clientX = event.detail.x ?? event.detail.clientX
        clientY = event.detail.y ?? event.detail.clientY
      }
    }
    
    setWordPopup({ 
      visible: true, 
      mode: initialMode, 
      mark: mark ?? null, 
      word, 
      contextSentence, 
      occurrence,
      x: clientX, 
      y: clientY 
    })
  }

  const handleSentenceClick = (sentenceId: string) => {
    setActiveSentenceId(prev => prev === sentenceId ? null : sentenceId)
  }

  const handleClosePopup = () => {
    setWordPopup((prev) => ({ ...prev, visible: false }))
    setActiveMarkId(null)
    setSelectedWord(null)
    setActiveSentenceId(null)
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
        await CloudSyncService.syncFavorite(cloudId || undefined, recordId, 'add')
      } catch (err: any) {
        if (err?.statusCode === 401) {
          const relogin = await ensureLoggedIn()
          if (relogin) {
            await CloudSyncService.syncFavorite(cloudId || undefined, recordId, 'add')
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
        await CloudSyncService.syncFavorite(cloudId || undefined, recordId, 'remove')
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
      // success (normal/degraded): 重置状态，跳转到输入页继续分析新的文本
      reset()
      Taro.redirectTo({ url: '/pages/input/index' })
    }
  }

  // === 通用页面外壳 ===
  const pageShell = (extraContent: React.ReactNode) => {
    return (
      <View className='result-page'>
        <NavBar
          title='Claread透读'
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

  const renderSourceFallback = () => {
    const sourceParagraphs = splitSourceParagraphs(requestParams?.text || '')
    const isDegraded = pageState === 'degraded_light' || pageState === 'degraded_heavy'
    const title = isDegraded ? '本次解析未完成' : '未生成可渲染内容'
    const subtitle = isDegraded
      ? '部分分析节点执行失败，结构化结果未能生成。已为您回退展示原文，建议稍后重新解析。'
      : '当前记录没有生成可展示的结构化结果，建议调整原文后重试。'

    return pageShell(
      <>
        {renderDegradedBanner(pageState)}
        <ScrollView className='article-scroll' scrollY enhanced showScrollbar={false}>
          <View className='article-container fallback-article-container'>
            <View className='fallback-panel'>
              <Text className='fallback-title'>{title}</Text>
              <Text className='fallback-subtitle'>{subtitle}</Text>
            </View>

            {sourceParagraphs.length > 0 && (
              <View className='fallback-source-card'>
                <Text className='fallback-source-label'>原文回退</Text>
                {sourceParagraphs.map((paragraph, idx) => (
                  <Text key={`fallback-${idx}`} className='fallback-source-paragraph'>
                    {paragraph}
                  </Text>
                ))}
              </View>
            )}

            <View className='article-end-actions'>
              <View className='end-btn-primary' onClick={handleRetry}>
                <LucideIcon name='plus' size={18} color='#fff' />
                <Text>{isReplayMode ? '重新解析这篇' : '再分析一篇'}</Text>
              </View>
            </View>
            <View className='bottom-spacer' />
          </View>
        </ScrollView>
      </>
    )
  }

  // === 状态分支 ===

  // 全屏 Loading：仅在完全没有数据且状态为加载中时展示
  if (pageState === 'loading' && !sceneData) {
    return pageShell(
      <View className='state-container'>
        <ActiveLoading />
      </View>
    )
  }

  // 错误/空状态展示：仅在没有数据时展示
  if (!sceneData) {
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
      const defaultMsg = PAGE_STATE_MESSAGES[pageState]!
      const title = errorCode === 'INSUFFICIENT_CREDITS' ? '今日积分不足' : defaultMsg.title
      const subtitle = errorCode === 'INSUFFICIENT_CREDITS' ? errorMsg || '您的积分已耗尽，请明天再试' : defaultMsg.subtitle

      return pageShell(
        <View className='state-container'>
          <View className='state-vertical'>
            <ErrorIllustration />
            <Text className='state-title'>{title}</Text>
            <Text className='state-subtitle'>{subtitle}</Text>
          </View>
          <View className='state-cta safe-area-bottom'>
            <View className='btn-primary' onClick={handleRetry}>
              <Text className='btn-primary-text'>重新分析</Text>
            </View>
          </View>
        </View>
      )
    }

    // 默认保底 Loading
    return pageShell(
      <View className='state-container'>
        <View className='state-vertical'>
          <LoadingIllustration />
          <Text className='state-title'>正在解析文章...</Text>
          <Text className='state-subtitle-secondary'>首次解析可能需要 20-40 秒，请耐心等待</Text>
        </View>
      </View>
    )
  }

  // === 渲染核心交互层 (只要有 sceneData 就会执行到这里) ===

  if (!hasRenderableScene(sceneData)) {
    return renderSourceFallback()
  }

  const renderArticleHeader = () => {
    const { request } = sceneData!
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
    return sceneData!.article.paragraphs.map((paragraph, idx) => {
      const sentences = paragraph.sentenceIds
        .map((id) => sceneData!.article.sentences.find((s) => s.sentenceId === id))
        .filter((s): s is NonNullable<typeof s> => !!s)

      return (
        <ParagraphBlock
          key={`${paragraph.paragraphId}-${idx}`}
          order={idx + 1}
          sentences={sentences}
          translations={sceneData!.translations}
          inlineMarks={sceneData!.inlineMarks}
          activeMarkId={activeMarkId}
          selectedWord={selectedWord}
          vocabList={vocabList}
          tailEntries={sceneData!.sentenceEntries}
          pageMode={pageMode}
          activeSentenceId={activeSentenceId}
          onWordClick={handleWordClick}
          onSentenceClick={handleSentenceClick}
        />
      )
    })
  }

  return pageShell(
    <>
      <View className='result-content-root'>
        <View className='mode-tabs-container' role='tablist' aria-label='阅读模式切换'>
          <View className='mode-tabs'>
            {PAGE_MODE_OPTIONS.map((mode) => (
              <View
                key={mode.value}
                className={`mode-tab ${pageMode === mode.value ? 'active' : ''}`}
                onClick={(e) => {
                  e.stopPropagation()
                  setPageMode(mode.value as PageMode)
                }}
                role='tab'                aria-selected={pageMode === mode.value}
                aria-label={mode.label}
              >
                <Text className='mode-tab-label'>{mode.label}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* 降级提示条 */}
        {renderDegradedBanner(pageState)}

        <ScrollView className='article-scroll' scrollY enhanced showScrollbar={false} onScroll={handleScroll}>
          <View className='article-container'>
            {renderParagraphs()}
            
            <View className='article-end-actions'>
              <View className={`end-btn-secondary ${favorited ? 'favorited' : ''}`} onClick={handleToggleFavorite}>
                <LucideIcon name='bookmark' size={18} color={favorited ? 'var(--color-warn)' : 'var(--text-main)'} />
                <Text className={favorited ? 'favorited-text' : ''}>{favorited ? '已收藏' : '收藏'}</Text>
              </View>
              <View className='end-btn-primary' onClick={handleRetry}>
                <LucideIcon name='plus' size={18} color='#fff' />
                <Text>再分析一篇</Text>
              </View>
            </View>
            <View className='bottom-spacer' />
          </View>
        </ScrollView>
      </View>

      <WordPopup
        visible={wordPopup.visible}
        mode={wordPopup.mode}
        mark={wordPopup.mark}
        word={wordPopup.word}
        contextSentence={wordPopup.contextSentence}
        occurrence={wordPopup.occurrence}
        x={wordPopup.x}
        y={wordPopup.y}
        onClose={handleClosePopup}
        onExpand={() => setWordPopup({ ...wordPopup, mode: 'full' })}
        onAddVocab={async (w, dictResult) => {
          if (!recordId || !dictResult || dictResult.resultType !== 'entry') return
          const detailEntry = dictResult.entry
          const detailMeanings = detailEntry.meanings
          const derivedMeaning = detailMeanings[0]?.definitions
            ?.map((d) => d.meaning)
            .filter(Boolean)
            .join('；') || ''
          const vocabEntry: VocabEntry = {
            id: `${recordId}_${w}_${Date.now()}`,
            recordId,
            cloudRecordId: cloudId || undefined,
            word: w,
            partOfSpeech: detailMeanings[0]?.partOfSpeech || '',
            meaning: derivedMeaning.slice(0, 200),
            addedAt: Date.now(),
            mastered: false,
            lemma: detailEntry.baseWord ?? detailEntry.word,
            phonetic: detailEntry.phonetic,
            provider: dictResult.provider || 'tecd3',
          }
          saveVocabEntry(vocabEntry)
          track('add_vocab', { word: w })

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

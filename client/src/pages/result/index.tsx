import { useMemo } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useShareAppMessage } from '@tarojs/taro'
import { ROUTES } from '../../config/routes'
import { PageMode, AnyRenderSceneVm, AcademicRenderSceneVm } from '../../types/view/render-scene.vm'
import { getSafeDisplayLabel } from '../../config/purpose'
import NavBar from '../../components/NavBar'
import ParagraphBlock from '../../components/ParagraphBlock'
import WordPopup from '../../components/WordPopup'
import ContentSummaryCard from '../../components/ContentSummaryCard'
import LucideIcon from '../../components/LucideIcon'
import BottomSheetSelect from '../../components/BottomSheetSelect'
import FeedbackWidget from '../../components/FeedbackWidget'
import { useResultState } from './hooks/useResultState'
import { useResultEffects } from './hooks/useResultEffects'
import { useResultActions } from './hooks/useResultActions'
import { PAGE_MODE_OPTIONS, hasRenderableScene } from './utils'
import DegradedBanner from './components/DegradedBanner'
import SourceFallback from './components/SourceFallback'
import StateViews from './components/StateViews'
import './index.scss'

export default function Result() {
  const state = useResultState()
  const {
    navBarHeight, pageMode, setPageMode,
    vocabList, vocabSavedMap, wordPopup, setWordPopup,
    activeMarkId, selectedWord, activeSentenceId,
    animTrigger, favorited, vocabHighlights,
    showModeSheet, setShowModeSheet, tempConfig,
    pageState, sceneData, requestParams, errorCode, errorMsg,
    recordId, cloudId, isReplayMode,
  } = state

  useResultEffects({
    recordId, cloudId, sceneData, pageState,
    setFavorited: state.setFavorited,
    setVocabList: state.setVocabList,
    setVocabSavedMap: state.setVocabSavedMap,
    setVocabHighlights: state.setVocabHighlights,
    loadRecord: state.loadRecord,
    recoverActiveTask: state.recoverActiveTask,
    setWordPopup,
  })

  const actions = useResultActions({
    recordId, cloudId, requestParams, isReplayMode, pageState,
    favorited, wordPopup, activeSentenceId,
    setFavorited: state.setFavorited,
    setAnimTrigger: state.setAnimTrigger,
    setActiveMarkId: state.setActiveMarkId,
    setSelectedWord: state.setSelectedWord,
    setActiveSentenceId: state.setActiveSentenceId,
    setWordPopup,
    setVocabList: state.setVocabList,
    setShowModeSheet, setTempConfig: state.setTempConfig,
    analyze: state.analyze,
  })

  useShareAppMessage(() => {
    const academicVm = sceneData?.schemaVersion === '3.0.0-academic' ? sceneData as AcademicRenderSceneVm : null
    const academicTitle = academicVm?.title
    const firstSentence = sceneData?.article.sentences[0]?.text
    const title = academicTitle
      || (firstSentence ? firstSentence.split('\n')[0].slice(0, 30) + '...' : null)
      || 'Claread透读 - AI 英语深度解析'
    const path = recordId
      ? `${ROUTES.RESULT}?recordId=${recordId}&mode=replay`
      : ROUTES.RESULT
    return { title, path }
  })

  const isAcademicMode = sceneData?.schemaVersion === '3.0.0-academic'
  const academicVm = isAcademicMode ? (sceneData as AcademicRenderSceneVm) : null
  const academicContentSummary = academicVm?.contentSummary ?? null
  const academicTitle = academicVm?.title ?? null

  const articleHeader = useMemo(() => {
    if (!sceneData?.request) return null
    const { request } = sceneData
    return (
      <View className='article-header'>
        {isAcademicMode && academicTitle && (
          <Text className='article-title'>{academicTitle}</Text>
        )}
        <View className='article-meta-row'>
          <Text className='source-tag'>
            {request.sourceType === 'user_input' ? '手动输入' : '每日文章'}
          </Text>
          <Text className='level-tag'>
            {getSafeDisplayLabel(request.readingGoal, request.readingVariant)}
          </Text>
          {isAcademicMode && (
            <Text className='mode-tag-academic'>学术模式</Text>
          )}
        </View>
      </View>
    )
  }, [sceneData, isAcademicMode, academicTitle])

  const paragraphBlocks = useMemo(() => {
    if (!sceneData?.article?.paragraphs?.length) return null
    return sceneData.article.paragraphs.map((paragraph, idx) => {
      const sentences = paragraph.sentenceIds
        .map((id) => sceneData.article.sentences.find((s) => s.sentenceId === id))
        .filter((s): s is NonNullable<typeof s> => !!s)

      return (
        <ParagraphBlock
          key={`${paragraph.paragraphId}-${idx}`}
          order={idx + 1}
          sentences={sentences}
          translations={sceneData.translations}
          inlineMarks={sceneData.inlineMarks}
          activeMarkId={activeMarkId}
          selectedWord={selectedWord}
          vocabList={vocabList}
          vocabSavedMap={vocabSavedMap}
          tailEntries={sceneData.sentenceEntries}
          pageMode={pageMode}
          recordId={recordId || undefined}
          activeSentenceId={activeSentenceId}
          onWordClick={actions.handleWordClick}
          onSentenceClick={actions.handleSentenceClick}
        />
      )
    })
  }, [sceneData, activeMarkId, selectedWord, vocabList, vocabSavedMap, pageMode, recordId, activeSentenceId])

  if (!sceneData) {
    if (pageState === 'loading') {
      return <StateViews pageState='loading' errorCode={null} errorMsg={null} navBarHeight={navBarHeight} onRetry={actions.handleRetry} />
    }
    if (pageState === 'empty') {
      return <StateViews pageState='empty' errorCode={errorCode} errorMsg={errorMsg} navBarHeight={navBarHeight} onRetry={actions.handleRetry} />
    }
    if (pageState === 'failed' || pageState === 'timeout' || pageState === 'network_fail') {
      return <StateViews pageState={pageState} errorCode={errorCode} errorMsg={errorMsg} navBarHeight={navBarHeight} onRetry={actions.handleRetry} />
    }
    return <StateViews pageState='loading' errorCode={null} errorMsg={null} navBarHeight={navBarHeight} onRetry={actions.handleRetry} />
  }

  if (!hasRenderableScene(sceneData)) {
    return (
      <SourceFallback
        pageState={pageState} sceneData={sceneData}
        requestText={requestParams?.text} isReplayMode={isReplayMode}
        navBarHeight={navBarHeight} onRetry={actions.handleRetry}
      />
    )
  }

  return (
    <View className='result-page'>
      <NavBar title='Claread透读' showBack showHome />
      <View className='result-nav-spacer' style={{ height: navBarHeight + 'px' }} />

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
                role='tab'
                aria-selected={pageMode === mode.value}
                aria-label={`${mode.label}模式`}
              >
                <Text className='mode-tab-label'>{mode.label}</Text>
              </View>
            ))}
          </View>
        </View>

        <DegradedBanner pageState={pageState} sceneData={sceneData} onRetry={actions.handleRetry} />

        {isAcademicMode && sceneData?.warnings?.some(w => w.level === 'info' || w.code === 'NON_ACADEMIC_TEXT_DETECTED' || w.code === 'FRAGMENT_INPUT_DETECTED') && (
          <View className='academic-info-banner'>
            <LucideIcon name='info' size={14} color='var(--term-accent)' />
            <Text className='academic-info-text'>
              {sceneData.warnings.find(w => w.code === 'NON_ACADEMIC_TEXT_DETECTED')
                ? '检测到输入文本可能不是学术文献，已自动调整解析策略。如需英语学习模式，可切换至日常阅读。'
                : '检测到片段输入，内容概要可能不完整。'}
            </Text>
          </View>
        )}

        <ScrollView className='article-scroll' scrollY enhanced showScrollbar={false} onScroll={actions.handleScroll}>
          <View className='article-container'>
            {articleHeader}
            {academicContentSummary && (
              <ContentSummaryCard summary={academicContentSummary} />
            )}
            {paragraphBlocks}

            <View className='article-end-actions'>
              <View
                key={`fav-btn-${animTrigger}`}
                className={`end-btn-secondary ${favorited ? 'favorited' : ''} ${animTrigger > 0 ? 'animate-spring' : ''}`}
                onClick={actions.handleToggleFavorite}
                role='button'
                aria-label={favorited ? '取消收藏' : '加入收藏'}
              >
                <LucideIcon name='bookmark' size={18} color={favorited ? 'var(--color-warn)' : 'var(--text-main)'} />
                <Text className={favorited ? 'favorited-text' : ''}>{favorited ? '已收藏' : '收藏'}</Text>
              </View>
              <View
                className='end-btn-primary'
                onClick={actions.handleRetry}
                role='button'
                aria-label='分析新文章'
              >
                <LucideIcon name='plus' size={18} color='var(--color-white)' />
                <Text>再分析一篇</Text>
              </View>
            </View>

            {sceneData && (pageState === 'normal' || pageState === 'degraded_light') && (
              <FeedbackWidget
                recordId={recordId || ''}
                readingGoal={sceneData.request?.readingGoal}
                readingVariant={sceneData.request?.readingVariant}
                userFacingState={(sceneData as AnyRenderSceneVm).userFacingState}
              />
            )}
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
        readingVariant={sceneData?.request?.readingVariant}
        onClose={actions.handleClosePopup}
        onExpand={() => setWordPopup({ ...wordPopup, mode: 'full' })}
        onAddVocab={actions.handleAddVocab}
        onFavorite={(w) => { import('../../services/analytics').then(m => m.track('favorite_word', { word: w })) }}
      />

      <BottomSheetSelect
        visible={showModeSheet}
        currentGoal={tempConfig.purpose}
        currentLevel={tempConfig.level}
        onClose={() => setShowModeSheet(false)}
        onSelect={actions.handleModeSelect}
      />
    </View>
  )
}

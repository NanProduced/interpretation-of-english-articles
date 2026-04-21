/**
 * 单词复习页面
 *
 * 基于艾宾浩斯遗忘曲线的复习系统
 * 实现卡片式闪卡复习体验，支持：
 * - 回忆模式：先显示单词，点击显示释义
 * - 5级评分系统：0-5分，影响下次复习时间
 * - 进度追踪
 * - 跳转回原文语境
 *
 * 支持两种模式：
 * - 本地模式：未登录用户使用本地生词本
 * - 云端模式：已登录用户同步到云端
 */

import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState, useCallback, useEffect, useMemo } from 'react'
import { useAuthStore } from '../../stores/auth'
import {
  fetchDueVocabulary,
  submitReview,
} from '../../services/api/vocabulary.client'
import {
  getAllLocalDueVocabulary,
  submitLocalReview,
} from '../../services/review.service'
import type { DueVocabItem, ReviewQuality, ReviewSubmitResult } from '../../types/view/vocabulary.vm'
import { track } from '../../services/analytics'
import NavBar from '../../components/NavBar'
import LucideIcon from '../../components/LucideIcon'
import { useLayoutStore } from '../../stores/layout'
import { updateVocabEntry, getVocabulary } from '../../services/storage'
import './index.scss'

type ReviewStep = 'loading' | 'showing' | 'revealed' | 'finished'

interface ReviewSession {
  items: DueVocabItem[]
  currentIndex: number
  step: ReviewStep
  results: Array<{
    vocabId: string
    quality: ReviewQuality
    success: boolean
  }>
}

const REVIEW_QUALITY_OPTIONS: Array<{
  value: ReviewQuality
  label: string
  description: string
  emoji: string
  color: string
}> = [
  { value: 0, label: '忘记', description: '完全没印象', emoji: '😵', color: '#dc2626' },
  { value: 1, label: '模糊', description: '几乎忘记', emoji: '😟', color: '#ea580c' },
  { value: 2, label: '艰难', description: '有点印象', emoji: '🤔', color: '#ca8a04' },
  { value: 3, label: '记住', description: '刚好想起', emoji: '😊', color: '#16a34a' },
  { value: 4, label: '熟练', description: '轻松回忆', emoji: '😄', color: '#2563eb' },
  { value: 5, label: '完美', description: '完全掌握', emoji: '✨', color: '#7c3aed' },
]

export default function ReviewPage() {
  const { navBarHeight } = useLayoutStore()
  const { isLoggedIn } = useAuthStore()
  const [session, setSession] = useState<ReviewSession>({
    items: [],
    currentIndex: 0,
    step: 'loading',
    results: [],
  })

  const currentItem = useMemo(() => {
    if (session.currentIndex < session.items.length) {
      return session.items[session.currentIndex]
    }
    return null
  }, [session.currentIndex, session.items])

  const progress = useMemo(() => {
    if (session.items.length === 0) return 0
    return ((session.currentIndex + (session.step === 'revealed' ? 0.5 : 0)) / session.items.length) * 100
  }, [session.currentIndex, session.items.length, session.step])

  const stats = useMemo(() => {
    const total = session.results.length
    const correct = session.results.filter(r => r.quality >= 3).length
    const wrong = session.results.filter(r => r.quality < 3).length
    const avgQuality = total > 0
      ? session.results.reduce((sum, r) => sum + r.quality, 0) / total
      : 0
    return { total, correct, wrong, avgQuality: Math.round(avgQuality * 10) / 10 }
  }, [session.results])

  function updateLocalVocabAfterReview(vocabId: string, result: ReviewSubmitResult) {
    try {
      const vocab = getVocabulary()
      const index = vocab.findIndex(v => v.id === vocabId)
      if (index === -1) return

      const currentEntry = vocab[index]
      const updatedReviewCount = (currentEntry.reviewCount || 0) + 1

      updateVocabEntry(vocabId, {
        masteryStatus: result.newMasteryStatus as any,
        mastered: result.newMasteryStatus === 'mastered',
        reviewCount: updatedReviewCount,
        lastReviewedAt: Date.now(),
        nextReviewAt: result.nextReviewAt,
        easeFactor: result.newEaseFactor,
        repetitions: result.newRepetitions,
        reviewInterval: result.newInterval,
      })
    } catch (e) {
      console.error('[review] update local vocab failed:', e)
    }
  }

  const loadReviewItems = useCallback(async () => {
    try {
      let allItems: DueVocabItem[] = []

      if (isLoggedIn) {
        const overdueResult = await fetchDueVocabulary('overdue', 100)
        const todayResult = await fetchDueVocabulary('today', 100)

        allItems = [
          ...overdueResult.items,
          ...todayResult.items.filter(item =>
            !overdueResult.items.some(o => o.id === item.id)
          ),
        ]

        track('start_review_session', {
          totalItems: allItems.length,
          overdueCount: overdueResult.items.length,
          todayCount: todayResult.items.length,
          mode: 'cloud',
        })
      } else {
        const localResult = getAllLocalDueVocabulary(100)
        allItems = localResult.items

        track('start_review_session', {
          totalItems: allItems.length,
          mode: 'local',
        })
      }

      if (allItems.length === 0) {
        Taro.showModal({
          title: '太棒了！',
          content: '今天没有需要复习的单词，继续保持！',
          showCancel: false,
          confirmText: '返回',
          success: () => {
            Taro.navigateBack()
          },
        })
        setSession(prev => ({ ...prev, step: 'finished' }))
        return
      }

      setSession({
        items: allItems,
        currentIndex: 0,
        step: 'showing',
        results: [],
      })
    } catch (e) {
      console.error('[review] load items failed:', e)
      Taro.showToast({ title: '加载失败', icon: 'error' })
    }
  }, [isLoggedIn])

  useEffect(() => {
    loadReviewItems()
  }, [loadReviewItems])

  const revealCard = useCallback(() => {
    setSession(prev => ({
      ...prev,
      step: 'revealed',
    }))
  }, [])

  const submitAnswer = useCallback(async (quality: ReviewQuality) => {
    if (!currentItem) return

    try {
      let result: ReviewSubmitResult

      if (isLoggedIn) {
        result = await submitReview(currentItem.id, quality)
        updateLocalVocabAfterReview(currentItem.id, result)
      } else {
        const localResult = submitLocalReview(currentItem.id, quality)
        result = {
          vocabId: localResult.vocabId,
          success: localResult.success,
          nextReviewAt: localResult.nextReviewAt,
          newEaseFactor: localResult.newEaseFactor,
          newInterval: localResult.newInterval,
          newRepetitions: localResult.newRepetitions,
          newMasteryStatus: localResult.newMasteryStatus,
          quality: localResult.quality,
          message: localResult.message,
        }
      }

      track('review_answer_submit', {
        vocabId: currentItem.id,
        quality,
        success: result.success,
        mode: isLoggedIn ? 'cloud' : 'local',
      })

      setSession(prev => {
        const newResults = [
          ...prev.results,
          {
            vocabId: currentItem.id,
            quality,
            success: result.success,
          },
        ]

        const nextIndex = prev.currentIndex + 1

        if (nextIndex >= prev.items.length) {
          track('complete_review_session', {
            totalItems: prev.items.length,
            correctCount: newResults.filter(r => r.quality >= 3).length,
            avgQuality: newResults.reduce((sum, r) => sum + r.quality, 0) / newResults.length,
            mode: isLoggedIn ? 'cloud' : 'local',
          })

          return {
            ...prev,
            results: newResults,
            step: 'finished',
          }
        }

        return {
          ...prev,
          currentIndex: nextIndex,
          step: 'showing',
          results: newResults,
        }
      })

      if (quality >= 3) {
        Taro.showToast({ title: result.message, icon: 'success' })
      } else {
        Taro.showToast({ title: result.message, icon: 'none' })
      }
    } catch (e) {
      console.error('[review] submit failed:', e)
      Taro.showToast({ title: '提交失败', icon: 'error' })
    }
  }, [currentItem, isLoggedIn])

  const goToResult = useCallback(() => {
    if (!currentItem?.sourceRefs?.[0]?.clientRecordId) return
    const ref = currentItem.sourceRefs[0]
    let url = `/pages/result/index?recordId=${ref.clientRecordId}&mode=replay`
    if (ref.sourceSentenceId) {
      url += `&sentenceId=${ref.sourceSentenceId}`
    }
    Taro.navigateTo({ url })
  }, [currentItem])

  const restartReview = useCallback(() => {
    setSession({
      items: [],
      currentIndex: 0,
      step: 'loading',
      results: [],
    })
    loadReviewItems()
  }, [loadReviewItems])

  const renderLoading = () => (
    <View className='review-loading'>
      <LucideIcon name='loader2' size={48} color='var(--color-ink)' className='spinning' />
      <Text className='loading-text'>准备复习中...</Text>
    </View>
  )

  const renderFinished = () => (
    <View className='review-finished'>
      <View className='celebration-icon'>
        <LucideIcon name='trophy' size={80} color='#f59e0b' />
      </View>
      <Text className='finished-title'>复习完成！</Text>

      {!isLoggedIn && (
        <Text className='mode-hint'>
          💡 登录后可同步复习数据到云端，多设备共享
        </Text>
      )}

      <View className='finished-stats'>
        <View className='stat-card'>
          <Text className='stat-number'>{stats.total}</Text>
          <Text className='stat-label'>复习单词</Text>
        </View>
        <View className='stat-card success'>
          <Text className='stat-number'>{stats.correct}</Text>
          <Text className='stat-label'>记住了</Text>
        </View>
        <View className='stat-card warning'>
          <Text className='stat-number'>{stats.wrong}</Text>
          <Text className='stat-label'>需加强</Text>
        </View>
        <View className='stat-card highlight'>
          <Text className='stat-number'>{stats.avgQuality}</Text>
          <Text className='stat-label'>平均评分</Text>
        </View>
      </View>

      {stats.wrong > 0 && (
        <Text className='finished-hint'>
          有 {stats.wrong} 个单词需要加强复习，它们会更快地出现在下次复习中
        </Text>
      )}

      <View className='finished-actions'>
        <View className='action-btn primary' onClick={() => Taro.navigateBack()}>
          <LucideIcon name='arrowLeft' size={20} color='#fff' />
          <Text className='btn-text'>返回生词本</Text>
        </View>
        <View className='action-btn secondary' onClick={restartReview}>
          <LucideIcon name='refreshCw' size={20} color='var(--color-ink)' />
          <Text className='btn-text'>再复习一遍</Text>
        </View>
      </View>
    </View>
  )

  const renderCard = () => {
    if (!currentItem) return null

    return (
      <View className='review-card-container'>
        <View
          className={`review-card ${session.step === 'revealed' ? 'revealed' : ''}`}
          onClick={session.step === 'showing' ? revealCard : undefined}
        >
          <View className='card-front'>
            <View className='card-content'>
              <Text className='word-display'>{currentItem.displayWord}</Text>
              {currentItem.phonetic && (
                <Text className='phonetic-display'>/{currentItem.phonetic}/</Text>
              )}
              {currentItem.partOfSpeech && (
                <View className='pos-tag'>
                  <Text>{currentItem.partOfSpeech}</Text>
                </View>
              )}
            </View>
            <View className='card-hint'>
              <LucideIcon name='eye' size={20} color='var(--text-muted)' />
              <Text className='hint-text'>点击显示释义</Text>
            </View>
          </View>

          <View className='card-back'>
            <View className='card-content'>
              <View className='word-row'>
                <Text className='word-display-small'>{currentItem.displayWord}</Text>
                {currentItem.phonetic && (
                  <Text className='phonetic-small'>/{currentItem.phonetic}/</Text>
                )}
              </View>

              <View className='meaning-section'>
                {currentItem.partOfSpeech && (
                  <View className='pos-tag'>
                    <Text>{currentItem.partOfSpeech}</Text>
                  </View>
                )}
                <Text className='meaning-text'>{currentItem.shortMeaning}</Text>
              </View>

              {currentItem.sourceSentence && (
                <View className='context-section' onClick={goToResult}>
                  <LucideIcon name='quote' size={16} color='var(--text-muted)' />
                  <Text className='context-text'>"{currentItem.sourceSentence}"</Text>
                  {currentItem.sourceRefs?.[0]?.clientRecordId && (
                    <View className='context-link'>
                      <Text className='link-text'>查看原文</Text>
                      <LucideIcon name='externalLink' size={14} color='var(--color-primary)' />
                    </View>
                  )}
                </View>
              )}
            </View>

            <View className='quality-section'>
              <Text className='quality-title'>你对这个单词的记忆程度？</Text>
              <View className='quality-buttons'>
                {REVIEW_QUALITY_OPTIONS.map((option) => (
                  <View
                    key={option.value}
                    className='quality-btn'
                    onClick={() => submitAnswer(option.value)}
                    style={{
                      '--btn-color': option.color,
                    } as React.CSSProperties}
                  >
                    <Text className='btn-emoji'>{option.emoji}</Text>
                    <Text className='btn-label'>{option.label}</Text>
                    <Text className='btn-desc'>{option.description}</Text>
                  </View>
                ))}
              </View>
            </View>
          </View>
        </View>
      </View>
    )
  }

  return (
    <View className='review-page'>
      <NavBar title='单词复习' showBack />
      <View style={{ height: navBarHeight + 'px', flexShrink: 0 }} />

      {session.step !== 'loading' && session.step !== 'finished' && (
        <View className='progress-header'>
          <View className='progress-info'>
            <Text className='progress-count'>
              {session.currentIndex + 1} / {session.items.length}
            </Text>
            <Text className='progress-label'>个单词</Text>
          </View>
          <View className='progress-bar'>
            <View
              className='progress-fill'
              style={{ width: `${progress}%` }}
            />
          </View>
        </View>
      )}

      <View className='main-content'>
        {session.step === 'loading' && renderLoading()}
        {session.step === 'finished' && renderFinished()}
        {(session.step === 'showing' || session.step === 'revealed') && renderCard()}
      </View>
    </View>
  )
}

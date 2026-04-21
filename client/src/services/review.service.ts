/**
 * 本地复习系统服务
 *
 * 基于艾宾浩斯遗忘曲线的 SM-2 算法实现。
 * 支持未登录用户的本地生词本复习。
 *
 * SM-2 算法核心逻辑：
 * - 易度因子 (Ease Factor, EF): 默认 2.5，最低 1.3
 * - 复习间隔 (Interval): 两次复习之间的天数
 * - 连续成功次数 (Repetitions): 连续成功复习的次数
 */

import type { VocabEntry, DueVocabItem, ReviewStats, ReviewQuality } from '../types/view/vocabulary.vm'
import { getVocabulary, updateVocabEntry } from './storage'

const SM2_DEFAULT_EASE_FACTOR = 2.5
const SM2_MIN_EASE_FACTOR = 1.3
const SM2_FIRST_INTERVAL = 1
const SM2_SECOND_INTERVAL = 6

export function calculateNextReview(
  currentEaseFactor: number,
  currentInterval: number,
  currentRepetitions: number,
  quality: number,
): { newEaseFactor: number; newInterval: number; newRepetitions: number } {
  if (quality < 0 || quality > 5) {
    throw new Error('Quality must be between 0 and 5')
  }

  if (quality >= 3) {
    let newInterval: number
    if (currentRepetitions === 0) {
      newInterval = SM2_FIRST_INTERVAL
    } else if (currentRepetitions === 1) {
      newInterval = SM2_SECOND_INTERVAL
    } else {
      newInterval = Math.round(currentInterval * currentEaseFactor)
    }

    const delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    let newEaseFactor = currentEaseFactor + delta
    newEaseFactor = Math.max(newEaseFactor, SM2_MIN_EASE_FACTOR)

    const newRepetitions = currentRepetitions + 1

    return {
      newEaseFactor: Math.round(newEaseFactor * 1000) / 1000,
      newInterval,
      newRepetitions,
    }
  } else {
    return {
      newEaseFactor: currentEaseFactor,
      newInterval: SM2_FIRST_INTERVAL,
      newRepetitions: 0,
    }
  }
}

export function determineMasteryStatus(
  repetitions: number,
  easeFactor: number,
  quality: number,
): 'new' | 'learning' | 'mastered' | 'archived' {
  if (repetitions >= 5 && easeFactor >= 2.5) {
    return 'mastered'
  } else if (repetitions >= 3) {
    return 'learning'
  } else if (quality < 3) {
    return 'learning'
  } else if (repetitions === 0) {
    return 'new'
  } else {
    return 'learning'
  }
}

export function getReviewMessage(quality: number, repetitions: number): string {
  if (quality >= 4) {
    if (repetitions >= 5) {
      return '太棒了！这个单词已经完全掌握了！'
    } else if (repetitions >= 3) {
      return '记得很好，继续保持！'
    } else {
      return '不错，继续复习巩固！'
    }
  } else if (quality === 3) {
    return '勉强记住了，下次要多注意哦'
  } else if (quality === 2) {
    return '有点模糊，需要加强复习'
  } else if (quality === 1) {
    return '几乎忘记了，明天重新开始'
  } else {
    return '完全忘记了，需要重新学习'
  }
}

export function initializeReviewFields(entry: VocabEntry): void {
  const now = Date.now()
  const oneDayMs = 24 * 60 * 60 * 1000

  const updates: Partial<VocabEntry> = {}

  if (entry.easeFactor === undefined) {
    updates.easeFactor = SM2_DEFAULT_EASE_FACTOR
  }

  if (entry.repetitions === undefined) {
    updates.repetitions = 0
  }

  if (entry.reviewInterval === undefined) {
    updates.reviewInterval = SM2_FIRST_INTERVAL
  }

  if (entry.reviewCount === undefined) {
    updates.reviewCount = 0
  }

  if (entry.masteryStatus === undefined) {
    updates.masteryStatus = 'new'
    updates.mastered = false
  }

  if (entry.nextReviewAt === undefined) {
    if (entry.lastReviewedAt) {
      const daysSinceLastReview = Math.floor((now - entry.lastReviewedAt) / oneDayMs)
      const nextInterval = entry.reviewInterval || SM2_FIRST_INTERVAL
      if (daysSinceLastReview >= nextInterval) {
        updates.nextReviewAt = now
      } else {
        updates.nextReviewAt = entry.lastReviewedAt + nextInterval * oneDayMs
      }
    } else {
      updates.nextReviewAt = now
    }
  }

  if (Object.keys(updates).length > 0) {
    updateVocabEntry(entry.id, updates)
  }
}

export interface LocalReviewStats {
  totalVocab: number
  dueToday: number
  overdue: number
  newWords: number
  learning: number
  mastered: number
}

export function getLocalReviewStats(): LocalReviewStats {
  const vocab = getVocabulary().filter(v => !v.tombstone)

  const now = Date.now()
  const oneDayMs = 24 * 60 * 60 * 1000

  const todayStart = new Date(now)
  todayStart.setHours(0, 0, 0, 0)
  const todayStartMs = todayStart.getTime()
  const todayEndMs = todayStartMs + oneDayMs

  let dueToday = 0
  let overdue = 0
  let newWords = 0
  let learning = 0
  let mastered = 0

  for (const entry of vocab) {
    if (entry.easeFactor === undefined) {
      initializeReviewFields(entry)
    }

    const masteryStatus = entry.masteryStatus || 'new'
    if (masteryStatus === 'mastered') {
      mastered++
    } else if (masteryStatus === 'new') {
      newWords++
    } else {
      learning++
    }

    if (masteryStatus === 'mastered' || masteryStatus === 'archived') {
      continue
    }

    const nextReviewAt = entry.nextReviewAt
    if (nextReviewAt === undefined) {
      continue
    }

    if (nextReviewAt < todayStartMs) {
      overdue++
    } else if (nextReviewAt >= todayStartMs && nextReviewAt < todayEndMs) {
      dueToday++
    }
  }

  return {
    totalVocab: vocab.length,
    dueToday,
    overdue,
    newWords,
    learning,
    mastered,
  }
}

export function getLocalDueVocabulary(
  dueType: 'today' | 'overdue' | 'new' = 'today',
  limit = 100,
): { items: DueVocabItem[]; total: number; dueType: string } {
  const vocab = getVocabulary().filter(v => !v.tombstone)

  const now = Date.now()
  const oneDayMs = 24 * 60 * 60 * 1000

  const todayStart = new Date(now)
  todayStart.setHours(0, 0, 0, 0)
  const todayStartMs = todayStart.getTime()
  const todayEndMs = todayStartMs + oneDayMs

  const dueItems: DueVocabItem[] = []

  for (const entry of vocab) {
    if (entry.easeFactor === undefined) {
      initializeReviewFields(entry)
    }

    const masteryStatus = entry.masteryStatus || 'new'
    if (masteryStatus === 'mastered' || masteryStatus === 'archived') {
      continue
    }

    const nextReviewAt = entry.nextReviewAt
    if (nextReviewAt === undefined) {
      continue
    }

    let matches = false

    if (dueType === 'today') {
      matches = nextReviewAt >= todayStartMs && nextReviewAt < todayEndMs
    } else if (dueType === 'overdue') {
      matches = nextReviewAt < todayStartMs
    } else if (dueType === 'new') {
      matches = masteryStatus === 'new'
    }

    if (matches) {
      dueItems.push({
        id: entry.id,
        lemma: entry.lemma,
        displayWord: entry.word,
        phonetic: entry.phonetic,
        partOfSpeech: entry.partOfSpeech,
        shortMeaning: entry.meaning,
        masteryStatus: masteryStatus as DueVocabItem['masteryStatus'],
        repetitions: entry.repetitions || 0,
        easeFactor: entry.easeFactor || SM2_DEFAULT_EASE_FACTOR,
        reviewInterval: entry.reviewInterval || SM2_FIRST_INTERVAL,
        nextReviewAt: entry.nextReviewAt,
        sourceSentence: entry.sentence || entry.sourceRefs?.[0]?.sourceSentence,
        sourceRefs: entry.sourceRefs,
      })
    }
  }

  if (dueType === 'overdue') {
    dueItems.sort((a, b) => (a.nextReviewAt || 0) - (b.nextReviewAt || 0))
  } else if (dueType === 'today') {
    dueItems.sort((a, b) => (a.nextReviewAt || 0) - (b.nextReviewAt || 0))
  } else if (dueType === 'new') {
    dueItems.sort((a, b) => {
      const idxA = vocab.findIndex(v => v.id === a.id)
      const idxB = vocab.findIndex(v => v.id === b.id)
      return idxA - idxB
    })
  }

  return {
    items: dueItems.slice(0, limit),
    total: dueItems.length,
    dueType,
  }
}

export interface LocalSubmitReviewResult {
  vocabId: string
  success: boolean
  nextReviewAt?: number
  newEaseFactor: number
  newInterval: number
  newRepetitions: number
  newMasteryStatus: string
  quality: number
  message: string
}

export function submitLocalReview(
  vocabId: string,
  quality: ReviewQuality,
): LocalSubmitReviewResult {
  const vocab = getVocabulary()
  const index = vocab.findIndex(v => v.id === vocabId && !v.tombstone)

  if (index === -1) {
    throw new Error('Vocabulary entry not found')
  }

  const entry = vocab[index]

  if (entry.easeFactor === undefined) {
    initializeReviewFields(entry)
  }

  const currentEase = entry.easeFactor || SM2_DEFAULT_EASE_FACTOR
  const currentInterval = entry.reviewInterval || SM2_FIRST_INTERVAL
  const currentRepetitions = entry.repetitions || 0
  const currentReviewCount = entry.reviewCount || 0

  const { newEaseFactor, newInterval, newRepetitions } = calculateNextReview(
    currentEase,
    currentInterval,
    currentRepetitions,
    quality,
  )

  const newMasteryStatus = determineMasteryStatus(
    newRepetitions,
    newEaseFactor,
    quality,
  )

  const now = Date.now()
  const oneDayMs = 24 * 60 * 60 * 1000
  const nextReviewAt = now + newInterval * oneDayMs

  const message = getReviewMessage(quality, newRepetitions)

  updateVocabEntry(vocabId, {
    masteryStatus: newMasteryStatus,
    mastered: newMasteryStatus === 'mastered',
    reviewCount: currentReviewCount + 1,
    lastReviewedAt: now,
    nextReviewAt,
    easeFactor: newEaseFactor,
    repetitions: newRepetitions,
    reviewInterval: newInterval,
  })

  return {
    vocabId,
    success: true,
    nextReviewAt,
    newEaseFactor,
    newInterval,
    newRepetitions,
    newMasteryStatus,
    quality,
    message,
  }
}

export function getAllLocalDueVocabulary(limit = 100): { items: DueVocabItem[]; total: number } {
  const overdueResult = getLocalDueVocabulary('overdue', 100)
  const todayResult = getLocalDueVocabulary('today', 100)

  const allItems: DueVocabItem[] = [
    ...overdueResult.items,
    ...todayResult.items.filter(item =>
      !overdueResult.items.some(o => o.id === item.id)
    ),
  ]

  return {
    items: allItems.slice(0, limit),
    total: allItems.length,
  }
}

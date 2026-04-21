/**
 * 统一的词汇服务
 *
 * 负责合并云端和本地词汇数据，确保各页面数据源一致。
 * 同时支持：
 * - 获取合并后的词汇列表
 * - 获取合并后的复习统计
 * - 获取合并后的待复习列表
 */

import { getVocabulary } from './storage'
import { fetchCloudVocabulary, fetchReviewStats, fetchDueVocabulary } from './api/vocabulary.client'
import { getLocalReviewStats, getLocalDueVocabulary, initializeReviewFields } from './review.service'
import type { VocabEntry, ReviewStats, DueVocabItem } from '../types/view/vocabulary.vm'

export function mergeVocabCloudWithLocal(
  cloudItems: VocabEntry[],
  localItems: VocabEntry[],
): VocabEntry[] {
  const cloudMap = new Map<string, VocabEntry>()
  for (const item of cloudItems) {
    if (!item.tombstone) {
      cloudMap.set(item.id, item)
    }
  }

  const result: VocabEntry[] = []
  const processedLocalIds = new Set<string>()

  for (const local of localItems) {
    if (local.tombstone) {
      continue
    }

    if (local.pendingOp) {
      result.push({ ...local })
      processedLocalIds.add(local.id)
      continue
    }

    if (local.syncState === 'local_only') {
      result.push({ ...local })
      processedLocalIds.add(local.id)
      continue
    }

    const cloud = cloudMap.get(local.id)
    if (cloud) {
      const localLastReviewed = local.lastReviewedAt || 0
      const cloudLastReviewed = cloud.lastReviewedAt || 0

      if (localLastReviewed > cloudLastReviewed) {
        result.push({
          ...cloud,
          mastered: local.mastered,
          masteryStatus: local.masteryStatus,
          reviewCount: local.reviewCount,
          lastReviewedAt: local.lastReviewedAt,
          nextReviewAt: local.nextReviewAt,
          easeFactor: local.easeFactor,
          repetitions: local.repetitions,
          reviewInterval: local.reviewInterval,
        })
      } else if (cloudLastReviewed > localLastReviewed) {
        result.push({
          ...cloud,
          mastered: cloud.mastered,
        })
      } else {
        result.push({
          ...cloud,
          mastered: local.mastered !== cloud.mastered ? local.mastered : cloud.mastered,
          masteryStatus: local.masteryStatus || cloud.masteryStatus,
          reviewCount: local.reviewCount || cloud.reviewCount,
          lastReviewedAt: local.lastReviewedAt || cloud.lastReviewedAt,
          nextReviewAt: local.nextReviewAt || cloud.nextReviewAt,
          easeFactor: local.easeFactor || cloud.easeFactor,
          repetitions: local.repetitions || cloud.repetitions,
          reviewInterval: local.reviewInterval || cloud.reviewInterval,
        })
      }
      processedLocalIds.add(local.id)
      cloudMap.delete(local.id)
    } else {
      result.push({ ...local })
      processedLocalIds.add(local.id)
    }
  }

  for (const cloud of cloudMap.values()) {
    result.push({ ...cloud })
  }

  return result
}

export async function fetchAllCloudVocabulary(): Promise<VocabEntry[]> {
  let allCloudItems: VocabEntry[] = []
  let page = 1
  const pageSize = 100
  let hasMore = true

  while (hasMore) {
    const result = await fetchCloudVocabulary(page, pageSize)
    allCloudItems = allCloudItems.concat(result.items)
    hasMore = allCloudItems.length < result.total
    page++
  }

  return allCloudItems
}

export async function getMergedVocabulary(): Promise<VocabEntry[]> {
  const localItems = getVocabulary()

  const isLoggedIn = (await import('../stores/auth')).useAuthStore.getState().isLoggedIn

  if (!isLoggedIn) {
    for (const item of localItems) {
      if (item.easeFactor === undefined) {
        initializeReviewFields(item)
      }
    }
    return localItems.filter(v => !v.tombstone)
  }

  let cloudItems: VocabEntry[] = []
  try {
    cloudItems = await fetchAllCloudVocabulary()
  } catch (e) {
    console.warn('[vocab-service] fetch cloud vocab failed:', e)
    return localItems.filter(v => !v.tombstone)
  }

  return mergeVocabCloudWithLocal(cloudItems, localItems)
}

export async function getMergedReviewStats(): Promise<ReviewStats> {
  const localStats = getLocalReviewStats()

  const isLoggedIn = (await import('../stores/auth')).useAuthStore.getState().isLoggedIn

  if (!isLoggedIn) {
    return {
      totalVocab: localStats.totalVocab,
      dueToday: localStats.dueToday,
      overdue: localStats.overdue,
      newWords: localStats.newWords,
      learning: localStats.learning,
      mastered: localStats.mastered,
    }
  }

  try {
    const cloudStats = await fetchReviewStats()
    const mergedVocab = await getMergedVocabulary()

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

    for (const entry of mergedVocab) {
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
      totalVocab: mergedVocab.length,
      dueToday,
      overdue,
      newWords,
      learning,
      mastered,
    }
  } catch (e) {
    console.warn('[vocab-service] fetch cloud stats failed:', e)
    return {
      totalVocab: localStats.totalVocab,
      dueToday: localStats.dueToday,
      overdue: localStats.overdue,
      newWords: localStats.newWords,
      learning: localStats.learning,
      mastered: localStats.mastered,
    }
  }
}

export async function getMergedDueVocabulary(
  dueType: 'today' | 'overdue' | 'new' = 'today',
  limit = 100,
): Promise<{ items: DueVocabItem[]; total: number; dueType: string }> {
  const localResult = getLocalDueVocabulary(dueType, 1000)

  const isLoggedIn = (await import('../stores/auth')).useAuthStore.getState().isLoggedIn

  if (!isLoggedIn) {
    return {
      items: localResult.items.slice(0, limit),
      total: localResult.total,
      dueType,
    }
  }

  try {
    const cloudResult = await fetchDueVocabulary(dueType, 1000)
    const localItems = getVocabulary().filter(v => !v.tombstone)

    const pendingLocalIds = new Set<string>()
    for (const local of localItems) {
      if (local.pendingOp || local.syncState === 'local_only') {
        if (local.easeFactor === undefined) {
          initializeReviewFields(local)
        }

        const masteryStatus = local.masteryStatus || 'new'
        if (masteryStatus === 'mastered' || masteryStatus === 'archived') {
          continue
        }

        const nextReviewAt = local.nextReviewAt
        if (nextReviewAt === undefined) {
          continue
        }

        const now = Date.now()
        const oneDayMs = 24 * 60 * 60 * 1000
        const todayStart = new Date(now)
        todayStart.setHours(0, 0, 0, 0)
        const todayStartMs = todayStart.getTime()
        const todayEndMs = todayStartMs + oneDayMs

        let matches = false
        if (dueType === 'today') {
          matches = nextReviewAt >= todayStartMs && nextReviewAt < todayEndMs
        } else if (dueType === 'overdue') {
          matches = nextReviewAt < todayStartMs
        } else if (dueType === 'new') {
          matches = masteryStatus === 'new'
        }

        if (matches) {
          pendingLocalIds.add(local.id)
        }
      }
    }

    const cloudIds = new Set(cloudResult.items.map(i => i.id))
    const mergedItems: DueVocabItem[] = []

    for (const local of localItems) {
      if (pendingLocalIds.has(local.id) && !cloudIds.has(local.id)) {
        mergedItems.push({
          id: local.id,
          lemma: local.lemma,
          displayWord: local.word,
          phonetic: local.phonetic,
          partOfSpeech: local.partOfSpeech,
          shortMeaning: local.meaning,
          masteryStatus: (local.masteryStatus || 'new') as DueVocabItem['masteryStatus'],
          repetitions: local.repetitions || 0,
          easeFactor: local.easeFactor || 2.5,
          reviewInterval: local.reviewInterval || 1,
          nextReviewAt: local.nextReviewAt,
          sourceSentence: local.sentence || local.sourceRefs?.[0]?.sourceSentence,
          sourceRefs: local.sourceRefs,
        })
      }
    }

    for (const cloudItem of cloudResult.items) {
      if (!mergedItems.find(i => i.id === cloudItem.id)) {
        mergedItems.push(cloudItem)
      }
    }

    if (dueType === 'overdue') {
      mergedItems.sort((a, b) => (a.nextReviewAt || 0) - (b.nextReviewAt || 0))
    } else if (dueType === 'today') {
      mergedItems.sort((a, b) => (a.nextReviewAt || 0) - (b.nextReviewAt || 0))
    }

    return {
      items: mergedItems.slice(0, limit),
      total: mergedItems.length,
      dueType,
    }
  } catch (e) {
    console.warn('[vocab-service] fetch cloud due vocab failed:', e)
    return {
      items: localResult.items.slice(0, limit),
      total: localResult.total,
      dueType,
    }
  }
}

export async function getMergedAllDueVocabulary(limit = 100): Promise<{ items: DueVocabItem[]; total: number }> {
  const overdueResult = await getMergedDueVocabulary('overdue', 100)
  const todayResult = await getMergedDueVocabulary('today', 100)

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

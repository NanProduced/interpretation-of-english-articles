/**
 * CloudSyncService
 *
 * 分析成功后自动将本地数据同步到云端。
 * 所有操作均为 fire-and-forget，失败不影响本地数据。
 * 未登录时静默跳过。
 */

import Taro from '@tarojs/taro'
import { useAuthStore } from '../stores/auth'
import type { AnalysisRecord } from '../types/view/analysis-record.vm'
import type { FavoriteRecord } from '../types/view/favorites.vm'
import type { VocabEntry } from '../types/view/vocabulary.vm'
import { getRecord } from './storage'
import {
  saveRecordToCloud,
  fetchCloudRecordByClientId,
  deleteCloudRecord,
} from './api/records.client'
import {
  addFavoriteToCloud,
  removeFavoriteFromCloud,
} from './api/favorites.client'
import { addVocabToCloud } from './api/vocabulary.client'

// ---------------------------------------------------------------------------
// 工具函数
// ---------------------------------------------------------------------------

/** 计算字符串的简单哈希（用于 sourceTextHash，非安全用途） */
function hashString(str: string): string {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i)
    hash = (hash << 5) - hash + char
    hash = hash & hash // Convert to 32bit integer
  }
  return Math.abs(hash).toString(16).padStart(8, '0')
}

// ---------------------------------------------------------------------------
// CloudSyncService
// ---------------------------------------------------------------------------

const resolveCloudIdCache = new Map<string, Promise<string | null>>()

/** 尝试从本地或后端找回云端 UUID (带并发去重) */
async function resolveCloudId(clientRecordId: string): Promise<string | null> {
  // 1. 先看本地有没有内存中的新值
  const local = getRecord(clientRecordId)
  if (local?.cloudId) return local.cloudId

  if (resolveCloudIdCache.has(clientRecordId)) {
    return resolveCloudIdCache.get(clientRecordId)!
  }

  const promise = (async () => {
    try {
      const cloudRecord = await fetchCloudRecordByClientId(clientRecordId)
      if (cloudRecord?.cloudId) return cloudRecord.cloudId
    } catch {
      // 忽略 Lookup 失败
    } finally {
      // 一定时间后清理缓存，允许重试
      setTimeout(() => resolveCloudIdCache.delete(clientRecordId), 5000)
    }
    return null
  })()

  resolveCloudIdCache.set(clientRecordId, promise)
  return promise
}

// 简单队列机制，保证针对同一目标的云端同步请求有序执行
const syncQueues = new Map<string, Promise<void>>()

function enqueueSync(queueKey: string, task: () => Promise<void>): Promise<void> {
  const prev = syncQueues.get(queueKey) || Promise.resolve()
  const next = prev.then(task).catch(task) // 即便前一个失败，继续执行后一个
  syncQueues.set(queueKey, next)
  // 清理完成的队列
  next.finally(() => {
    if (syncQueues.get(queueKey) === next) {
      syncQueues.delete(queueKey)
    }
  })
  return next
}

export const CloudSyncService = {
  /**
   * 同步分析记录到云端（upsert）
   * - 未登录：静默跳过
   * - 已在云端存在：更新
   * - 网络失败：静默跳过，不阻塞
   */
  async syncRecord(record: AnalysisRecord): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return
    if (!record.sourceText) return

    try {
      await saveRecordToCloud({
        clientRecordId: record.recordId,
        title: record.title ?? null,
        sourceText: record.sourceText,
        sourceTextHash: hashString(record.sourceText),
        requestPayload: record.requestPayload,
        renderScene: record.renderScene,
        pageState: record.pageState,
      })
    } catch (err) {
      // 静默失败，不影响用户
      console.warn('[cloudSync] syncRecord failed', record.recordId, err)
    }
  },

  /**
   * 同步收藏状态到云端
   * @param cloudId 云端 UUID
   * @param clientRecordId 本地记录 ID
   * @param action 'add' | 'remove'
   */
  async syncFavorite(cloudId: string | undefined, clientRecordId: string, action: 'add' | 'remove'): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return
    
    return enqueueSync(`fav_${clientRecordId}`, async () => {
      let resolvedId = cloudId
      if (!resolvedId) {
        resolvedId = (await resolveCloudId(clientRecordId)) || undefined
      }

      if (!resolvedId) {
        console.warn('[cloudSync] syncFavorite skipped: missing cloudId even after resolve', clientRecordId)
        return
      }

      try {
        if (action === 'add') {
          await addFavoriteToCloud(resolvedId, clientRecordId)
        } else {
          await removeFavoriteFromCloud(resolvedId)
        }
      } catch (err) {
        console.warn('[cloudSync] syncFavorite failed', clientRecordId, action, err)
      }
    })
  },

  /**
   * 同步生词本条目到云端
   */
  async syncVocab(entry: VocabEntry): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return
    
    // 使用 lemma 或 word 作为去重队列 key，保证同一个词的同步是有序的
    const queueKey = `vocab_${entry.recordId}_${entry.lemma || entry.word}`
    
    return enqueueSync(queueKey, async () => {
      let resolvedRecordId = entry.cloudRecordId
      if (!resolvedRecordId && entry.recordId) {
        resolvedRecordId = (await resolveCloudId(entry.recordId)) || undefined
      }

      if (!resolvedRecordId) {
         console.warn('[cloudSync] syncVocab skipped: missing cloudRecordId for word', entry.word)
         return
      }

      try {
        // 这里的 entry 是 clone 的或者是最新的，确保带上 resolvedRecordId
        const res = await addVocabToCloud({ ...entry, cloudRecordId: resolvedRecordId })
        
        // 同步成功后，用云端返回的真正 UUID 替换本地的临时 ID，确保后续删除/更新操作能对准
        if (res.id && res.id !== entry.id) {
          const { getVocabulary, removeVocabEntry, saveVocabEntry } = await import('./storage')
          const currentVocab = getVocabulary()
          const target = currentVocab.find(v => v.id === entry.id)
          if (target) {
            removeVocabEntry(entry.id)
            saveVocabEntry({ ...target, id: res.id })
          }
        }
      } catch (err) {
        console.warn('[cloudSync] syncVocab failed', entry.word, err)
      }
    })
  },

  /**
   * 同步所有本地收藏到云端（登录后全量同步）
   * 注意：这要求本地记录必须带有 cloudId
   */
  async syncAllFavorites(localFavorites: FavoriteRecord[]): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return

    const records = localFavorites
      .map((favorite) => getRecord(favorite.recordId))
      .filter((record): record is AnalysisRecord => !!record)

    await Promise.allSettled(
      records
        .filter(r => r.isFavorited && r.cloudId)
        .map((r) => addFavoriteToCloud(r.cloudId!, r.recordId))
    )
  },

  /**
   * 同步所有本地生词本到云端（登录后全量同步）
   */
  async syncAllVocab(localVocab: VocabEntry[]): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return

    await Promise.allSettled(
      localVocab
        .filter(e => e.cloudRecordId)
        .map((entry) => addVocabToCloud(entry))
    )
  },
}

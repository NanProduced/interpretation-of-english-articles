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
    if (!cloudId) {
      console.warn('[cloudSync] syncFavorite skipped: missing cloudId')
      return
    }

    try {
      if (action === 'add') {
        await addFavoriteToCloud(cloudId, clientRecordId)
      } else {
        await removeFavoriteFromCloud(cloudId)
      }
    } catch (err) {
      console.warn('[cloudSync] syncFavorite failed', clientRecordId, action, err)
    }
  },

  /**
   * 同步生词本条目到云端
   */
  async syncVocab(entry: VocabEntry): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return
    if (!entry.cloudRecordId) {
       console.warn('[cloudSync] syncVocab skipped: missing cloudRecordId for word', entry.word)
       return
    }

    try {
      await addVocabToCloud(entry)
    } catch (err) {
      console.warn('[cloudSync] syncVocab failed', entry.word, err)
    }
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

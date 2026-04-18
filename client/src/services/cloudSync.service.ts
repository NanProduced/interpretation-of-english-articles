/**
 * 云同步服务
 *
 * 提供离线优先的同步功能
 * 所有涉及状态变更的同步操作，在网络失败时被可靠缓存
 * 网络恢复时自动在后台同步积压操作
 *
 * 向后兼容：保持原有 API 接口不变
 */

import { useAuthStore } from '../stores/auth'
import type { AnalysisRecord } from '../types/view/analysis-record.vm'
import type { FavoriteRecord } from '../types/view/favorites.vm'
import type { VocabEntry } from '../types/view/vocabulary.vm'
import { getRecord } from './storage'
import { syncService } from './sync'

/**
 * 云同步服务对象
 * 提供静态方法调用，保持向后兼容
 */
export const CloudSyncService = {
  /**
   * 初始化同步服务
   * 应该在应用启动时调用
   */
  async initialize(): Promise<void> {
    await syncService.initialize()
  },

  /**
   * 同步分析记录到云端
   * @param record 分析记录
   */
  async syncRecord(record: AnalysisRecord): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return
    syncService.enqueueRecordSync(record)
  },

  /**
   * 同步收藏状态到云端
   * @param cloudId 云端 ID（可选）
   * @param clientRecordId 客户端记录 ID
   * @param action 操作类型：add 或 remove
   */
  async syncFavorite(
    cloudId: string | undefined,
    clientRecordId: string,
    action: 'add' | 'remove'
  ): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return
    syncService.enqueueFavoriteSync(cloudId, clientRecordId, action)
  },

  /**
   * 同步生词到云端
   * @param entry 生词条目
   */
  async syncVocab(entry: VocabEntry): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return
    syncService.enqueueVocabSync(entry, 'add')
  },

  /**
   * 更新生词的掌握状态
   * @param vocabId 生词 ID
   * @param entry 生词条目
   * @param patch 更新的字段
   */
  async updateVocab(
    vocabId: string,
    entry: VocabEntry,
    patch: {
      mastery_status?: 'new' | 'learning' | 'review' | 'mastered' | 'archived'
      short_meaning?: string
    }
  ): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return
    syncService.enqueueVocabSync(entry, 'update', vocabId, patch)
  },

  /**
   * 删除生词
   * @param vocabId 生词 ID
   * @param entry 生词条目
   */
  async deleteVocab(vocabId: string, entry: VocabEntry): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return
    syncService.enqueueVocabSync(entry, 'delete', vocabId)
  },

  /**
   * 同步所有收藏到云端
   * 用于应用启动时的全量同步
   * @param localFavorites 本地收藏列表
   */
  async syncAllFavorites(localFavorites: FavoriteRecord[]): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return

    const records = localFavorites
      .map((favorite) => getRecord(favorite.recordId))
      .filter((record): record is AnalysisRecord => !!record)

    for (const record of records) {
      if (record.isFavorited) {
        syncService.enqueueFavoriteSync(record.cloudId, record.recordId, 'add')
      }
    }
  },

  /**
   * 同步所有生词到云端
   * 用于应用启动时的全量同步
   * @param localVocab 本地生词列表
   */
  async syncAllVocab(localVocab: VocabEntry[]): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return

    for (const entry of localVocab) {
      syncService.enqueueVocabSync(entry, 'add')
    }
  },

  /**
   * 获取队列统计信息
   * @returns 队列统计信息
   */
  getQueueStats(): {
    pendingCount: number
    inProgressCount: number
    failedCount: number
    totalCount: number
  } {
    return syncService.getQueueStats()
  },

  /**
   * 手动触发同步
   * 用于应用从后台恢复等场景
   */
  triggerSync(): void {
    syncService.triggerSync()
  },

  /**
   * 压缩队列
   * 合并同一实体的多次操作
   */
  compressQueue(): void {
    syncService.compressQueue()
  },

  /**
   * 检查当前是否在线
   * @returns 是否在线
   */
  isOnline(): boolean {
    return syncService.isOnline()
  },

  /**
   * 获取消费者状态
   * @returns 消费者状态：idle | running | paused | stopped
   */
  getConsumerStatus(): string {
    return syncService.getConsumerStatus()
  }
}

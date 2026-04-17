/**
 * CloudSyncService
 *
 * 离线优先的云端同步服务。
 *
 * 特性：
 * 1. 所有同步操作在网络失败时会被可靠地缓存到本地
 * 2. 网络恢复时自动在后台同步积压的操作
 * 3. 对同一实体的多次反向操作进行智能合并，只发送最终有效状态
 * 4. 保证队列消费的顺序性，防止并发重复提交
 *
 * 未登录时静默跳过。
 */

import { useAuthStore } from '../stores/auth'
import type { AnalysisRecord } from '../types/view/analysis-record.vm'
import type { FavoriteRecord } from '../types/view/favorites.vm'
import type { VocabEntry } from '../types/view/vocabulary.vm'
import { getRecord } from './storage'
import { syncService } from './sync'

/**
 * CloudSyncService
 *
 * 保持原有 API 接口不变，内部使用新的同步队列系统
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
   * 同步分析记录到云端（upsert）
   * - 未登录：静默跳过
   * - 已在云端存在：更新
   * - 网络失败：入队等待重试
   */
  async syncRecord(record: AnalysisRecord): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return

    syncService.enqueueRecordSync(record)
  },

  /**
   * 同步收藏状态到云端
   * @param cloudId 云端 UUID
   * @param clientRecordId 本地记录 ID
   * @param action 'add' | 'remove'
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
   * 同步生词本条目到云端
   */
  async syncVocab(entry: VocabEntry): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return

    syncService.enqueueVocabSync(entry, 'add')
  },

  /**
   * 更新生词状态（如标记为已掌握）
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
   */
  async deleteVocab(vocabId: string, entry: VocabEntry): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return

    syncService.enqueueVocabSync(entry, 'delete', vocabId)
  },

  /**
   * 同步所有本地收藏到云端（登录后全量同步）
   * 注意：这要求本地记录必须带有 cloudId
   *
   * 这个方法主要用于用户刚登录时，将本地已有数据与云端同步
   * 在离线优先架构中，通常情况下应该使用 syncFavorite 方法
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
   * 同步所有本地生词本到云端（登录后全量同步）
   *
   * 这个方法主要用于用户刚登录时，将本地已有数据与云端同步
   * 在离线优先架构中，通常情况下应该使用 syncVocab 方法
   */
  async syncAllVocab(localVocab: VocabEntry[]): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return

    for (const entry of localVocab) {
      syncService.enqueueVocabSync(entry, 'add')
    }
  },

  /**
   * 获取队列统计信息
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
   */
  triggerSync(): void {
    syncService.triggerSync()
  },

  /**
   * 压缩队列（合并同一实体的冗余操作）
   */
  compressQueue(): void {
    syncService.compressQueue()
  },

  /**
   * 检查网络状态
   */
  isOnline(): boolean {
    return syncService.isOnline()
  },

  /**
   * 获取消费者状态
   */
  getConsumerStatus(): string {
    return syncService.getConsumerStatus()
  },
}

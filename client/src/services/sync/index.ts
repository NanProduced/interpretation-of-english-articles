/**
 * 统一同步服务
 *
 * 整合队列、合并器、网络监听和消费者
 * 提供离线优先的云端同步能力
 */

import type {
  SyncQueueItem,
  SyncOperationType,
  SyncEntityKey,
  RecordUpsertOperationData,
  FavoriteOperationData,
  VocabOperationData,
  SyncQueueStats,
} from '../../types/sync-queue.vm'
import {
  generateOperationId,
  DEFAULT_SYNC_CONFIG,
} from '../../types/sync-queue.vm'
import {
  getSyncQueue,
  saveSyncQueue,
  getPendingSyncQueue,
  getSyncMetadata,
  saveSyncMetadata,
  addToSyncQueue,
  removeFromSyncQueue,
} from '../storage'
import { operationMerger } from './operation-merger.service'
import { networkMonitor, initializeNetworkMonitor } from './network-monitor.service'
import { queueConsumer, initializeQueueConsumer } from './queue-consumer.service'
import {
  saveRecordToCloud,
  addFavoriteToCloud,
  removeFavoriteFromCloud,
  addVocabToCloud,
  updateCloudVocabulary,
  deleteCloudVocabulary,
  fetchCloudRecordByClientId,
} from '../api'
import { useAuthStore } from '../../stores/auth'
import type { AnalysisRecord } from '../../types/view/analysis-record.vm'
import type { VocabEntry } from '../../types/view/vocabulary.vm'

/**
 * 同步服务类
 */
class SyncService {
  private isInitialized: boolean = false
  private isShuttingDown: boolean = false

  /**
   * 初始化同步服务
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) return

    await initializeNetworkMonitor()

    initializeQueueConsumer(this.executeOperation.bind(this))

    const metadata = getSyncMetadata()
    if (metadata.isProcessing && metadata.currentProcessingId) {
      console.warn(
        '[sync-service] 检测到上次未完成的同步操作，operationId:',
        metadata.currentProcessingId
      )
      this.recoverFromCrash(metadata.currentProcessingId)
    }

    if (networkMonitor.isOnline()) {
      queueConsumer.triggerProcess()
    }

    this.isInitialized = true

    console.log('[sync-service] 同步服务已初始化')
  }

  /**
   * 从崩溃中恢复
   */
  private recoverFromCrash(operationId: string): void {
    const queue = getSyncQueue()
    const item = queue.find((i) => i.operationId === operationId)

    if (item) {
      if (item.failureCount >= DEFAULT_SYNC_CONFIG.maxRetries - 1) {
        console.warn('[sync-service] 操作重试次数过多，标记为失败:', operationId)
      } else {
        console.log('[sync-service] 恢复操作，将重新尝试:', operationId)
      }
    }

    saveSyncMetadata({
      isProcessing: false,
      currentProcessingId: undefined,
    })
  }

  /**
   * 执行操作（消费者的执行器）
   */
  private async executeOperation(
    operationType: SyncOperationType,
    data: SyncQueueItem['data']
  ): Promise<unknown> {
    if (!useAuthStore.getState().isLoggedIn) {
      throw new Error('用户未登录')
    }

    switch (operationType) {
      case 'record_upsert':
        return this.executeRecordUpsert(data as RecordUpsertOperationData)

      case 'favorite_add':
        return this.executeFavoriteAdd(data as FavoriteOperationData)

      case 'favorite_remove':
        return this.executeFavoriteRemove(data as FavoriteOperationData)

      case 'vocab_add':
        return this.executeVocabAdd(data as VocabOperationData)

      case 'vocab_update':
        return this.executeVocabUpdate(data as VocabOperationData)

      case 'vocab_delete':
        return this.executeVocabDelete(data as VocabOperationData)

      default:
        throw new Error(`未知的操作类型: ${operationType}`)
    }
  }

  /**
   * 执行记录 upsert
   */
  private async executeRecordUpsert(data: RecordUpsertOperationData): Promise<unknown> {
    return saveRecordToCloud({
      clientRecordId: data.clientRecordId,
      title: data.title,
      sourceText: data.sourceText,
      sourceTextHash: data.sourceTextHash,
      requestPayload: data.requestPayload,
      renderScene: data.renderScene,
      pageState: data.pageState,
      userFacingState: data.userFacingState,
      workflowVersion: data.workflowVersion,
      schemaVersion: data.schemaVersion,
    })
  }

  /**
   * 执行添加收藏
   */
  private async executeFavoriteAdd(data: FavoriteOperationData): Promise<unknown> {
    let cloudId = data.cloudId

    if (!cloudId) {
      const cloudRecord = await fetchCloudRecordByClientId(data.clientRecordId)
      if (cloudRecord?.cloudId) {
        cloudId = cloudRecord.cloudId
      } else {
        throw new Error(`无法找到记录的云端 ID: ${data.clientRecordId}`)
      }
    }

    return addFavoriteToCloud(cloudId, data.clientRecordId)
  }

  /**
   * 执行移除收藏
   */
  private async executeFavoriteRemove(data: FavoriteOperationData): Promise<unknown> {
    let cloudId = data.cloudId

    if (!cloudId) {
      const cloudRecord = await fetchCloudRecordByClientId(data.clientRecordId)
      if (cloudRecord?.cloudId) {
        cloudId = cloudRecord.cloudId
      } else {
        throw new Error(`无法找到记录的云端 ID: ${data.clientRecordId}`)
      }
    }

    return removeFavoriteFromCloud(cloudId)
  }

  /**
   * 执行添加生词
   */
  private async executeVocabAdd(data: VocabOperationData): Promise<unknown> {
    return addVocabToCloud(data.entry)
  }

  /**
   * 执行更新生词
   */
  private async executeVocabUpdate(data: VocabOperationData): Promise<unknown> {
    if (!data.vocabId) {
      throw new Error('缺少生词 ID')
    }

    if (!data.patch) {
      return
    }

    return updateCloudVocabulary(data.vocabId, data.patch)
  }

  /**
   * 执行删除生词
   */
  private async executeVocabDelete(data: VocabOperationData): Promise<unknown> {
    if (!data.vocabId) {
      throw new Error('缺少生词 ID')
    }

    return deleteCloudVocabulary(data.vocabId)
  }

  /**
   * 入队记录同步操作
   */
  enqueueRecordSync(record: AnalysisRecord): void {
    if (!useAuthStore.getState().isLoggedIn) {
      console.log('[sync-service] 用户未登录，跳过记录同步入队')
      return
    }

    if (!record.sourceText) {
      console.warn('[sync-service] 记录缺少 sourceText，跳过入队')
      return
    }

    const entityKey: SyncEntityKey = {
      type: 'record',
      id: record.recordId,
    }

    const operationData: RecordUpsertOperationData = {
      clientRecordId: record.recordId,
      title: record.title ?? null,
      sourceText: record.sourceText,
      sourceTextHash: this.hashString(record.sourceText),
      requestPayload: record.requestPayload,
      renderScene: record.renderScene,
      pageState: record.pageState,
      userFacingState: undefined,
      workflowVersion: undefined,
      schemaVersion: undefined,
    }

    this.enqueueOperation(
      'record_upsert',
      entityKey,
      operationData,
      10
    )
  }

  /**
   * 入队收藏操作
   */
  enqueueFavoriteSync(
    cloudId: string | undefined,
    clientRecordId: string,
    action: 'add' | 'remove'
  ): void {
    if (!useAuthStore.getState().isLoggedIn) {
      console.log('[sync-service] 用户未登录，跳过收藏同步入队')
      return
    }

    const entityKey: SyncEntityKey = {
      type: 'favorite',
      id: clientRecordId,
    }

    const operationData: FavoriteOperationData = {
      cloudId,
      clientRecordId,
    }

    const operationType = action === 'add' ? 'favorite_add' : 'favorite_remove'

    this.enqueueOperation(operationType, entityKey, operationData, 20)
  }

  /**
   * 入队生词本操作
   */
  enqueueVocabSync(
    entry: VocabEntry,
    action: 'add' | 'update' | 'delete',
    vocabId?: string,
    patch?: {
      mastery_status?: 'new' | 'learning' | 'review' | 'mastered' | 'archived'
      short_meaning?: string
    }
  ): void {
    if (!useAuthStore.getState().isLoggedIn) {
      console.log('[sync-service] 用户未登录，跳生词本同步入队')
      return
    }

    const entityKey: SyncEntityKey = {
      type: 'vocab',
      id: entry.recordId,
      subId: (entry.lemma || entry.word).toLowerCase(),
    }

    const operationData: VocabOperationData = {
      vocabId,
      entry,
      patch,
    }

    let operationType: SyncOperationType
    switch (action) {
      case 'add':
        operationType = 'vocab_add'
        break
      case 'update':
        operationType = 'vocab_update'
        break
      case 'delete':
        operationType = 'vocab_delete'
        break
    }

    this.enqueueOperation(operationType, entityKey, operationData, 30)
  }

  /**
   * 通用入队方法
   */
  private enqueueOperation(
    operationType: SyncOperationType,
    entityKey: SyncEntityKey,
    data: SyncQueueItem['data'],
    priority: number = 50
  ): void {
    const newOperation: SyncQueueItem = {
      operationId: generateOperationId(),
      operationType,
      timestamp: Date.now(),
      entityKey,
      data,
      status: 'pending',
      failureCount: 0,
      priority,
    }

    const existingQueue = getSyncQueue()
    const { updatedQueue, mergeResult } = operationMerger.processNewOperation(
      newOperation,
      existingQueue
    )

    if (mergeResult) {
      console.log(
        `[sync-service] 操作合并: ${newOperation.operationId}, 策略: ${mergeResult.strategy}`
      )
    }

    saveSyncQueue(updatedQueue)

    if (networkMonitor.isOnline() && queueConsumer.getStatus() === 'running') {
      queueConsumer.triggerProcess()
    }
  }

  /**
   * 计算字符串哈希
   */
  private hashString(str: string): string {
    let hash = 0
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i)
      hash = (hash << 5) - hash + char
      hash = hash & hash
    }
    return Math.abs(hash).toString(16).padStart(8, '0')
  }

  /**
   * 获取队列统计信息
   */
  getQueueStats(): SyncQueueStats {
    const queue = getSyncQueue()
    let pendingCount = 0
    let inProgressCount = 0
    let failedCount = 0

    for (const item of queue) {
      switch (item.status) {
        case 'pending':
          pendingCount++
          break
        case 'in_progress':
          inProgressCount++
          break
        case 'failed':
          failedCount++
          break
      }
    }

    return {
      pendingCount,
      inProgressCount,
      failedCount,
      totalCount: queue.length,
    }
  }

  /**
   * 手动触发同步
   */
  triggerSync(): void {
    if (networkMonitor.isOnline()) {
      queueConsumer.triggerProcess()
    } else {
      console.log('[sync-service] 网络离线，无法触发同步')
    }
  }

  /**
   * 压缩队列
   */
  compressQueue(): void {
    queueConsumer.compressQueue()
  }

  /**
   * 清理已完成的操作
   */
  clearCompleted(): void {
    const queue = getSyncQueue()
    const filtered = queue.filter((item) => item.status !== 'completed')
    saveSyncQueue(filtered)
  }

  /**
   * 停止同步服务
   */
  shutdown(): void {
    this.isShuttingDown = true
    queueConsumer.stop()
    console.log('[sync-service] 同步服务已停止')
  }

  /**
   * 获取网络状态
   */
  isOnline(): boolean {
    return networkMonitor.isOnline()
  }

  /**
   * 获取消费者状态
   */
  getConsumerStatus(): string {
    return queueConsumer.getStatus()
  }
}

/**
 * 全局单例同步服务
 */
export const syncService = new SyncService()

/**
 * 初始化同步服务
 * 应该在应用启动时调用
 */
export async function initializeSyncService(): Promise<void> {
  await syncService.initialize()
}

/**
 * 导出所有子服务
 */
export { operationMerger } from './operation-merger.service'
export { networkMonitor, initializeNetworkMonitor } from './network-monitor.service'
export { queueConsumer, initializeQueueConsumer } from './queue-consumer.service'

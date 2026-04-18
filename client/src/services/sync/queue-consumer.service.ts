/**
 * 队列消费者服务
 *
 * 负责消费同步队列中的操作
 * 保证顺序执行、并发控制、错误重试
 *
 * 错误处理策略：
 * - 网络错误（连接超时、网络断开等）：重试，设置 retryAt
 * - HTTP 错误（4xx、5xx）：直接标记为 failed，不重试
 * - 超过最大重试次数：标记为 failed
 */

import type {
  SyncQueueItem,
  SyncOperationType,
  SyncConfig,
} from '../../types/sync-queue.vm'
import {
  DEFAULT_SYNC_CONFIG,
  calculateBackoffDelay,
} from '../../types/sync-queue.vm'
import {
  getSyncMetadata,
  saveSyncMetadata,
  getPendingSyncQueue,
  updateSyncQueueItem,
  removeFromSyncQueue,
  getSyncQueue,
  saveSyncQueue,
} from '../storage'
import { networkMonitor } from './network-monitor.service'
import { operationMerger } from './operation-merger.service'
import { useAuthStore } from '../../stores/auth'
import { ApiError } from '../api/client'

/**
 * 操作执行器类型
 */
export type OperationExecutor = (
  operationType: SyncOperationType,
  data: SyncQueueItem['data']
) => Promise<unknown>

/**
 * 消费者状态
 */
export type ConsumerStatus = 'idle' | 'running' | 'paused' | 'stopped'

/**
 * 消费者事件类型
 */
export type ConsumerEventType =
  | 'start'
  | 'stop'
  | 'pause'
  | 'resume'
  | 'operation_start'
  | 'operation_success'
  | 'operation_failed'
  | 'operation_retried'
  | 'queue_empty'
  | 'error'

/**
 * 消费者事件数据
 */
export interface ConsumerEvent {
  type: ConsumerEventType
  timestamp: number
  operationId?: string
  operationType?: SyncOperationType
  error?: string
  retryCount?: number
}

/**
 * 消费者事件回调
 */
export type ConsumerEventListener = (event: ConsumerEvent) => void

/**
 * 队列消费者服务
 */
export class QueueConsumer {
  private status: ConsumerStatus = 'idle'
  private config: SyncConfig
  private executor: OperationExecutor | null = null
  private eventListeners: Map<ConsumerEventType, Set<ConsumerEventListener>> = new Map()
  private isProcessing: boolean = false
  private processingTimeout: NodeJS.Timeout | null = null

  constructor(customConfig?: Partial<SyncConfig>) {
    this.config = { ...DEFAULT_SYNC_CONFIG, ...customConfig }
  }

  /**
   * 设置操作执行器
   */
  setExecutor(executor: OperationExecutor): void {
    this.executor = executor
  }

  /**
   * 注册事件监听器
   */
  on(eventType: ConsumerEventType, listener: ConsumerEventListener): () => void {
    if (!this.eventListeners.has(eventType)) {
      this.eventListeners.set(eventType, new Set())
    }
    const listeners = this.eventListeners.get(eventType)!
    listeners.add(listener)

    return () => {
      listeners.delete(listener)
    }
  }

  /**
   * 触发事件
   */
  private emit(event: ConsumerEvent): void {
    const listeners = this.eventListeners.get(event.type)
    if (!listeners) return

    for (const listener of listeners) {
      try {
        listener(event)
      } catch (e) {
        console.error('[queue-consumer] 事件监听器执行失败', e)
      }
    }
  }

  /**
   * 启动消费者
   */
  start(): void {
    if (this.status === 'running') return

    this.status = 'running'
    this.emit({ type: 'start', timestamp: Date.now() })

    this.setupNetworkRecoveryListener()

    this.processQueue()
  }

  /**
   * 暂停消费者
   */
  pause(): void {
    if (this.status !== 'running') return

    this.status = 'paused'
    this.emit({ type: 'pause', timestamp: Date.now() })
  }

  /**
   * 恢复消费者
   */
  resume(): void {
    if (this.status !== 'paused') return

    this.status = 'running'
    this.emit({ type: 'resume', timestamp: Date.now() })

    this.processQueue()
  }

  /**
   * 停止消费者
   */
  stop(): void {
    this.status = 'stopped'

    if (this.processingTimeout) {
      clearTimeout(this.processingTimeout)
      this.processingTimeout = null
    }

    this.emit({ type: 'stop', timestamp: Date.now() })
  }

  /**
   * 设置网络恢复监听
   */
  private setupNetworkRecoveryListener(): void {
    const handleNetworkRecovered = () => {
      if (this.status === 'running' || this.status === 'paused') {
        this.resume()
      }
    }

    window.addEventListener('network-recovered', handleNetworkRecovered)
  }

  /**
   * 处理队列
   */
  private async processQueue(): Promise<void> {
    if (this.status !== 'running') return
    if (this.isProcessing) return

    if (!useAuthStore.getState().isLoggedIn) {
      console.log('[queue-consumer] 用户未登录，暂停同步')
      this.scheduleNextProcess()
      return
    }

    if (!networkMonitor.isOnline()) {
      console.log('[queue-consumer] 网络离线，等待恢复')
      this.pause()
      return
    }

    this.isProcessing = true
    saveSyncMetadata({ isProcessing: true })

    try {
      const pendingItems = getPendingSyncQueue()

      if (pendingItems.length === 0) {
        this.emit({ type: 'queue_empty', timestamp: Date.now() })
        this.isProcessing = false
        saveSyncMetadata({ isProcessing: false })
        this.scheduleNextProcess()
        return
      }

      const batchSize = Math.min(this.config.batchSize, pendingItems.length)
      const batch = pendingItems.slice(0, batchSize)

      for (const item of batch) {
        if (this.status !== 'running') break

        const success = await this.processSingleItem(item)

        if (!success && this.isNetworkError()) {
          console.log('[queue-consumer] 检测到网络错误，暂停队列处理')
          this.pause()
          break
        }
      }
    } catch (error) {
      console.error('[queue-consumer] 队列处理失败', error)
      this.emit({
        type: 'error',
        timestamp: Date.now(),
        error: error instanceof Error ? error.message : String(error),
      })
    } finally {
      this.isProcessing = false
      saveSyncMetadata({ isProcessing: false })
    }

    if (this.status === 'running') {
      this.scheduleNextProcess()
    }
  }

  /**
   * 处理单个队列项
   */
  private async processSingleItem(item: SyncQueueItem): Promise<boolean> {
    if (!this.executor) {
      console.error('[queue-consumer] 未设置操作执行器')
      return false
    }

    this.emit({
      type: 'operation_start',
      timestamp: Date.now(),
      operationId: item.operationId,
      operationType: item.operationType,
    })

    updateSyncQueueItem(item.operationId, {
      status: 'in_progress',
    })
    saveSyncMetadata({ currentProcessingId: item.operationId })

    try {
      await this.executor(item.operationType, item.data)

      removeFromSyncQueue(item.operationId)

      this.emit({
        type: 'operation_success',
        timestamp: Date.now(),
        operationId: item.operationId,
        operationType: item.operationType,
      })

      saveSyncMetadata({
        lastSyncedAt: Date.now(),
        currentProcessingId: undefined,
      })

      return true
    } catch (error) {
      console.error(`[queue-consumer] 操作执行失败 ${item.operationId}`, error)

      const errorMessage = error instanceof Error ? error.message : String(error)
      const newFailureCount = item.failureCount + 1

      const isNetworkError = this.isNetworkError() || this.isRetriableError(error)

      if (isNetworkError && newFailureCount < this.config.maxRetries) {
        const backoffDelay = calculateBackoffDelay(newFailureCount, this.config)
        const retryAt = Date.now() + backoffDelay

        updateSyncQueueItem(item.operationId, {
          status: 'pending',
          failureCount: newFailureCount,
          lastError: errorMessage,
          retryAt,
        })

        this.emit({
          type: 'operation_retried',
          timestamp: Date.now(),
          operationId: item.operationId,
          operationType: item.operationType,
          error: errorMessage,
          retryCount: newFailureCount,
        })
      } else {
        updateSyncQueueItem(item.operationId, {
          status: 'failed',
          failureCount: newFailureCount,
          lastError: errorMessage,
        })

        this.emit({
          type: 'operation_failed',
          timestamp: Date.now(),
          operationId: item.operationId,
          operationType: item.operationType,
          error: errorMessage,
        })
      }

      saveSyncMetadata({ currentProcessingId: undefined })

      return false
    }
  }

  /**
   * 检查是否为网络错误
   */
  private isNetworkError(): boolean {
    return !networkMonitor.isOnline()
  }

  /**
   * 检查是否为可重试的错误
   * 只有网络错误（NETWORK_ERROR、TIMEOUT）才应该重试
   * HTTP 错误（4xx、5xx）不应该重试
   */
  private isRetriableError(error: unknown): boolean {
    if (error instanceof ApiError) {
      return error.code === 'NETWORK_ERROR' || error.code === 'TIMEOUT'
    }
    return false
  }

  /**
   * 安排下一次处理
   */
  private scheduleNextProcess(): void {
    if (this.processingTimeout) {
      clearTimeout(this.processingTimeout)
    }

    const pendingItems = getPendingSyncQueue()

    if (pendingItems.length === 0) {
      this.processingTimeout = setTimeout(() => {
        this.processQueue()
      }, 5000)
      return
    }

    const now = Date.now()
    const nextRetry = pendingItems
      .filter((item) => item.retryAt && item.retryAt > now)
      .sort((a, b) => (a.retryAt || 0) - (b.retryAt || 0))[0]

    const delay = nextRetry?.retryAt ? Math.max(0, nextRetry.retryAt - now) : 1000

    this.processingTimeout = setTimeout(() => {
      this.processQueue()
    }, Math.min(delay, 30000))
  }

  /**
   * 手动触发队列处理
   */
  triggerProcess(): void {
    if (this.status === 'running') {
      this.processQueue()
    }
  }

  /**
   * 获取当前状态
   */
  getStatus(): ConsumerStatus {
    return this.status
  }

  /**
   * 压缩队列
   * 在处理前对队列进行优化，合并同一实体的操作
   */
  compressQueue(): void {
    const queue = getSyncQueue()
    const compressed = operationMerger.compressQueue(queue)
    saveSyncQueue(compressed)
  }
}

/**
 * 全局单例队列消费者
 */
export const queueConsumer = new QueueConsumer()

/**
 * 初始化队列消费者
 * 应该在应用启动时调用
 */
export function initializeQueueConsumer(executor: OperationExecutor): void {
  queueConsumer.setExecutor(executor)
  queueConsumer.start()
}

/**
 * 检查是否有正在处理的操作
 */
export function hasActiveProcessing(): boolean {
  const metadata = getSyncMetadata()
  return metadata.isProcessing
}

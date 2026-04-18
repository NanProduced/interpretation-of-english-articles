/**
 * 同步队列 VM
 *
 * 定义同步队列的数据结构和类型
 * 支持离线优先架构，网络失败时缓存操作，网络恢复时自动同步
 */

import type { AnalysisRecord } from './view/analysis-record.vm'
import type { VocabEntry } from './view/vocabulary.vm'
import type { AnalyzeRequest } from '../services/api'
import type { RenderSceneVm, ResultPageState } from './view/render-scene.vm'

/**
 * 同步操作类型
 */
export type SyncOperationType =
  | 'record_upsert'
  | 'favorite_add'
  | 'favorite_remove'
  | 'vocab_add'
  | 'vocab_update'
  | 'vocab_delete'

/**
 * 同步操作状态
 */
export type SyncOperationStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'cancelled'

/**
 * 同步实体类型
 */
export type SyncEntityType = 'record' | 'favorite' | 'vocab'

/**
 * 实体唯一标识
 */
export interface SyncEntityKey {
  type: SyncEntityType
  id: string
  subId?: string
}

/**
 * 记录更新/插入操作数据
 * 对应 AnalysisRecord 中的关键字段
 */
export interface RecordUpsertOperationData {
  clientRecordId: string
  title?: string | null
  sourceText: string
  sourceTextHash: string
  requestPayload: {
    reading_goal: AnalyzeRequest['reading_goal']
    reading_variant: AnalyzeRequest['reading_variant']
    source_type: 'user_input'
  }
  renderScene: RenderSceneVm | null
  pageState: ResultPageState
  userFacingState?: string | null
  workflowVersion?: string | null
  schemaVersion?: string | null
}

/**
 * 收藏操作数据
 */
export interface FavoriteOperationData {
  cloudId?: string
  clientRecordId: string
}

/**
 * 生词本操作数据
 */
export interface VocabOperationData {
  vocabId?: string
  entry: VocabEntry
  patch?: {
    mastery_status?: string
    short_meaning?: string
  }
}

/**
 * 同步操作数据的联合类型
 */
export type SyncOperationData =
  | RecordUpsertOperationData
  | FavoriteOperationData
  | VocabOperationData

/**
 * 同步队列项
 * 表示待同步的单个操作
 */
export interface SyncQueueItem {
  operationId: string
  operationType: SyncOperationType
  timestamp: number
  entityKey: SyncEntityKey
  data: SyncOperationData
  status: SyncOperationStatus
  failureCount: number
  lastError?: string
  retryAt?: number
  priority: number
}

/**
 * 同步队列统计信息
 */
export interface SyncQueueStats {
  pendingCount: number
  inProgressCount: number
  failedCount: number
  totalCount: number
}

/**
 * 网络状态
 */
export type NetworkStatus = 'online' | 'offline' | 'unknown'

/**
 * 同步配置
 */
export interface SyncConfig {
  maxRetries: number
  initialRetryDelay: number
  maxRetryDelay: number
  backoffFactor: number
  batchSize: number
  syncTimeout: number
}

/**
 * 默认同步配置
 */
export const DEFAULT_SYNC_CONFIG: SyncConfig = {
  maxRetries: 5,
  initialRetryDelay: 1000,
  maxRetryDelay: 60000,
  backoffFactor: 2,
  batchSize: 10,
  syncTimeout: 30000
}

/**
 * 操作合并规则
 */
export interface OperationMergeRule {
  sourceType: SyncOperationType
  targetType: SyncOperationType
  resultType: SyncOperationType | null
  strategy: 'replace' | 'merge' | 'cancel' | 'keep_both'
}

/**
 * 默认操作合并规则
 * 定义同一实体的多次操作如何合并
 */
export const DEFAULT_MERGE_RULES: OperationMergeRule[] = [
  {
    sourceType: 'record_upsert',
    targetType: 'record_upsert',
    resultType: 'record_upsert',
    strategy: 'replace'
  },
  {
    sourceType: 'favorite_add',
    targetType: 'favorite_remove',
    resultType: null,
    strategy: 'cancel'
  },
  {
    sourceType: 'favorite_remove',
    targetType: 'favorite_add',
    resultType: 'favorite_add',
    strategy: 'replace'
  },
  {
    sourceType: 'favorite_add',
    targetType: 'favorite_add',
    resultType: 'favorite_add',
    strategy: 'keep_both'
  },
  {
    sourceType: 'favorite_remove',
    targetType: 'favorite_remove',
    resultType: 'favorite_remove',
    strategy: 'keep_both'
  },
  {
    sourceType: 'vocab_add',
    targetType: 'vocab_delete',
    resultType: null,
    strategy: 'cancel'
  },
  {
    sourceType: 'vocab_delete',
    targetType: 'vocab_add',
    resultType: 'vocab_add',
    strategy: 'replace'
  },
  {
    sourceType: 'vocab_update',
    targetType: 'vocab_update',
    resultType: 'vocab_update',
    strategy: 'merge'
  },
  {
    sourceType: 'vocab_add',
    targetType: 'vocab_update',
    resultType: 'vocab_add',
    strategy: 'merge'
  }
]

/**
 * 生成唯一操作 ID
 * 格式：op_{timestamp}_{random}
 */
export function generateOperationId(): string {
  return `op_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`
}

/**
 * 计算指数退避延迟
 * @param failureCount 失败次数
 * @param config 同步配置
 * @returns 延迟时间（毫秒）
 */
export function calculateBackoffDelay(
  failureCount: number,
  config: SyncConfig = DEFAULT_SYNC_CONFIG
): number {
  const delay = config.initialRetryDelay * Math.pow(config.backoffFactor, failureCount - 1)
  return Math.min(delay, config.maxRetryDelay)
}

/**
 * 判断两个实体是否相同
 */
export function isSameEntity(a: SyncEntityKey, b: SyncEntityKey): boolean {
  if (a.type !== b.type) return false
  if (a.id !== b.id) return false
  if (a.subId !== b.subId) return false
  return true
}

/**
 * 将实体键转换为字符串表示
 * 格式：{type}:{id} 或 {type}:{id}:{subId}
 */
export function entityKeyToString(key: SyncEntityKey): string {
  if (key.subId) {
    return `${key.type}:${key.id}:${key.subId}`
  }
  return `${key.type}:${key.id}`
}

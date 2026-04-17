/**
 * 同步队列类型定义
 *
 * 用于实现离线优先的云端同步架构
 * 支持操作持久化、网络恢复自动同步、智能操作合并
 */

import type { AnalysisRecord } from './view/analysis-record.vm'
import type { VocabEntry } from './view/vocabulary.vm'

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
 * 同步操作实体类型
 * 用于标识同一实体的操作，支持智能合并
 */
export type SyncEntityType = 'record' | 'favorite' | 'vocab'

/**
 * 同步操作实体标识
 * 用于唯一标识一个实体，支持操作合并
 */
export interface SyncEntityKey {
  /** 实体类型 */
  type: SyncEntityType
  /** 实体唯一标识 */
  id: string
  /** 可选的子标识（用于复合实体，如同一记录下的不同单词） */
  subId?: string
}

/**
 * 记录同步操作数据
 */
export interface RecordUpsertOperationData {
  clientRecordId: string
  title?: string | null
  sourceText: string
  sourceTextHash: string
  requestPayload: {
    reading_goal: AnalysisRecord['requestPayload']['reading_goal']
    reading_variant: AnalysisRecord['requestPayload']['reading_variant']
    source_type: 'user_input'
  }
  renderScene: AnalysisRecord['renderScene']
  pageState: string
  userFacingState?: string | null
  workflowVersion?: string | null
  schemaVersion?: string | null
}

/**
 * 收藏同步操作数据
 */
export interface FavoriteOperationData {
  cloudId?: string
  clientRecordId: string
}

/**
 * 生词本同步操作数据
 */
export interface VocabOperationData {
  vocabId?: string
  entry: VocabEntry
  patch?: {
    mastery_status?: 'new' | 'learning' | 'review' | 'mastered' | 'archived'
    short_meaning?: string
  }
}

/**
 * 同步操作数据联合类型
 */
export type SyncOperationData =
  | RecordUpsertOperationData
  | FavoriteOperationData
  | VocabOperationData

/**
 * 同步队列项
 * 每个项代表一个待同步的操作
 */
export interface SyncQueueItem {
  /** 全局唯一操作 ID */
  operationId: string
  /** 操作类型 */
  operationType: SyncOperationType
  /** 操作时间戳 */
  timestamp: number
  /** 实体标识（用于操作合并） */
  entityKey: SyncEntityKey
  /** 操作数据 */
  data: SyncOperationData
  /** 操作状态 */
  status: SyncOperationStatus
  /** 失败次数（用于重试策略） */
  failureCount: number
  /** 最后一次失败的错误信息 */
  lastError?: string
  /** 下次重试时间戳（用于退避策略） */
  retryAt?: number
  /** 操作优先级（数字越小优先级越高） */
  priority: number
}

/**
 * 同步队列统计信息
 */
export interface SyncQueueStats {
  /** 待处理操作数 */
  pendingCount: number
  /** 处理中操作数 */
  inProgressCount: number
  /** 失败操作数 */
  failedCount: number
  /** 总操作数 */
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
  /** 最大重试次数 */
  maxRetries: number
  /** 初始重试延迟（ms） */
  initialRetryDelay: number
  /** 最大重试延迟（ms） */
  maxRetryDelay: number
  /** 退避因子 */
  backoffFactor: number
  /** 批处理大小 */
  batchSize: number
  /** 同步超时时间（ms） */
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
  syncTimeout: 30000,
}

/**
 * 操作合并规则
 * 定义哪些操作可以合并，以及如何合并
 */
export interface OperationMergeRule {
  /** 源操作类型 */
  sourceType: SyncOperationType
  /** 目标操作类型 */
  targetType: SyncOperationType
  /** 合并结果类型（null 表示相互抵消） */
  resultType: SyncOperationType | null
  /** 合并策略 */
  strategy: 'replace' | 'merge' | 'cancel' | 'keep_both'
}

/**
 * 默认操作合并规则
 */
export const DEFAULT_MERGE_RULES: OperationMergeRule[] = [
  {
    sourceType: 'record_upsert',
    targetType: 'record_upsert',
    resultType: 'record_upsert',
    strategy: 'replace',
  },
  {
    sourceType: 'favorite_add',
    targetType: 'favorite_remove',
    resultType: null,
    strategy: 'cancel',
  },
  {
    sourceType: 'favorite_remove',
    targetType: 'favorite_add',
    resultType: 'favorite_add',
    strategy: 'replace',
  },
  {
    sourceType: 'favorite_add',
    targetType: 'favorite_add',
    resultType: 'favorite_add',
    strategy: 'keep_both',
  },
  {
    sourceType: 'favorite_remove',
    targetType: 'favorite_remove',
    resultType: 'favorite_remove',
    strategy: 'keep_both',
  },
  {
    sourceType: 'vocab_add',
    targetType: 'vocab_delete',
    resultType: null,
    strategy: 'cancel',
  },
  {
    sourceType: 'vocab_delete',
    targetType: 'vocab_add',
    resultType: 'vocab_add',
    strategy: 'replace',
  },
  {
    sourceType: 'vocab_update',
    targetType: 'vocab_update',
    resultType: 'vocab_update',
    strategy: 'merge',
  },
  {
    sourceType: 'vocab_add',
    targetType: 'vocab_update',
    resultType: 'vocab_add',
    strategy: 'merge',
  },
]

/**
 * 生成操作唯一 ID
 */
export function generateOperationId(): string {
  return `op_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`
}

/**
 * 计算退避延迟
 * 使用指数退避策略
 */
export function calculateBackoffDelay(
  failureCount: number,
  config: SyncConfig = DEFAULT_SYNC_CONFIG
): number {
  const delay = config.initialRetryDelay * Math.pow(config.backoffFactor, failureCount - 1)
  return Math.min(delay, config.maxRetryDelay)
}

/**
 * 检查两个实体键是否指向同一实体
 */
export function isSameEntity(a: SyncEntityKey, b: SyncEntityKey): boolean {
  if (a.type !== b.type) return false
  if (a.id !== b.id) return false
  if (a.subId !== b.subId) return false
  return true
}

/**
 * 生成实体键的字符串表示
 */
export function entityKeyToString(key: SyncEntityKey): string {
  if (key.subId) {
    return `${key.type}:${key.id}:${key.subId}`
  }
  return `${key.type}:${key.id}`
}

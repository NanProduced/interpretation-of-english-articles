export type SyncOperationType =
  | 'record_upsert'
  | 'favorite_add'
  | 'favorite_remove'
  | 'vocab_add'
  | 'vocab_update'
  | 'vocab_delete'

export type SyncOperationStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'cancelled'

export type SyncEntityType = 'record' | 'favorite' | 'vocab'

export interface SyncEntityKey {
  type: SyncEntityType
  id: string
  subId?: string
}

export interface RecordUpsertOperationData {
  clientRecordId: string
  title?: string | null
  sourceText: string
  sourceTextHash: string
  requestPayload: any
  renderScene: any
  pageState: string
  userFacingState?: string | null
  workflowVersion?: string | null
  schemaVersion?: string | null
}

export interface FavoriteOperationData {
  cloudId?: string
  clientRecordId: string
}

export interface VocabOperationData {
  vocabId?: string
  entry: any
  patch?: {
    mastery_status?: string
    short_meaning?: string
  }
}

export type SyncOperationData =
  | RecordUpsertOperationData
  | FavoriteOperationData
  | VocabOperationData

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

export interface SyncQueueStats {
  pendingCount: number
  inProgressCount: number
  failedCount: number
  totalCount: number
}

export type NetworkStatus = 'online' | 'offline' | 'unknown'

export interface SyncConfig {
  maxRetries: number
  initialRetryDelay: number
  maxRetryDelay: number
  backoffFactor: number
  batchSize: number
  syncTimeout: number
}

export const DEFAULT_SYNC_CONFIG: SyncConfig = {
  maxRetries: 5,
  initialRetryDelay: 1000,
  maxRetryDelay: 60000,
  backoffFactor: 2,
  batchSize: 10,
  syncTimeout: 30000
}

export interface OperationMergeRule {
  sourceType: SyncOperationType
  targetType: SyncOperationType
  resultType: SyncOperationType | null
  strategy: 'replace' | 'merge' | 'cancel' | 'keep_both'
}

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

export function generateOperationId(): string {
  return 'op_' + Date.now() + '_' + Math.random().toString(36).slice(2, 11)
}

export function calculateBackoffDelay(
  failureCount: number,
  config: SyncConfig = DEFAULT_SYNC_CONFIG
): number {
  const delay = config.initialRetryDelay * Math.pow(config.backoffFactor, failureCount - 1)
  return Math.min(delay, config.maxRetryDelay)
}

export function isSameEntity(a: SyncEntityKey, b: SyncEntityKey): boolean {
  if (a.type !== b.type) return false
  if (a.id !== b.id) return false
  if (a.subId !== b.subId) return false
  return true
}

export function entityKeyToString(key: SyncEntityKey): string {
  if (key.subId) {
    return key.type + ':' + key.id + ':' + key.subId
  }
  return key.type + ':' + key.id
}

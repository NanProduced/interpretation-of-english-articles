/**
 * 操作合并服务
 *
 * 智能合并同一实体的多次反向操作
 * 避免发送无意义的冗余请求到云端
 */

import type {
  SyncQueueItem,
  SyncOperationType,
  OperationMergeRule,
  RecordUpsertOperationData,
  FavoriteOperationData,
  VocabOperationData,
} from '../../types/sync-queue.vm'
import { isSameEntity, entityKeyToString } from '../../types/sync-queue.vm'

/**
 * 操作合并结果
 */
export interface MergeResult {
  /** 是否需要合并 */
  shouldMerge: boolean
  /** 合并后的操作类型（null 表示相互抵消） */
  resultType: SyncOperationType | null
  /** 合并策略 */
  strategy: OperationMergeRule['strategy']
  /** 合并后的数据（如果需要合并） */
  mergedData?: RecordUpsertOperationData | FavoriteOperationData | VocabOperationData
  /** 需要移除的操作 ID 列表 */
  operationIdsToRemove: string[]
}

/**
 * 操作合并服务
 */
export class OperationMerger {
  private rules: OperationMergeRule[]

  constructor(customRules?: OperationMergeRule[]) {
    this.rules = customRules || this.getDefaultRules()
  }

  /**
   * 获取默认合并规则
   */
  private getDefaultRules(): OperationMergeRule[] {
    return [
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
  }

  /**
   * 查找合并规则
   */
  private findMergeRule(
    sourceType: SyncOperationType,
    targetType: SyncOperationType
  ): OperationMergeRule | null {
    return this.rules.find(
      (rule) => rule.sourceType === sourceType && rule.targetType === targetType
    ) || null
  }

  /**
   * 检查两个操作是否可以合并
   */
  canMerge(source: SyncQueueItem, target: SyncQueueItem): boolean {
    if (!isSameEntity(source.entityKey, target.entityKey)) {
      return false
    }

    const rule = this.findMergeRule(source.operationType, target.operationType)
    return rule !== null
  }

  /**
   * 合并两个操作
   * 注意：source 是新操作，target 是队列中已存在的操作
   */
  merge(source: SyncQueueItem, target: SyncQueueItem): MergeResult {
    if (!isSameEntity(source.entityKey, target.entityKey)) {
      return {
        shouldMerge: false,
        resultType: null,
        strategy: 'keep_both',
        operationIdsToRemove: [],
      }
    }

    const rule = this.findMergeRule(source.operationType, target.operationType)

    if (!rule) {
      return {
        shouldMerge: false,
        resultType: null,
        strategy: 'keep_both',
        operationIdsToRemove: [],
      }
    }

    switch (rule.strategy) {
      case 'cancel':
        return {
          shouldMerge: true,
          resultType: null,
          strategy: 'cancel',
          operationIdsToRemove: [source.operationId, target.operationId],
        }

      case 'replace':
        return {
          shouldMerge: true,
          resultType: rule.resultType,
          strategy: 'replace',
          mergedData: source.data,
          operationIdsToRemove: [target.operationId],
        }

      case 'merge':
        return {
          shouldMerge: true,
          resultType: rule.resultType,
          strategy: 'merge',
          mergedData: this.mergeData(source.data, target.data, source.operationType),
          operationIdsToRemove: [target.operationId],
        }

      case 'keep_both':
      default:
        return {
          shouldMerge: false,
          resultType: null,
          strategy: 'keep_both',
          operationIdsToRemove: [],
        }
    }
  }

  /**
   * 合并操作数据
   */
  private mergeData(
    sourceData: SyncQueueItem['data'],
    targetData: SyncQueueItem['data'],
    operationType: SyncOperationType
  ): SyncQueueItem['data'] {
    switch (operationType) {
      case 'record_upsert':
        return this.mergeRecordData(
          sourceData as RecordUpsertOperationData,
          targetData as RecordUpsertOperationData
        )

      case 'vocab_update':
        return this.mergeVocabUpdateData(
          sourceData as VocabOperationData,
          targetData as VocabOperationData
        )

      case 'vocab_add':
        return this.mergeVocabAddData(
          sourceData as VocabOperationData,
          targetData as VocabOperationData
        )

      default:
        return sourceData
    }
  }

  /**
   * 合并记录数据
   * 新数据覆盖旧数据
   */
  private mergeRecordData(
    source: RecordUpsertOperationData,
    target: RecordUpsertOperationData
  ): RecordUpsertOperationData {
    return {
      ...target,
      ...source,
      title: source.title ?? target.title,
      userFacingState: source.userFacingState ?? target.userFacingState,
      workflowVersion: source.workflowVersion ?? target.workflowVersion,
      schemaVersion: source.schemaVersion ?? target.schemaVersion,
    }
  }

  /**
   * 合并生词本更新数据
   */
  private mergeVocabUpdateData(
    source: VocabOperationData,
    target: VocabOperationData
  ): VocabOperationData {
    return {
      ...target,
      ...source,
      patch: {
        ...target.patch,
        ...source.patch,
      },
    }
  }

  /**
   * 合并生词本添加数据
   * 如果有更新操作，合并到添加数据中
   */
  private mergeVocabAddData(
    source: VocabOperationData,
    target: VocabOperationData
  ): VocabOperationData {
    const result: VocabOperationData = {
      ...target,
      ...source,
      entry: {
        ...target.entry,
        ...source.entry,
      },
    }

    if (source.patch || target.patch) {
      result.patch = {
        ...target.patch,
        ...source.patch,
      }
    }

    return result
  }

  /**
   * 处理新操作入队时的合并逻辑
   * 遍历队列中同一实体的所有操作，决定如何合并
   */
  processNewOperation(
    newOperation: SyncQueueItem,
    existingQueue: SyncQueueItem[]
  ): {
    updatedQueue: SyncQueueItem[]
    mergeResult: MergeResult | null
  } {
    const sameEntityOperations = existingQueue.filter((item) =>
      isSameEntity(item.entityKey, newOperation.entityKey)
    )

    if (sameEntityOperations.length === 0) {
      return {
        updatedQueue: [...existingQueue, newOperation],
        mergeResult: null,
      }
    }

    const sameEntityPending = sameEntityOperations.filter(
      (item) => item.status === 'pending' || item.status === 'failed'
    )

    if (sameEntityPending.length === 0) {
      return {
        updatedQueue: [...existingQueue, newOperation],
        mergeResult: null,
      }
    }

    let resultQueue = [...existingQueue]
    let currentOperation = newOperation
    let finalMergeResult: MergeResult | null = null

    for (const existingOp of sameEntityPending.reverse()) {
      const mergeResult = this.merge(currentOperation, existingOp)

      if (mergeResult.shouldMerge) {
        finalMergeResult = mergeResult

        resultQueue = resultQueue.filter(
          (item) => !mergeResult.operationIdsToRemove.includes(item.operationId)
        )

        if (mergeResult.resultType !== null && mergeResult.mergedData) {
          currentOperation = {
            ...currentOperation,
            operationType: mergeResult.resultType,
            data: mergeResult.mergedData,
          }
        } else {
          return {
            updatedQueue: resultQueue,
            mergeResult: finalMergeResult,
          }
        }
      }
    }

    if (finalMergeResult?.resultType !== null) {
      resultQueue = [...resultQueue, currentOperation]
    }

    return {
      updatedQueue: resultQueue,
      mergeResult: finalMergeResult,
    }
  }

  /**
   * 按实体分组操作
   */
  groupByEntity(operations: SyncQueueItem[]): Map<string, SyncQueueItem[]> {
    const groups = new Map<string, SyncQueueItem[]>()

    for (const op of operations) {
      const key = entityKeyToString(op.entityKey)
      const group = groups.get(key) || []
      group.push(op)
      groups.set(key, group)
    }

    return groups
  }

  /**
   * 压缩队列（优化离线期间的大量操作）
   * 对同一实体的操作进行合并，只保留最终有效状态
   */
  compressQueue(operations: SyncQueueItem[]): SyncQueueItem[] {
    const groups = this.groupByEntity(operations)
    const result: SyncQueueItem[] = []

    for (const [, group] of groups) {
      const sorted = [...group].sort((a, b) => a.timestamp - b.timestamp)

      if (sorted.length <= 1) {
        result.push(...sorted)
        continue
      }

      let compressed: SyncQueueItem[] = [sorted[0]]

      for (let i = 1; i < sorted.length; i++) {
        const current = sorted[i]
        const last = compressed[compressed.length - 1]

        const mergeResult = this.merge(current, last)

        if (mergeResult.shouldMerge) {
          if (mergeResult.resultType !== null && mergeResult.mergedData) {
            compressed[compressed.length - 1] = {
              ...last,
              operationType: mergeResult.resultType,
              data: mergeResult.mergedData,
              timestamp: current.timestamp,
            }
          } else {
            compressed.pop()
          }
        } else {
          compressed.push(current)
        }
      }

      result.push(...compressed)
    }

    return result.sort((a, b) => a.timestamp - b.timestamp)
  }
}

/**
 * 全局单例操作合并器
 */
export const operationMerger = new OperationMerger()

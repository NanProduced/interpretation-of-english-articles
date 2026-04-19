/**
 * 生词本 VM
 *
 * 记录从结果页"记入生词本"的词条
 * 记录来源 recordId、词条文本、释义、加入时间、是否已掌握
 */

export interface VocabEntry {
  id: string
  /** 来源分析记录的前端稳定主键 (client_record_id) */
  recordId: string
  /** 来源分析记录的云端 ID (UUID) */
  cloudRecordId?: string
  /** 同步状态 */
  syncState?: 'local_only' | 'syncing' | 'synced' | 'sync_failed'
  /** 待执行操作 */
  pendingOp?: 'create' | 'update' | 'delete' | null
  /** 最近一次同步错误 */
  lastSyncError?: string | null
  /** 软删除标记 */
  tombstone?: boolean
  /** 单词/短语原文 */
  word: string
  /** 词性 */
  partOfSpeech: string
  /** 释义 */
  meaning: string
  /** 加入时间 */
  addedAt: number
  /** 是否已掌握 */
  mastered: boolean
  
  /** 词形还原后的原形 */
  lemma?: string
  /** 音标 */
  phonetic?: string
  
  /** 深度学习数据（从后端 meanings_json 等解析） */
  detailMeanings?: Array<{
    pos: string;
    definitions: string[];
  }>;
  /** 词形变换列表 */
  exchange?: string[];
  /** 标签列表 */
  tags?: string[];
  
  /** 来源句子文本 */
  sentence?: string
  /** 来源上下文文本 */
  context?: string
  /** 词典来源 */
  provider?: string
}

/**
 * 生词本 VM
 *
 * 记录从结果页"记入生词本"的词条
 * 记录来源 recordId、词条文本、释义、加入时间、是否已掌握
 */

export interface VocabEntry {
  id: string
  /** 来源分析记录 ID */
  recordId: string
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
}

/**
 * 生词本 VM
 *
 * 记录从结果页"记入生词本"的词条。
 * 以 lemma 为唯一标识，同 lemma 多次收藏会合并 sourceRefs。
 *
 * 基于艾宾浩斯遗忘曲线的复习系统扩展：
 * - 实现 SM-2 算法（SuperMemo 2）进行科学复习调度
 * - 根据复习质量动态调整下次复习时间
 */

/** 单次收藏来源的语境记录 */
export interface SourceRef {
  /** 来源分析记录的前端稳定主键 */
  clientRecordId: string
  /** 来源分析记录的云端 UUID */
  cloudRecordId?: string
  /** 来源句子文本 */
  sourceSentence?: string
  /** 来源上下文文本 */
  sourceContext?: string
  /** 来源句子 ID（用于跳转定位） */
  sourceSentenceId?: string
  /** 收藏时的锚点文本（如 "adopted"） */
  sourceAnchorText?: string
  /** 在句子中的第几次出现 */
  sourceOccurrence?: number
  /** 收藏时间 ISO 字符串 */
  collectedAt?: string
}

/**
 * 复习质量评分（SM-2 算法的 0-5 分制）
 *
 * - 0: 完全忘记 (Complete Blackout)
 * - 1: 几乎忘记 (Wrong Response)
 * - 2: 模糊记得 (Wrong Response, On The Tip Of The Tongue)
 * - 3: 记住了 (Correct Response, With Serious Difficulty)
 * - 4: 熟练掌握 (Correct Response, With Some Hesitation)
 * - 5: 完全掌握 (Perfect Response)
 */
export type ReviewQuality = 0 | 1 | 2 | 3 | 4 | 5

export interface VocabEntry {
  id: string
  /** 同步状态 */
  syncState?: 'local_only' | 'syncing' | 'synced' | 'sync_failed'
  /** 待执行操作 */
  pendingOp?: 'create' | 'update' | 'delete' | null
  /** 最近一次同步错误 */
  lastSyncError?: string | null
  /** 软删除标记 */
  tombstone?: boolean

  /** 词形还原后的原形（主键） */
  lemma: string
  /** 展示词头（用户实际收藏的形态，如 "adopted"） */
  word: string
  /** 词性 */
  partOfSpeech: string
  /** 简短释义 */
  meaning: string
  /** 加入时间 */
  addedAt: number
  /** 是否已掌握（兼容旧字段，实际由 masteryStatus 决定） */
  mastered: boolean

  /** 词典词条稳定引用 ID（用于按需加载完整词条） */
  dictEntryId?: number
  /** 音标 */
  phonetic?: string
  /** 深度学习数据（从后端 meanings_json 解析） */
  detailMeanings?: Array<{
    pos: string
    definitions: string[]
  }>
  /** 词形变换列表 */
  exchange?: string[]
  /** 标签列表 */
  tags?: string[]
  /** 词典来源 */
  provider?: string

  /** 最近一次来源句子文本（顶层兼容字段，用于列表页快速展示） */
  sentence?: string
  /** 最近一次来源上下文文本 */
  context?: string

  /** 多来源语境数组（详情页使用） */
  sourceRefs?: SourceRef[]
  /** 用户实际收藏过的词形变体列表 */
  collectedForms?: string[]
  /** Free Dictionary API 音频 URL 缓存 */
  audioUrl?: string

  // ---------------------------------------------------------------------------
  // 艾宾浩斯复习系统字段
  // ---------------------------------------------------------------------------

  /**
   * 掌握状态
   * - new: 新词（从未复习过）
   * - learning: 学习中
   * - review: 需要复习
   * - mastered: 已掌握
   * - archived: 已归档
   */
  masteryStatus?: 'new' | 'learning' | 'review' | 'mastered' | 'archived'

  /** 累计复习次数 */
  reviewCount?: number

  /** 最近一次复习时间（时间戳毫秒） */
  lastReviewedAt?: number

  /** 下一次复习时间（时间戳毫秒），基于艾宾浩斯遗忘曲线计算 */
  nextReviewAt?: number

  /**
   * 易度因子 (Ease Factor, EF)
   * SM-2 算法核心参数，默认 2.5，最低 1.3
   * 表示单词的难易程度，值越大表示越容易记住
   */
  easeFactor?: number

  /**
   * 连续成功复习次数
   * 用于计算下一次复习间隔
   * - 0 表示从未成功复习过或刚失败重置
   * - >= 5 且 easeFactor >= 2.5 时标记为 mastered
   */
  repetitions?: number

  /**
   * 当前复习间隔（天）
   * 上一次成功复习后计算出的间隔
   */
  reviewInterval?: number
}

/** saveVocabEntry 的返回结果，用于 toast 反馈 */
export interface SaveVocabResult {
  entry: VocabEntry
  /** 是否发生了 lemma 归并（同 lemma 已存在） */
  merged: boolean
  /** 归并后的语境总数 */
  totalSourceCount: number
}

/** highlights API 单个匹配结果 */
export interface VocabHighlightMatch {
  vocabId: string
  lemma: string
  sentenceId: string
  anchorText: string
  occurrence: number
  masteryStatus: string
}

// ---------------------------------------------------------------------------
// 艾宾浩斯复习系统相关类型
// ---------------------------------------------------------------------------

/** 复习统计数据 */
export interface ReviewStats {
  /** 生词总数 */
  totalVocab: number
  /** 今日待复习数量 */
  dueToday: number
  /** 逾期未复习数量 */
  overdue: number
  /** 新词数量（从未复习过） */
  newWords: number
  /** 学习中数量 */
  learning: number
  /** 已掌握数量 */
  mastered: number
}

/** 待复习单词列表项 */
export interface DueVocabItem {
  id: string
  lemma: string
  displayWord: string
  phonetic?: string
  partOfSpeech?: string
  shortMeaning: string
  masteryStatus: 'new' | 'learning' | 'review' | 'mastered' | 'archived'
  repetitions: number
  easeFactor: number
  reviewInterval: number
  nextReviewAt?: number
  sourceSentence?: string
  sourceRefs?: SourceRef[]
  meaningsJson?: Array<Record<string, unknown>>
  payloadJson?: Record<string, unknown>
}

/** 提交复习结果的响应 */
export interface ReviewSubmitResult {
  vocabId: string
  success: boolean
  /** 下一次复习时间（时间戳毫秒） */
  nextReviewAt?: number
  /** 新的易度因子 */
  newEaseFactor: number
  /** 新的复习间隔（天） */
  newInterval: number
  /** 新的连续成功复习次数 */
  newRepetitions: number
  /** 新的掌握状态 */
  newMasteryStatus: string
  /** 本次复习质量评分 */
  quality: number
  /** 提示消息 */
  message: string
}

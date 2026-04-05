/**
 * 收藏全文 VM
 *
 * 只存对 analysis_records.recordId 的引用
 * 不复制整份 renderScene（按需从 record 读取）
 */

export interface FavoriteRecord {
  recordId: string
  createdAt: number
}

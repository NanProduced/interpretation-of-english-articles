/**
 * 分析记录 VM
 *
 * 对应本地存储的 analysis_record 数据结构
 * 不直接等同于后端 DTO，是前端用于回看的快照模型
 */

import type { AnalyzeRequest } from '../../services/api'
import type { RenderSceneVm, ResultPageState } from './render-scene.vm'

export interface AnalysisRecord {
  /** 本地生成唯一 ID */
  recordId: string
  /** 原始输入文本（用于重新分析） */
  sourceText: string
  /** 发给 /analyze 的请求参数 */
  requestPayload: {
    reading_goal: AnalyzeRequest['reading_goal']
    reading_variant: AnalyzeRequest['reading_variant']
    source_type: 'user_input'
  }
  /** 分析结果快照（null 表示分析失败/异常） */
  renderScene: RenderSceneVm | null
  /** 回看时的页面状态 */
  pageState: ResultPageState
  /** 创建时间（timestamp） */
  createdAt: number
  /** 最近一次更新时间（timestamp） */
  updatedAt: number
  /** 是否已收藏全文 */
  isFavorited: boolean
}

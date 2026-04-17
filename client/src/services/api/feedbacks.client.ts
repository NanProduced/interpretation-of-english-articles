/**
 * Cloud API: Feedback System
 *
 * 对应后端 GET/POST /feedbacks
 * 用于收集用户反馈，为后续 RAG 的 few-shot 注入做准备
 */

import { request } from './client'

// ---------------------------------------------------------------------------
// 类型定义
// ---------------------------------------------------------------------------

export type FeedbackType =
  | 'result_overall'
  | 'grammar_note'
  | 'sentence_analysis'
  | 'vocab_entry'
  | 'general'

export type FeedbackCategory =
  | 'data_error'
  | 'poor_quality'
  | 'translation_wrong'
  | 'incomplete'
  | 'irrelevant'
  | 'unclear'
  | 'performance'
  | 'ui_ux'
  | 'other'
  | 'too_slow'
  | 'layout_mess'
  | 'inaccurate_annotation'
  | 'split_wrong'
  | 'wrong_in_context'
  | 'feature_suggestion'
  | 'app_crash'
  | 'experience_issue'

export type FeedbackStatus = 'pending' | 'reviewed' | 'used_for_rag' | 'dismissed'

// ---------------------------------------------------------------------------
// 后端 DTO（snake_case）
// ---------------------------------------------------------------------------

interface FeedbackResponseDto {
  id: string
  user_id: string
  feedback_type: FeedbackType
  satisfaction: boolean | null
  category: FeedbackCategory | null
  detail_text: string | null
  analysis_record_id: string | null
  context_json: Record<string, unknown>
  client_metadata_json: Record<string, unknown>
  status: FeedbackStatus
  admin_note: string | null
  created_at: string
  updated_at: string
}

interface FeedbackListDto {
  items: FeedbackResponseDto[]
  total: number
  page: number
  limit: number
}

interface FeedbackCreateDto {
  id: string
  created: boolean
  created_at: string
}

interface ShouldTriggerResponse {
  should_trigger: boolean
}

// ---------------------------------------------------------------------------
// 上下文数据类型定义
// 
// 【重要设计原则】
// 所有能通过 analysis_record_id 关联查询到的数据（如原文、长度、解析结果）都不存储
// 只存储：关键 ID 引用、反馈特有元数据、无法通过关联查询的数据
// ---------------------------------------------------------------------------

/**
 * 结果页整体反馈的上下文数据
 * 
 * 可通过 analysis_record_id 查询的数据（不存储）：
 * - source_text（原文）→ 可计算 preview、length
 * - reading_goal, reading_variant, extended, user_facing_state（来自 analysis_records 表）
 * - sentence_count, vocab_count（来自 render_scene_json）
 * 
 * 必须存储的数据：
 * - source_text_hash：如果没有 analysis_record_id，用这个关联
 * - processing_ms：反馈触发时的处理耗时（可能在 analysis_records 中未保存）
 */
export interface ResultOverallContext {
  source_text_hash?: string
  processing_ms?: number
}

/**
 * 标注（语法/句式）反馈的上下文数据
 * 
 * 可通过 annotation_id + render_scene_json 查询的数据（不存储）：
 * - sentence_text（原文）
 * - annotation 具体内容（label, content 等）
 * 
 * 必须存储的数据：
 * - sentence_id：句子 ID（用于定位问题位置）
 * - annotation_id：标注 ID（用于定位具体是哪个标注）
 * - annotation_type：标注类型（grammar_note / sentence_analysis）
 */
export interface AnnotationContext {
  sentence_id?: string
  annotation_id?: string
  annotation_type?: 'grammar_note' | 'sentence_analysis'
}

/**
 * 词汇卡片反馈的上下文数据
 * 
 * 可通过 mark_id + render_scene_json 查询的数据（不存储）：
 * - lemma, part_of_speech, short_meaning, phonetic 等词汇信息
 * - source_sentence, context_preview 等上下文
 * 
 * 必须存储的数据：
 * - mark_id：词汇标记 ID（用于定位具体是哪个词汇）
 * - vocab_preview：词汇预览（方便快速查看反馈内容）
 * - vocab_source：词汇来源
 * - is_ai_annotated：是否 AI 标注（这个可能在 render_scene_json 中没有明确标识）
 */
export interface VocabContext {
  mark_id?: string
  vocab_preview?: string
  vocab_source?: string
  is_ai_annotated?: boolean
}

/**
 * 通用反馈的上下文数据
 * 
 * 通用反馈没有 analysis_record_id，所以需要存储一些元数据
 */
export interface GeneralContext {
  page?: string
  app_version?: string
  platform?: string
}

// ---------------------------------------------------------------------------
// API 调用参数类型
// ---------------------------------------------------------------------------

export interface SubmitFeedbackParams {
  feedback_type: FeedbackType
  satisfaction?: boolean | null
  category?: FeedbackCategory | null
  detail_text?: string | null
  analysis_record_id?: string | null
  context_json?: ResultOverallContext | AnnotationContext | VocabContext | GeneralContext
  client_metadata_json?: Record<string, unknown>
}

// ---------------------------------------------------------------------------
// API 调用
// ---------------------------------------------------------------------------

/**
 * 提交用户反馈
 */
export async function submitFeedback(
  params: SubmitFeedbackParams
): Promise<{ id: string; created: boolean }> {
  const res = await request<FeedbackCreateDto>({
    url: '/feedbacks',
    method: 'POST',
    data: {
      feedback_type: params.feedback_type,
      satisfaction: params.satisfaction ?? null,
      category: params.category ?? null,
      detail_text: params.detail_text ?? null,
      analysis_record_id: params.analysis_record_id ?? null,
      context_json: params.context_json ?? {},
      client_metadata_json: params.client_metadata_json ?? {},
    },
  })
  return { id: res.id, created: res.created }
}

/**
 * 检查是否应该弹出结果页反馈询问
 *
 * 触发规则：
 * 1. 文本字符数 > 300
 * 2. 响应时间 > 60 秒
 * 3. 结果状态为降级状态
 *
 * 同时限制：24 小时内最多弹出 3 次
 */
export async function checkShouldTriggerFeedback(
  params: {
    source_text_length: number
    processing_ms?: number
    user_facing_state?: string
  }
): Promise<boolean> {
  const queryParams = new URLSearchParams()
  queryParams.append('source_text_length', String(params.source_text_length))
  if (params.processing_ms !== undefined) {
    queryParams.append('processing_ms', String(params.processing_ms))
  }
  if (params.user_facing_state) {
    queryParams.append('user_facing_state', params.user_facing_state)
  }

  const res = await request<ShouldTriggerResponse>({
    url: `/feedbacks/check/should-trigger?${queryParams.toString()}`,
    method: 'GET',
  })
  return res.should_trigger
}

/**
 * 获取用户的反馈列表
 */
export async function fetchFeedbacks(
  page = 1,
  limit = 20,
  filters?: {
    feedback_type?: FeedbackType
    satisfaction?: boolean
    category?: FeedbackCategory
    status?: FeedbackStatus
  }
): Promise<{ items: FeedbackResponseDto[]; total: number }> {
  const queryParams = new URLSearchParams()
  queryParams.append('page', String(page))
  queryParams.append('limit', String(limit))

  if (filters?.feedback_type) {
    queryParams.append('feedback_type', filters.feedback_type)
  }
  if (filters?.satisfaction !== undefined) {
    queryParams.append('satisfaction', String(filters.satisfaction))
  }
  if (filters?.category) {
    queryParams.append('category', filters.category)
  }
  if (filters?.status) {
    queryParams.append('status', filters.status)
  }

  const res = await request<FeedbackListDto>({
    url: `/feedbacks?${queryParams.toString()}`,
  })
  return {
    items: res.items,
    total: res.total,
  }
}

/**
 * 获取单条反馈详情
 */
export async function fetchFeedback(feedbackId: string): Promise<FeedbackResponseDto | null> {
  try {
    const res = await request<FeedbackResponseDto>({
      url: `/feedbacks/${feedbackId}`,
    })
    return res
  } catch (err: unknown) {
    if ((err as any)?.statusCode === 404) return null
    throw err
  }
}

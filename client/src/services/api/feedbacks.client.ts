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
// ---------------------------------------------------------------------------

/** 结果页整体反馈的上下文数据 */
export interface ResultOverallContext {
  source_text_preview?: string
  source_text_length?: number
  reading_goal?: string
  reading_variant?: string
  extended?: boolean
  user_facing_state?: string
  processing_ms?: number
  task_status?: string
  sentence_count?: number
  vocab_count?: number
}

/** 标注（语法/句式）反馈的上下文数据 */
export interface AnnotationContext {
  sentence_id?: string
  sentence_text?: string
  annotation_id?: string
  annotation_type?: 'grammar_note' | 'sentence_analysis'
  label?: string
  content_preview?: string
  source_text_preview?: string
}

/** 词汇卡片反馈的上下文数据 */
export interface VocabContext {
  lemma?: string
  display_word?: string
  part_of_speech?: string
  short_meaning?: string
  phonetic?: string
  source_sentence?: string
  context_preview?: string
}

/** 通用反馈的上下文数据 */
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

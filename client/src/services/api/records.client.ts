/**
 * Cloud API: Analysis Records
 *
 * 对应后端 GET/POST/PATCH/DELETE /records
 * 需要认证，自动附带 Authorization header
 */

import { request } from './client'
import type { AnalysisRecord } from '../../types/view/analysis-record.vm'
import type { AnalyzeRequest } from './client'

// ---------------------------------------------------------------------------
// 后端 DTO（snake_case）
// ---------------------------------------------------------------------------

interface RecordResponseDto {
  id: string
  user_id: string
  client_record_id: string
  source_type: string
  title: string | null
  source_text: string
  source_text_hash: string
  request_payload_json: {
    reading_goal?: string
    reading_variant?: string
    source_type?: string
  }
  render_scene_json: Record<string, unknown> | null
  page_state_json: Record<string, unknown> | null
  reading_goal: string | null
  reading_variant: string | null
  user_facing_state: string | null
  workflow_version: string | null
  schema_version: string | null
  analysis_status: string
  last_opened_at: string | null
  created_at: string
  updated_at: string
}

interface RecordListDto {
  items: RecordResponseDto[]
  total: number
  page: number
  limit: number
}

interface RecordUpsertDto {
  id: string
  client_record_id: string
  created: boolean
  updated_at: string
}

// ---------------------------------------------------------------------------
// 字段映射：后端 DTO → 前端 VM
// ---------------------------------------------------------------------------

function dtoToVm(dto: RecordResponseDto): AnalysisRecord {
  const payload = dto.request_payload_json || {}
  return {
    recordId: dto.client_record_id,
    sourceText: dto.source_text,
    requestPayload: {
      reading_goal: payload.reading_goal as AnalyzeRequest['reading_goal'],
      reading_variant: payload.reading_variant as AnalyzeRequest['reading_variant'],
      source_type: (payload.source_type as AnalyzeRequest['source_type']) || 'user_input',
    },
    renderScene: (dto.render_scene_json as unknown as AnalysisRecord['renderScene']) || null,
    pageState: ((dto.page_state_json as unknown as { pageState?: string })?.pageState as AnalysisRecord['pageState']) || 'normal',
    createdAt: new Date(dto.created_at).getTime(),
    updatedAt: new Date(dto.updated_at).getTime(),
    isFavorited: false, // 云端不存这个，前端本地维护
  }
}

// ---------------------------------------------------------------------------
// API 调用
// ---------------------------------------------------------------------------

export interface SaveRecordParams {
  clientRecordId: string
  sourceText: string
  sourceTextHash: string
  requestPayload: {
    reading_goal: AnalyzeRequest['reading_goal']
    reading_variant: AnalyzeRequest['reading_variant']
    source_type: 'user_input'
  }
  renderScene: AnalysisRecord['renderScene']
  pageState: string
  userFacingState?: string | null
  workflowVersion?: string | null
  schemaVersion?: string | null
}

/**
 * 保存分析记录到云端（upsert by clientRecordId）
 */
export async function saveRecordToCloud(
  params: SaveRecordParams
): Promise<{ id: string; created: boolean }> {
  const res = await request<RecordUpsertDto>({
    url: '/records',
    method: 'POST',
    data: {
      client_record_id: params.clientRecordId,
      source_type: 'user_input',
      title: null,
      source_text: params.sourceText,
      source_text_hash: params.sourceTextHash,
      request_payload_json: params.requestPayload,
      render_scene_json: params.renderScene || {},
      page_state_json: { pageState: params.pageState },
      reading_goal: params.requestPayload.reading_goal,
      reading_variant: params.requestPayload.reading_variant,
      user_facing_state: params.userFacingState,
      workflow_version: params.workflowVersion,
      schema_version: params.schemaVersion,
      analysis_status: params.renderScene ? 'ready' : 'failed',
    },
  })
  return { id: res.id, created: res.created }
}

/**
 * 获取云端记录列表
 */
export async function fetchCloudRecords(
  page = 1,
  limit = 20
): Promise<{ items: AnalysisRecord[]; total: number }> {
  const res = await request<RecordListDto>({
    url: `/records?page=${page}&limit=${limit}`,
  })
  return {
    items: res.items.map(dtoToVm),
    total: res.total,
  }
}

/**
 * 获取单条云端记录
 */
export async function fetchCloudRecord(recordId: string): Promise<AnalysisRecord | null> {
  try {
    const res = await request<RecordResponseDto>({
      url: `/records/${recordId}`,
    })
    return dtoToVm(res)
  } catch (err: unknown) {
    if ((err as any)?.statusCode === 404) return null
    throw err
  }
}

/**
 * 更新云端记录
 */
export async function updateCloudRecord(
  recordId: string,
  patch: {
    title?: string
    render_scene_json?: Record<string, unknown>
    page_state_json?: Record<string, unknown>
    user_facing_state?: string
    analysis_status?: string
    last_opened_at?: string
  }
): Promise<void> {
  await request<void>({
    url: `/records/${recordId}`,
    method: 'PATCH',
    data: patch,
  })
}

/**
 * 删除云端记录
 */
export async function deleteCloudRecord(recordId: string): Promise<void> {
  await request<void>({
    url: `/records/${recordId}`,
    method: 'DELETE',
  })
}

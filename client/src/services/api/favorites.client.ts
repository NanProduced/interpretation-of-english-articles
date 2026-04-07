/**
 * Cloud API: Favorites
 *
 * 对应后端 GET/POST/DELETE /favorites
 * 需要认证，自动附带 Authorization header
 */

import { request } from './client'
import type { FavoriteRecord } from '../../types/view/favorites.vm'

// ---------------------------------------------------------------------------
// 后端 DTO（snake_case）
// ---------------------------------------------------------------------------

interface FavoriteResponseDto {
  id: string
  user_id: string
  target_type: string
  target_key: string
  analysis_record_id: string | null
  payload_json: Record<string, unknown>
  note: string | null
  created_at: string
  updated_at: string
}

interface FavoriteListDto {
  items: FavoriteResponseDto[]
  total: number
}

function dtoToVm(dto: FavoriteResponseDto): FavoriteRecord {
  return {
    recordId: dto.target_key,
    createdAt: new Date(dto.created_at).getTime(),
  }
}

// ---------------------------------------------------------------------------
// API 调用
// ---------------------------------------------------------------------------

/**
 * 获取云端收藏列表
 */
export async function fetchCloudFavorites(): Promise<{ items: FavoriteRecord[]; total: number }> {
  const res = await request<FavoriteListDto>({
    url: '/favorites',
  })
  return {
    items: res.items.map(dtoToVm),
    total: res.total,
  }
}

/**
 * 添加收藏
 */
export async function addFavoriteToCloud(
  analysisRecordId: string
): Promise<{ id: string }> {
  return request<{ id: string; ok: boolean }>({
    url: '/favorites',
    method: 'POST',
    data: {
      target_type: 'analysis_record',
      target_key: analysisRecordId,
      analysis_record_id: analysisRecordId,
      payload_json: {},
      note: null,
    },
  }).then((r) => ({ id: r.id }))
}

/**
 * 移除收藏
 */
export async function removeFavoriteFromCloud(
  analysisRecordId: string
): Promise<void> {
  await request<{ deleted: boolean }>({
    url: `/favorites/${analysisRecordId}`,
    method: 'DELETE',
  })
}

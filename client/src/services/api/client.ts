/**
 * API Client - 统一请求入口
 *
 * 所有 API 调用必须通过此模块
 * 支持环境配置 + 认证头注入预留
 */

import Taro from '@tarojs/taro'
import { apiConfig, getAuthHeaders } from '../../config/api.config'
import type { AnalyzeResponseDto } from '../../types/api/analyze-response.dto'
import type { DictResponseDto } from '../../types/api/dict-response.dto'

/** API 错误类型 */
export class ApiError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode: number,
    public response?: unknown
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** 请求选项 */
interface RequestOptions {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: unknown
  headers?: Record<string, string>
  timeout?: number
}

/**
 * 统一请求方法
 * - 自动添加 baseURL
 * - 自动注入认证头
 * - 统一错误处理
 */
export async function request<T>(options: RequestOptions): Promise<T> {
  const { url, method = 'GET', data, headers = {}, timeout = apiConfig.timeout } = options

  const fullUrl = url.startsWith('http') ? url : `${apiConfig.baseUrl}${url}`

  try {
    const response = await Taro.request({
      url: fullUrl,
      method,
      data,
      header: {
        ...getAuthHeaders(),
        ...headers,
      },
      timeout,
    })

    const { statusCode, data: responseData } = response

    if (statusCode >= 400) {
      throw new ApiError(
        `请求失败: ${statusCode}`,
        'HTTP_ERROR',
        statusCode,
        responseData
      )
    }

    return responseData as T
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }

    // Taro.request 可能的网络错误
    if (error instanceof Error) {
      if (error.message.includes('timeout')) {
        throw new ApiError('请求超时', 'TIMEOUT', 0)
      }
      if (error.message.includes('network') || error.message.includes('ERR_')) {
        throw new ApiError('网络错误', 'NETWORK_ERROR', 0)
      }
    }

    throw new ApiError('未知错误', 'UNKNOWN', 0, error)
  }
}

// ============ /analyze API ============

/**
 * /analyze 请求参数
 *
 * 对齐后端 AnalyzeRequest (analysis.py)
 * - reading_goal: exam | daily_reading | academic
 * - reading_variant: 按 reading_goal 分组
 *   - exam: gaokao | cet | gre | ielts_toefl
 *   - daily_reading: beginner_reading | intermediate_reading | intensive_reading
 *   - academic: academic_general
 *
 * 注意：当前联调范围仅限 source_type = 'user_input'
 * daily_article / ocr 不在本联调范围内
 */
export interface AnalyzeRequest {
  text: string
  reading_goal: 'exam' | 'daily_reading' | 'academic'
  reading_variant: 'gaokao' | 'cet' | 'gre' | 'ielts_toefl' | 'beginner_reading' | 'intermediate_reading' | 'intensive_reading' | 'academic_general'
  /** 当前联调范围: 仅限 user_input */
  source_type: 'user_input'
  /** 是否开启深度篇章分析 */
  extended?: boolean
}

/**
 * 调用 /analyze 接口
 *
 * 统一返回 AnalyzeResponseDto (snake_case)
 * 由调用方通过 analyzeResponseDtoToVm() 转换为前端 VM (camelCase)
 */
export async function fetchAnalyze(dto: AnalyzeRequest): Promise<AnalyzeResponseDto> {
  return request<AnalyzeResponseDto>({
    url: '/analyze',
    method: 'POST',
    data: dto,
  })
}

// ============ /dict API ============

/**
 * 调用 /dict 接口查询单词释义
 *
 * 使用 Free Dictionary API (dictionaryapi.dev)
 * 降级策略：网络失败时返回 null，不阻塞 UI
 */
export async function fetchDict(word: string): Promise<DictResponseDto> {
  return request<DictResponseDto>({
    url: `/dict?q=${encodeURIComponent(word)}&type=word`,
  })
}

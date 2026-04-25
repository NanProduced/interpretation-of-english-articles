/**
 * API Services 统一导出
 *
 * 使用方式:
 * import { analyze, AnalyzeRequest } from '@/services/api'
 */

// Client
export {
  fetchAnalyze,
  request,
  type AnalyzeRequest,
  ApiError,
  detectGenre,
  type GenreDetectionResponse,
  type GenreDetectionResult,
  type GenreCategory,
} from './client'

// Adapter
export { analyzeResponseDtoToVm } from './adapters/render-scene.adapter'

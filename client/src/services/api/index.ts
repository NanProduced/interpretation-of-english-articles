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
  fetchDict,
  fetchDictEntry,
  type AnalyzeRequest,
  ApiError,
} from './client'

// Adapter
export { analyzeResponseDtoToVm } from './adapters/render-scene.adapter'

// Dictionary Cache Utilities (for debugging and cache management)
export {
  getDictFromCache,
  getDictEntryFromCache,
  setDictToCache,
  setDictEntryToCache,
  clearL1Cache,
  clearL2Cache,
  getCacheStats,
} from './dictCache'

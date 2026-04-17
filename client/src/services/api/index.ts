/**
 * API Services 统一导出
 *
 * 使用方式:
 * import { analyze, AnalyzeRequest } from '@/services/api'
 */

// Client
export { fetchAnalyze, request, type AnalyzeRequest, ApiError } from './client'

// Adapter
export { analyzeResponseDtoToVm, vmToAnalyzeResponseDto } from './adapters/render-scene.adapter'

// Records
export {
  saveRecordToCloud,
  fetchCloudRecords,
  fetchCloudRecord,
  fetchCloudRecordByClientId,
  updateCloudRecord,
  deleteCloudRecord,
  type SaveRecordParams,
} from './records.client'

// Favorites
export {
  fetchCloudFavorites,
  addFavoriteToCloud,
  removeFavoriteFromCloud,
} from './favorites.client'

// Vocabulary
export {
  fetchCloudVocabulary,
  addVocabToCloud,
  updateCloudVocabulary,
  deleteCloudVocabulary,
} from './vocabulary.client'

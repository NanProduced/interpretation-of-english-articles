import { create } from 'zustand'
import { fetchAnalyze, AnalyzeRequest } from '../services/api'
import { analyzeResponseDtoToVm } from '../services/api/adapters/render-scene.adapter'
import { normalizeServerAnalyzeParams } from '../config/purpose'
import {
  RenderSceneVm,
  ResultPageState,
} from '../types/view/render-scene.vm'
import { saveRecord, generateRecordId, getRecord } from '../services/storage'
import { CloudSyncService } from '../services/cloudSync.service'
import type { AnalysisRecord } from '../types/view/analysis-record.vm'
import { track } from '../services/analytics'

/**
 * 页面状态推导（唯一状态入口）
 * 规则：
 * - idle | loading → loading
 * - error + TIMEOUT → timeout
 * - error + NETWORK_ERROR → network_fail
 * - error → failed
 * - empty → empty
 * - success → vm.userFacingState
 */
function derivePageState(
  phase: ArticlePhase,
  errorCode: string | null,
  vm: RenderSceneVm | null
): ResultPageState {
  if (phase === 'idle' || phase === 'loading') return 'loading'
  if (phase === 'error') {
    if (errorCode === 'TIMEOUT') return 'timeout'
    if (errorCode === 'NETWORK_ERROR') return 'network_fail'
    return 'failed'
  }
  if (phase === 'empty') return 'empty'
  // success
  return vm!.userFacingState
}

/**
 * 页面/分析状态机
 *
 * phase 是唯一的状态判定入口，sceneData/error 辅助判断内容
 * - idle:       初始态，未发起请求（result 页应显示 loading）
 * - loading:    请求中
 * - success:    请求成功，sceneData 有有效内容
 * - empty:      请求成功，但无有效内容（warnings 可能有内容）
 * - error:      请求失败
 */
export type ArticlePhase = 'idle' | 'loading' | 'success' | 'empty' | 'error'

/** 判断是否为"空结果"（请求成功但无有效内容） */
function isEmptyResult(vm: RenderSceneVm): boolean {
  const sentences = vm.article?.sentences
  if (!sentences || sentences.length === 0) return true
  return sentences.every((s) => !s.text || s.text.trim() === '')
}

interface ArticleState {
  // 渲染模型 (VM)
  sceneData: RenderSceneVm | null
  // 请求参数（用于重新发起）
  requestParams: AnalyzeRequest | null
  // 当前记录 ID（回看时使用）
  recordId: string | null
  // 内部状态机（仅 store 内部使用）
  phase: ArticlePhase
  error: string | null
  errorCode: string | null
  // 页面级状态（唯一对外状态口）
  pageState: ResultPageState
  // 是否为回看模式（不回写 storage）
  isReplayMode: boolean
  // Actions
  analyze: (params: AnalyzeRequest) => Promise<void>
  loadRecord: (recordId: string) => void
  reset: () => void
}

export const useArticleStore = create<ArticleState>((set, get) => ({
  sceneData: null,
  requestParams: null,
  recordId: null,
  phase: 'idle',
  error: null,
  errorCode: null,
  pageState: 'loading',
  isReplayMode: false,

  analyze: async (params: AnalyzeRequest) => {
    const normalizedRequest = {
      ...params,
      ...normalizeServerAnalyzeParams(params.reading_goal, params.reading_variant),
    } as AnalyzeRequest

    set({
      phase: 'loading',
      error: null,
      errorCode: null,
      requestParams: normalizedRequest,
      isReplayMode: false,
    })

    try {
      const dto = await fetchAnalyze(normalizedRequest)
      // 调试日志：确认后端返回的原始数据结构
      console.log('[article] analyze dto received:', {
        hasData: !!dto,
        schemaVersion: (dto as any)?.schema_version,
        hasArticle: !!(dto as any)?.article,
        articleParagraphs: (dto as any)?.article?.paragraphs?.length,
        articleSentences: (dto as any)?.article?.sentences?.length,
        inlineMarksCount: (dto as any)?.inline_marks?.length,
        userFacingState: (dto as any)?.user_facing_state,
      })
      const vm: RenderSceneVm = analyzeResponseDtoToVm(dto)
      const phase = isEmptyResult(vm) ? 'empty' : 'success'
      const pageState = derivePageState(phase, null, vm)

      // 自动保存到本地历史记录（非回看模式）
      const recordId = generateRecordId()
      const record: AnalysisRecord = {
        recordId,
        sourceText: normalizedRequest.text,
        requestPayload: {
          reading_goal: normalizedRequest.reading_goal,
          reading_variant: normalizedRequest.reading_variant,
          source_type: 'user_input',
        },
        renderScene: vm,
        pageState,
        createdAt: Date.now(),
        updatedAt: Date.now(),
        isFavorited: false,
      }
      saveRecord(record)
      // 静默同步到云端（未登录自动跳过，失败不阻塞）
      CloudSyncService.syncRecord(record)
      track('analyze_success', { pageState })

      set({ sceneData: vm, phase, pageState, recordId })
    } catch (err: any) {
      // 详细日志，便于调试
      console.error('[article] analyze failed:', {
        name: err?.name,
        message: err?.message,
        code: err?.code,
        statusCode: err?.statusCode,
        response: err?.response,
        stack: err?.stack,
      })
      const message = err?.message || '网络或服务异常，请稍后重试'
      const code = err?.code || 'UNKNOWN'
      const phase: ArticlePhase = 'error'
      const pageState = derivePageState(phase, code, null)

      // 分析失败也保存一条记录（renderScene = null），便于回看
      const recordId = generateRecordId()
      const record: AnalysisRecord = {
        recordId,
        sourceText: normalizedRequest.text,
        requestPayload: {
          reading_goal: normalizedRequest.reading_goal,
          reading_variant: normalizedRequest.reading_variant,
          source_type: 'user_input',
        },
        renderScene: null,
        pageState,
        createdAt: Date.now(),
        updatedAt: Date.now(),
        isFavorited: false,
      }
      saveRecord(record)
      track('analyze_failed', { errorCode: code })

      set({ error: message, errorCode: code, phase, pageState, recordId })
    }
  },

  /** 从历史记录加载（回看模式，不重新请求） */
  loadRecord: (recordId: string) => {
    const record = getRecord(recordId)
    if (!record) {
      set({ phase: 'error', error: '记录不存在或已删除', errorCode: 'RECORD_NOT_FOUND', pageState: 'failed', recordId: null, isReplayMode: true })
      return
    }
    const pageState = record.pageState
    const phase = pageState === 'empty' ? 'empty'
      : pageState === 'failed' || pageState === 'timeout' || pageState === 'network_fail' ? 'error'
      : record.renderScene ? 'success' : 'error'
    set({
      sceneData: record.renderScene,
      requestParams: record.sourceText ? {
        text: record.sourceText,
        ...normalizeServerAnalyzeParams(
          record.requestPayload.reading_goal,
          record.requestPayload.reading_variant
        ),
        source_type: 'user_input',
      } : null,
      recordId,
      phase,
      error: null,
      errorCode: null,
      pageState,
      isReplayMode: true,
    })
  },

  reset: () => set({
    sceneData: null,
    requestParams: null,
    recordId: null,
    phase: 'idle',
    error: null,
    errorCode: null,
    pageState: 'loading',
    isReplayMode: false,
  }),
}))

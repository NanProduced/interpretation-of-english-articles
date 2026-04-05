import { create } from 'zustand'
import { fetchAnalyze, AnalyzeRequest } from '../services/api'
import { analyzeResponseDtoToVm } from '../services/api/adapters/render-scene.adapter'
import {
  RenderSceneVm,
  RenderSceneVmBase,
  ContentResultState,
  ResultPageState,
} from '../types/view/render-scene.vm'

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
  return (
    vm.article.sentences.length === 0 ||
    vm.article.sentences.every((s) => s.text.trim() === '')
  )
}

interface ArticleState {
  // 渲染模型 (VM)
  sceneData: RenderSceneVm | null
  // 请求参数（用于重新发起）
  requestParams: AnalyzeRequest | null
  // 内部状态机（仅 store 内部使用）
  phase: ArticlePhase
  error: string | null
  errorCode: string | null
  // 页面级状态（唯一对外状态口）
  pageState: ResultPageState
  // Actions
  analyze: (params: AnalyzeRequest) => Promise<void>
  reset: () => void
}

export const useArticleStore = create<ArticleState>((set) => ({
  sceneData: null,
  requestParams: null,
  phase: 'idle',
  error: null,
  errorCode: null,
  pageState: 'loading',

  analyze: async (params: AnalyzeRequest) => {
    set({ phase: 'loading', error: null, errorCode: null, requestParams: params })

    try {
      const dto = await fetchAnalyze(params)
      const vm: RenderSceneVm = analyzeResponseDtoToVm(dto)
      const phase = isEmptyResult(vm) ? 'empty' : 'success'
      const pageState = derivePageState(phase, null, vm)
      set({ sceneData: vm, phase, pageState })
    } catch (err: any) {
      const message = err?.message || '网络或服务异常，请稍后重试'
      const code = err?.code || 'UNKNOWN'
      const phase: ArticlePhase = 'error'
      const pageState = derivePageState(phase, code, null)
      set({ error: message, errorCode: code, phase, pageState })
    }
  },

  reset: () => set({
    sceneData: null,
    requestParams: null,
    phase: 'idle',
    error: null,
    errorCode: null,
    pageState: 'loading',
  }),
}))

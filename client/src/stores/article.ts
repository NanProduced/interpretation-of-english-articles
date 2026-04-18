import Taro from '@tarojs/taro'
import { create } from 'zustand'
import {
  AnalyzeRequest,
  submitAnalysisTask,
  fetchAnalyze,
  getTaskStatus,
  getCurrentTask,
  checkAnonymousQuota,
  ApiError,
} from '../services/api/client'
import { fetchCloudRecord, fetchCloudRecordByClientId } from '../services/api/records.client'
import { analyzeResponseDtoToVm } from '../services/api/adapters/render-scene.adapter'
import { normalizeServerAnalyzeParams } from '../config/purpose'
import { useAuthStore } from './auth'
import {
  RenderSceneVm,
  ResultPageState,
} from '../types/view/render-scene.vm'
import { saveRecord, getRecord, updateVocabularyRecordId } from '../services/storage'
import type { AnalysisRecord } from '../types/view/analysis-record.vm'
import { track } from '../services/analytics'

function derivePageState(
  phase: ArticlePhase,
  errorCode: string | null,
  vm: RenderSceneVm | null
): ResultPageState {
  if (phase === 'idle' || phase === 'loading' || phase === 'polling') return 'loading'
  if (phase === 'error') {
    if (errorCode === 'TIMEOUT') return 'timeout'
    if (errorCode === 'NETWORK_ERROR') return 'network_fail'
    if (errorCode === 'AUTH_REQUIRED') return 'failed'
    return 'failed'
  }
  if (phase === 'empty') return 'empty'
  
  const state = vm?.userFacingState
  if (!state || (state as any) === 'loading') return 'normal'
  return state
}

export type ArticlePhase = 'idle' | 'loading' | 'polling' | 'success' | 'empty' | 'error'

function isEmptyResult(vm: RenderSceneVm): boolean {
  const sentences = vm.article?.sentences
  if (!sentences || sentences.length === 0) return true
  return sentences.every((s) => !s.text || s.text.trim() === '')
}

function deriveFallbackTitle(text: string): string | null {
  const firstLine = text.split('\n')[0]?.trim() || ''
  if (!firstLine) return null
  return firstLine.length > 50 ? `${firstLine.slice(0, 50)}...` : firstLine
}

function generateLocalRecordId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

let currentAbortFlag = false

interface ArticleState {
  sceneData: RenderSceneVm | null
  requestParams: AnalyzeRequest | null
  recordId: string | null
  cloudId: string | null
  phase: ArticlePhase
  error: string | null
  errorCode: string | null
  pageState: ResultPageState
  isReplayMode: boolean
  analyze: (params: AnalyzeRequest) => Promise<void>
  recoverActiveTask: (targetRecordId?: string) => Promise<void>
  loadRecord: (recordId: string) => void
  reset: () => void
}

export const useArticleStore = create<ArticleState>((set, get) => {

  const applySuccessRecord = (
    cloudRecord: AnalysisRecord,
    fallbackCloudId: string
  ) => {
    if (!cloudRecord.renderScene) {
      throw new Error('Record not found or empty render scene')
    }
    const vm = cloudRecord.renderScene
    const phase = isEmptyResult(vm) ? 'empty' : 'success'
    let pageState = derivePageState(phase, null, vm)
    
    if (pageState === 'loading' && phase === 'success') {
      pageState = 'normal'
    }

    const currentRecordId = get().recordId
    const newRecordId = cloudRecord.recordId

    if (currentRecordId && currentRecordId !== newRecordId) {
      updateVocabularyRecordId(currentRecordId, newRecordId)
    }

    const localRecord: AnalysisRecord = {
      ...cloudRecord,
      pageState,
    }
    saveRecord(localRecord)
    track('analyze_success', { pageState })

    if (!currentAbortFlag) {
      set({
        sceneData: vm,
        phase,
        pageState,
        recordId: newRecordId,
        cloudId: fallbackCloudId,
      })
    }
  }

  const startPolling = async (taskId: string) => {
    if (get().phase === 'success' || get().phase === 'empty') return

    while (!currentAbortFlag) {
      try {
        const statusRes = await getTaskStatus(taskId)
        if (get().phase === 'success' || get().phase === 'empty') break

        if (['queued', 'running', 'finalizing'].includes(statusRes.status)) {
          await new Promise(resolve => setTimeout(resolve, 2000))
          continue
        }

        if (statusRes.status === 'succeeded') {
          const cloudRecord = await fetchCloudRecord(statusRes.record_id)
          if (!cloudRecord) {
            throw new Error('Record not found')
          }
          applySuccessRecord(cloudRecord, statusRes.record_id)
          break
        }

        const errorCode = statusRes.failure_code || 'UNKNOWN'
        throw new ApiError(statusRes.failure_message || '分析失败', errorCode, 500)

      } catch (err: any) {
        if (currentAbortFlag) break
        if (get().phase === 'success' || get().phase === 'empty') break

        const message = err?.message || '网络或服务异常，请稍后重试'
        const code = err?.code || 'UNKNOWN'
        const phase: ArticlePhase = 'error'
        const pageState = derivePageState(phase, code, null)

        track('analyze_failed', { errorCode: code })
        set({ error: message, errorCode: code, phase, pageState })
        break
      }
    }
  }

  return {
    sceneData: null,
    requestParams: null,
    recordId: null,
    cloudId: null,
    phase: 'idle',
    error: null,
    errorCode: null,
    pageState: 'loading',
    isReplayMode: false,

    analyze: async (params: AnalyzeRequest) => {
      currentAbortFlag = false

      const normalizedRequest = {
        ...params,
        ...normalizeServerAnalyzeParams(params.reading_goal, params.reading_variant),
      } as AnalyzeRequest

      set({
        phase: 'loading',
        error: null,
        errorCode: null,
        sceneData: null,
        requestParams: normalizedRequest,
        isReplayMode: false,
      })

      // 匿名用户：先消耗试用次数（POST /quota/check 会在后端累加计数）
      if (!useAuthStore.getState().isLoggedIn) {
        const anonymousId = Taro.getStorageSync('anonymous_id') as string | undefined
        if (anonymousId) {
          try {
            const quotaResult = await checkAnonymousQuota(anonymousId)
            if (!quotaResult.allowed) {
              set({
                phase: 'error',
                error: '今日试用次数已用完，请登录后继续使用',
                errorCode: 'GUEST_QUOTA_EXCEEDED',
                pageState: 'failed',
              })
              return
            }
          } catch {
            // 网络错误时静默放行，不阻塞用户体验
          }
        }
      }

      const clientRecordId = `task-${generateLocalRecordId()}`
      let taskId = ''
      let serverRecordId = ''

      try {
        if (!useAuthStore.getState().isLoggedIn) {
          const res = await fetchAnalyze(normalizedRequest)
          const vm = analyzeResponseDtoToVm(res)
          const phase = isEmptyResult(vm) ? 'empty' : 'success'
          let pageState = derivePageState(phase, null, vm)
          if (pageState === 'loading' && phase === 'success') {
            pageState = 'normal'
          }
          
          const localRecord: AnalysisRecord = {
            recordId: clientRecordId,
            title: deriveFallbackTitle(normalizedRequest.text),
            sourceText: normalizedRequest.text,
            requestPayload: {
              reading_goal: normalizedRequest.reading_goal,
              reading_variant: normalizedRequest.reading_variant,
              source_type: normalizedRequest.source_type,
            },
            renderScene: vm,
            pageState,
            createdAt: Date.now(),
            updatedAt: Date.now(),
            isFavorited: false,
          }
          saveRecord(localRecord)
          track('analyze_success', { pageState })
          set({
            sceneData: vm,
            phase,
            pageState,
            recordId: clientRecordId,
            cloudId: null,
          })
          return
        }

        const res = await submitAnalysisTask({
          ...normalizedRequest,
          wait_for_result: true,
          wait_timeout_seconds: 40,
          client_record_id: clientRecordId,
        })
        taskId = res.task_id
        serverRecordId = res.record_id

        if (res.render_scene) {
          const vm = analyzeResponseDtoToVm(res.render_scene)
          const phase = isEmptyResult(vm) ? 'empty' : 'success'
          let pageState = derivePageState(phase, null, vm)
          if (pageState === 'loading' && phase === 'success') {
            pageState = 'normal'
          }
          
          const localRecord: AnalysisRecord = {
            recordId: clientRecordId,
            cloudId: serverRecordId,
            title: deriveFallbackTitle(normalizedRequest.text),
            sourceText: normalizedRequest.text,
            requestPayload: {
              reading_goal: normalizedRequest.reading_goal,
              reading_variant: normalizedRequest.reading_variant,
              source_type: normalizedRequest.source_type,
            },
            renderScene: vm,
            pageState,
            createdAt: Date.now(),
            updatedAt: Date.now(),
            isFavorited: false,
          }
          saveRecord(localRecord)
          track('analyze_success', { pageState })
          set({
            sceneData: vm,
            phase,
            pageState,
            recordId: clientRecordId,
            cloudId: serverRecordId,
          })
          return
        }

        const pageState = derivePageState('polling', null, null)
        set({ phase: 'polling', pageState, recordId: clientRecordId, cloudId: serverRecordId })
      } catch (err: any) {
        if (err instanceof ApiError && err.statusCode === 409) {
          const current = await getCurrentTask()
          if (current.has_active && current.task) {
             taskId = current.task.task_id
             serverRecordId = current.task.record_id
             
             const cloudRecord = await fetchCloudRecord(serverRecordId)
             if (!cloudRecord) {
                const message = '无法恢复当前任务，请稍后重试'
                set({ error: message, errorCode: 'RECOVERY_FAILED', phase: 'error', pageState: 'failed' })
                return
             }
             
             const realClientRecordId = cloudRecord.recordId
             
             if (clientRecordId !== realClientRecordId) {
               updateVocabularyRecordId(clientRecordId, realClientRecordId)
             }
             
             const recoveryPageState = derivePageState('polling', null, null)
             set({ phase: 'polling', pageState: recoveryPageState, recordId: realClientRecordId, cloudId: serverRecordId })
             await startPolling(taskId)
             return
          } else {
             throw err
          }
        } else if (err instanceof ApiError && err.statusCode === 402) {
          set({
            error: '今日解析积分已用尽',
            errorCode: 'INSUFFICIENT_CREDITS',
            phase: 'error',
            pageState: 'failed',
          })
          return
        } else if (err instanceof ApiError && err.statusCode === 401) {
          set({
            error: '请先登录以开始解析',
            errorCode: 'AUTH_REQUIRED',
            phase: 'error',
            pageState: 'failed',
          })
          return
        } else {
          const message = err?.message || '网络或服务异常，请稍后重试'
          const code = err?.code || 'UNKNOWN'
          const phase: ArticlePhase = 'error'
          const pageState = derivePageState(phase, code, null)
          set({ error: message, errorCode: code, phase, pageState })
          return
        }
      }

      await startPolling(taskId)
    },

    recoverActiveTask: async (targetRecordId?: string) => {
      if (get().phase === 'polling' || get().phase === 'loading') return
      
      try {
        const current = await getCurrentTask()
        if (current.has_active && current.task) {
          const serverRecordId = current.task.record_id
          
          if (targetRecordId && targetRecordId !== serverRecordId) {
             const cloudRecord = await fetchCloudRecord(serverRecordId)
             if (cloudRecord && cloudRecord.recordId !== targetRecordId) {
                return 
             }
          }

          currentAbortFlag = false

          const cloudRecord = await fetchCloudRecord(serverRecordId)
          if (!cloudRecord) {
             return
          }

          const realClientRecordId = cloudRecord.recordId
          const currentRecordId = get().recordId

          if (currentRecordId && currentRecordId !== realClientRecordId) {
            updateVocabularyRecordId(currentRecordId, realClientRecordId)
          }

          set({
            recordId: realClientRecordId,
            cloudId: serverRecordId,
            phase: 'polling',
            isReplayMode: false,
            error: null,
            errorCode: null,
            pageState: 'loading'
          })

          await startPolling(current.task.task_id)
        }
      } catch (err) {
        // Silently ignore recovery failure
      }
    },

    loadRecord: async (recordId: string) => {
      const record = getRecord(recordId)
      if (!record) {
        const { isLoggedIn } = useAuthStore.getState()
        if (isLoggedIn) {
          try {
            const cloudRecord = await fetchCloudRecordByClientId(recordId)
            if (cloudRecord) {
              saveRecord(cloudRecord)
              const pageState = cloudRecord.pageState
              const phase = pageState === 'empty' ? 'empty'
                : pageState === 'failed' || pageState === 'timeout' || pageState === 'network_fail' ? 'error'
                : cloudRecord.renderScene ? 'success' : 'error'
              set({
                sceneData: cloudRecord.renderScene,
                requestParams: cloudRecord.sourceText ? {
                  text: cloudRecord.sourceText,
                  ...normalizeServerAnalyzeParams(
                    cloudRecord.requestPayload.reading_goal,
                    cloudRecord.requestPayload.reading_variant
                  ),
                  source_type: cloudRecord.requestPayload.source_type || 'user_input',
                } : null,
                recordId,
                cloudId: cloudRecord.cloudId || null,
                phase,
                error: null,
                errorCode: null,
                pageState,
                isReplayMode: true,
              })
              return
            }
          } catch (err) {
            // Silently ignore
          }
        }
        set({ phase: 'error', error: '记录不存在或已删除', errorCode: 'RECORD_NOT_FOUND', pageState: 'failed', recordId: null, cloudId: null, isReplayMode: true })
        return
      }

      if (record.pageState === 'loading' && !record.renderScene) {
         get().recoverActiveTask(recordId)
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
          source_type: record.requestPayload.source_type || 'user_input',
        } : null,
        recordId,
        cloudId: record.cloudId || null,
        phase,
        error: null,
        errorCode: null,
        pageState,
        isReplayMode: true,
      })
    },

    reset: () => {
      currentAbortFlag = true
      set({
        sceneData: null,
        requestParams: null,
        recordId: null,
        cloudId: null,
        phase: 'idle',
        error: null,
        errorCode: null,
        pageState: 'loading',
        isReplayMode: false,
      })
    },
  }
})

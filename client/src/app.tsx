import { PropsWithChildren, useEffect } from 'react'
import Taro from '@tarojs/taro'
import { useAuthStore } from './stores/auth'
import { useArticleStore } from './stores/article'
import { CloudSyncService } from './services/cloudSync.service'
import { getFavorites, getVocabulary } from './services/storage'
import './app.scss'

const INTERRUPTED_STATE_KEY = 'analysis_interrupted'

function App({ children }: PropsWithChildren<any>) {
  // 启动时恢复认证状态
  useEffect(() => {
    const restoreState = async () => {
      await useAuthStore.getState().restore()
      if ((Taro as any)._navigatingToOnboarding) return
      ;(Taro as any)._navigatingToOnboarding = true
      // restore 完成后检查是否首次登录（已登录但未设置过用户配置）→ 跳转 onboarding
      const { isLoggedIn } = useAuthStore.getState()
      if (isLoggedIn && !Taro.getStorageSync('user_configured')) {
        Taro.navigateTo({ url: '/pages/onboarding/index' })
      }
    }
    restoreState()
  }, [])

  // 处理小程序切前台/后台事件
  useEffect(() => {
    // 切后台：保存分析中断状态
    const hideHandler = () => {
      const { phase, recordId } = useArticleStore.getState()
      if ((phase === 'loading' || phase === 'polling') && recordId) {
        try {
          Taro.setStorageSync(INTERRUPTED_STATE_KEY, {
            interruptedAt: Date.now(),
            recordId,
          })
        } catch {
          // ignore
        }
      }
    }

    // 切前台：恢复状态 + 尝试同步 pending 数据
    const showHandler = async (options: any) => {
      // 尝试静默同步 pending 数据（未登录则跳过）
      if (useAuthStore.getState().isLoggedIn) {
        const favorites = getFavorites()
        const vocab = getVocabulary()
        if (favorites.length > 0) {
          CloudSyncService.syncAllFavorites(favorites)
        }
        if (vocab.length > 0) {
          CloudSyncService.syncAllVocab(vocab)
        }
      }

      // 检查是否分析中断需要恢复
      let interrupted: { interruptedAt: number; recordId: string } | null = null
      try {
        interrupted = Taro.getStorageSync(INTERRUPTED_STATE_KEY)
        Taro.removeStorageSync(INTERRUPTED_STATE_KEY)
      } catch {
        // ignore
      }

      if (!interrupted) return

      const { phase, sceneData, recordId } = useArticleStore.getState()

      // 分析中断后优先尝试恢复活跃任务，而不是直接判失败
      if ((phase === 'loading' || phase === 'polling') && !sceneData && interrupted.recordId === recordId) {
        await useArticleStore.getState().recoverActiveTask(recordId || undefined)
      }
    }

    Taro.onAppHide(hideHandler)
    Taro.onAppShow(showHandler)
    return () => {
      Taro.offAppHide(hideHandler)
      Taro.offAppShow(showHandler)
    }
  }, [])

  return children
}

export default App

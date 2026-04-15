import { PropsWithChildren, useEffect, useState, useCallback } from 'react'
import Taro from '@tarojs/taro'
import { useAuthStore } from './stores/auth'
import { useArticleStore } from './stores/article'
import { CloudSyncService } from './services/cloudSync.service'
import { ensureLoggedIn } from './services/auth'
import { getFavorites, getVocabulary } from './services/storage'
import LoginGuideModal from './components/LoginGuideModal'
import './app.scss'

const INTERRUPTED_STATE_KEY = 'analysis_interrupted'
const GUEST_DISMISSED_KEY = 'guest_dismissed'

function App({ children }: PropsWithChildren<any>) {
  const [showLoginGuide, setShowLoginGuide] = useState(false)

  const handleGuestDismiss = useCallback(() => {
    Taro.setStorageSync(GUEST_DISMISSED_KEY, new Date().toDateString())
    setShowLoginGuide(false)
  }, [])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showLoginGuide) {
        handleGuestDismiss()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [showLoginGuide, handleGuestDismiss])

  useEffect(() => {
    const restoreState = async () => {
      await useAuthStore.getState().restore()
      if ((Taro as any)._navigatingToOnboarding) return
      ;(Taro as any)._navigatingToOnboarding = true

      const { isLoggedIn } = useAuthStore.getState()

      if (isLoggedIn && !Taro.getStorageSync('user_configured')) {
        Taro.navigateTo({ url: '/pages/onboarding/index' })
      } else if (!isLoggedIn) {
        const dismissed = Taro.getStorageSync(GUEST_DISMISSED_KEY)
        const today = new Date().toDateString()
        if (dismissed !== today) {
          setShowLoginGuide(true)
        }
      }
    }
    restoreState()
  }, [])

  const handleLogin = async () => {
    setShowLoginGuide(false)
    const result = await ensureLoggedIn(true)
    if (result.success && result.isFirstLogin) {
      Taro.navigateTo({ url: '/pages/profile/index' })
    }
  }

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

  return (
    <>
      {children}
      <LoginGuideModal
        visible={showLoginGuide}
        onClose={handleGuestDismiss}
        onLogin={handleLogin}
      />
    </>
  )
}

export default App

import { PropsWithChildren, useEffect, useState } from 'react'
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
const INVITER_ID_KEY = 'pending_inviter_id'

function extractInviterId(options: any): string | null {
  const query = options?.query || options
  const inviter = query?.inviter || query?.inviter_id
  if (inviter && typeof inviter === 'string' && inviter.trim()) {
    return inviter.trim()
  }
  return null
}

function savePendingInviter(inviterId: string): void {
  const { isLoggedIn } = useAuthStore.getState()
  if (isLoggedIn) {
    console.log('[invite] User already logged in, ignoring invite')
    return
  }
  const existing = Taro.getStorageSync(INVITER_ID_KEY)
  if (existing && existing !== inviterId) {
    console.log('[invite] Inviter ID conflict, keeping first one:', existing)
    return
  }
  Taro.setStorageSync(INVITER_ID_KEY, inviterId)
  console.log('[invite] Saved pending inviter:', inviterId)
}

function App({ children }: PropsWithChildren<any>) {
  const [showLoginGuide, setShowLoginGuide] = useState(false)

  // 启动时恢复认证状态 + 处理邀请参数
  useEffect(() => {
    const restoreState = async () => {
      const launchOptions = Taro.getLaunchOptionsSync()
      console.log('[app] Launch options:', launchOptions)
      
      const inviterId = extractInviterId(launchOptions)
      if (inviterId) {
        savePendingInviter(inviterId)
      }

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
    // LoginGuideModal 已提供确认 UI，跳过 ensureLoggedIn 中的重复弹窗
    const result = await ensureLoggedIn(true)
    if (result.success && result.isFirstLogin) {
      // 首次登录 → 跳转到 Profile 引导填写头像昵称
      Taro.navigateTo({ url: '/pages/profile/index' })
    }
  }

  const handleGuestDismiss = () => {
    // 记录当天已选择游客模式，明天再弹
    Taro.setStorageSync(GUEST_DISMISSED_KEY, new Date().toDateString())
    setShowLoginGuide(false)
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

    // 切前台：处理邀请参数 + 恢复状态 + 尝试同步 pending 数据
    const showHandler = async (options: any) => {
      console.log('[app] onAppShow options:', options)
      
      const inviterId = extractInviterId(options)
      if (inviterId) {
        savePendingInviter(inviterId)
      }

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

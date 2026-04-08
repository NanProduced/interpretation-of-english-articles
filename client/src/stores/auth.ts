/**
 * 认证状态管理
 *
 * 管理微信登录 token 和用户信息，
 * 提供持久化和跨请求的认证状态共享。
 */

import Taro from '@tarojs/taro'
import { create } from 'zustand'

const AUTH_TOKEN_KEY = 'auth_token'
const AUTH_USER_KEY = 'auth_user_info'

export interface UserInfo {
  user_id: string
  session_id?: string
  avatar_url?: string
  nickname?: string
}

interface AuthState {
  token: string | null
  userInfo: UserInfo | null
  isLoggedIn: boolean

  /** 登录成功，写入 token 和 用户信息 */
  login: (token: string, userInfo: UserInfo) => void

  /** 更新用户信息字段（如头像、昵称） */
  updateUserInfo: (updates: Partial<UserInfo>) => void

  /** 登出，清除所有认证状态 */
  logout: () => void

  /** 从本地存储恢复认证状态（启动时调用） */
  restore: () => void

  /** 调用 /auth/session/me 获取最新用户信息 */
  fetchUserInfo: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  userInfo: null,
  isLoggedIn: false,

  login: (token: string, userInfo: UserInfo) => {
    Taro.setStorageSync(AUTH_TOKEN_KEY, token)
    Taro.setStorageSync(AUTH_USER_KEY, JSON.stringify(userInfo))
    set({ token, userInfo, isLoggedIn: true })
  },

  updateUserInfo: (updates: Partial<UserInfo>) => {
    const { userInfo } = get()
    if (!userInfo) return
    const newUserInfo = { ...userInfo, ...updates }
    Taro.setStorageSync(AUTH_USER_KEY, JSON.stringify(newUserInfo))
    set({ userInfo: newUserInfo })
  },

  logout: () => {
    // 异步调用后端登出（fire-and-forget），不阻塞本地清理
    const token = useAuthStore.getState().token
    if (token) {
      import('../services/api/client').then(({ fetchSessionLogout }) => {
        fetchSessionLogout(token).catch(() => {
          // 登出 API 失败静默忽略，token 已本地清除
        })
      })
    }
    Taro.removeStorageSync(AUTH_TOKEN_KEY)
    Taro.removeStorageSync(AUTH_USER_KEY)
    set({ token: null, userInfo: null, isLoggedIn: false })
  },


  restore: () => {
    try {
      const token = Taro.getStorageSync(AUTH_TOKEN_KEY) as string | undefined
      const userInfoRaw = Taro.getStorageSync(AUTH_USER_KEY) as string | undefined
      if (token && userInfoRaw) {
        const userInfo = JSON.parse(userInfoRaw) as UserInfo
        set({ token, userInfo, isLoggedIn: true })
      }
    } catch {
      // ignore parse errors, treat as not logged in
      set({ token: null, userInfo: null, isLoggedIn: false })
    }
  },

  fetchUserInfo: async () => {
    const { token } = get()
    if (!token) return

    try {
      const { fetchSessionUser } = await import('../services/api/client')
      const data = await fetchSessionUser()
      const userInfo: UserInfo = {
        user_id: data.user_id,
        session_id: data.session_id,
        avatar_url: data.avatar_url,
        nickname: data.nickname,
      }
      Taro.setStorageSync(AUTH_USER_KEY, JSON.stringify(userInfo))
      set({ userInfo })
    } catch {
      // 网络错误，静默忽略，下次请求会自然触发 401
    }
  },
}))

/** 便捷导出：直接获取当前 token（用于请求头注入） */
export function getToken(): string | null {
  return useAuthStore.getState().token
}

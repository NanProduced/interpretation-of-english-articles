/**
 * 认证服务
 *
 * 封装微信登录流程，供非 Profile 页面调用（收藏/生词本等场景引导登录）
 */

import Taro from '@tarojs/taro'
import { useAuthStore } from '../stores/auth'
import { fetchWeChatLogin } from './api/client'

/**
 * 引导用户登录
 *
 * 流程：
 * 1. 检查是否已登录（已登录直接返回 true）
 * 2. 弹出确认对话框
 * 3. 用户确认 → 调用 wx.login → 后端换取 session token → 存到 auth store
 * 4. 用户取消 → 返回 false
 *
 * @returns true = 登录成功，false = 用户取消或失败
 */
export async function ensureLoggedIn(): Promise<boolean> {
  // 已登录，直接放行
  if (useAuthStore.getState().isLoggedIn) {
    return true
  }

  // 弹确认框
  const { confirm } = await Taro.showModal({
    title: '登录后同步云端',
    content: '登录后可将收藏和生词本同步到云端，跨设备查看。是否立即登录？',
    confirmText: '微信登录',
    confirmColor: '#07c160',
    cancelText: '稍后',
  })

  if (!confirm) {
    return false
  }

  // 执行微信登录
  try {
    const loginResult = await Taro.login()
    if (!loginResult.code) {
      Taro.showToast({ title: '微信登录失败', icon: 'none' })
      return false
    }

    const res = await fetchWeChatLogin(loginResult.code)
    useAuthStore.getState().login(res.session_token, { user_id: res.user_id })
    Taro.showToast({ title: '登录成功', icon: 'success' })
    return true
  } catch (err) {
    console.warn('[auth] ensureLoggedIn failed', err)
    Taro.showToast({ title: '登录失败，请重试', icon: 'none' })
    return false
  }
}

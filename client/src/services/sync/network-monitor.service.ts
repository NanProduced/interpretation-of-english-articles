/**
 * 网络状态监听服务
 *
 * 监听网络状态变化，在网络从离线恢复到在线时
 * 自动触发同步队列消费
 */

import Taro from '@tarojs/taro'
import type { NetworkStatus } from '../../types/sync-queue.vm'
import { getSyncMetadata, saveSyncMetadata } from '../storage'

/**
 * 网络状态变化回调
 */
export type NetworkStatusChangeCallback = (
  status: NetworkStatus,
  previousStatus: NetworkStatus
) => void

/**
 * 网络连接类型
 */
export type NetworkType = 'wifi' | '2g' | '3g' | '4g' | '5g' | 'unknown' | 'none'

/**
 * 网络状态监听服务
 */
export class NetworkMonitor {
  private currentStatus: NetworkStatus = 'unknown'
  private isInitialized: boolean = false
  private callbacks: Set<NetworkStatusChangeCallback> = new Set()
  private networkType: NetworkType = 'unknown'

  /**
   * 初始化网络监听
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) return

    const savedMetadata = getSyncMetadata()
    this.currentStatus = savedMetadata.networkStatus

    try {
      const res = await Taro.getNetworkType()
      this.networkType = res.networkType as NetworkType
      this.currentStatus = this.networkType === 'none' ? 'offline' : 'online'

      saveSyncMetadata({ networkStatus: this.currentStatus })
    } catch (e) {
      console.warn('[network-monitor] 获取网络状态失败', e)
      this.currentStatus = 'unknown'
    }

    this.startListening()

    this.isInitialized = true
  }

  /**
   * 开始监听网络状态变化
   */
  private startListening(): void {
    try {
      Taro.onNetworkStatusChange((res) => {
        const previousStatus = this.currentStatus
        this.networkType = res.networkType as NetworkType
        this.currentStatus = res.isConnected ? 'online' : 'offline'

        saveSyncMetadata({ networkStatus: this.currentStatus })

        this.notifyCallbacks(this.currentStatus, previousStatus)

        if (previousStatus === 'offline' && this.currentStatus === 'online') {
          this.onNetworkRecovered()
        }
      })
    } catch (e) {
      console.error('[network-monitor] 启动网络监听失败', e)
    }
  }

  /**
   * 网络恢复回调
   */
  private onNetworkRecovered(): void {
    console.log('[network-monitor] 网络已恢复，准备同步队列')

    const event = new CustomEvent('network-recovered', {
      detail: { timestamp: Date.now() },
    })
    window.dispatchEvent(event)
  }

  /**
   * 注册网络状态变化回调
   */
  onStatusChange(callback: NetworkStatusChangeCallback): () => void {
    this.callbacks.add(callback)
    return () => this.callbacks.delete(callback)
  }

  /**
   * 通知所有回调
   */
  private notifyCallbacks(status: NetworkStatus, previousStatus: NetworkStatus): void {
    for (const callback of this.callbacks) {
      try {
        callback(status, previousStatus)
      } catch (e) {
        console.error('[network-monitor] 回调执行失败', e)
      }
    }
  }

  /**
   * 获取当前网络状态
   */
  getCurrentStatus(): NetworkStatus {
    return this.currentStatus
  }

  /**
   * 获取当前网络类型
   */
  getNetworkType(): NetworkType {
    return this.networkType
  }

  /**
   * 检查是否在线
   */
  isOnline(): boolean {
    return this.currentStatus === 'online'
  }

  /**
   * 检查是否离线
   */
  isOffline(): boolean {
    return this.currentStatus === 'offline'
  }

  /**
   * 手动检查网络状态
   * 用于在关键操作前确认网络状态
   */
  async checkNetworkStatus(): Promise<NetworkStatus> {
    try {
      const res = await Taro.getNetworkType()
      this.networkType = res.networkType as NetworkType
      const newStatus = this.networkType === 'none' ? 'offline' : 'online'

      if (newStatus !== this.currentStatus) {
        const previousStatus = this.currentStatus
        this.currentStatus = newStatus
        saveSyncMetadata({ networkStatus: this.currentStatus })
        this.notifyCallbacks(this.currentStatus, previousStatus)

        if (previousStatus === 'offline' && this.currentStatus === 'online') {
          this.onNetworkRecovered()
        }
      }

      return this.currentStatus
    } catch (e) {
      console.warn('[network-monitor] 手动检查网络状态失败', e)
      return this.currentStatus
    }
  }

  /**
   * 停止监听
   */
  destroy(): void {
    try {
      Taro.offNetworkStatusChange(() => {})
    } catch (e) {
      console.warn('[network-monitor] 停止监听失败', e)
    }
    this.callbacks.clear()
    this.isInitialized = false
  }
}

/**
 * 全局单例网络监视器
 */
export const networkMonitor = new NetworkMonitor()

/**
 * 初始化网络监听
 * 应该在应用启动时调用
 */
export async function initializeNetworkMonitor(): Promise<void> {
  await networkMonitor.initialize()
}

/**
 * 等待网络恢复
 * 用于在需要网络的操作前等待
 */
export function waitForNetworkRecovery(timeout: number = 30000): Promise<boolean> {
  return new Promise((resolve) => {
    if (networkMonitor.isOnline()) {
      resolve(true)
      return
    }

    const timer = setTimeout(() => {
      cleanup()
      resolve(false)
    }, timeout)

    const cleanup = networkMonitor.onStatusChange((status) => {
      if (status === 'online') {
        clearTimeout(timer)
        cleanup()
        resolve(true)
      }
    })
  })
}

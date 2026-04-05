/**
 * Result 页面状态插画 - Goodnotes 墨水线条风格
 *
 * 设计原则：
 * - 纯线条，无填充
 * - 线条色: #c0c0c0 (灰线) / #030213 (墨线)
 * - 线条粗: 2rpx，圆角端点
 * - 尺寸: 120rpx × 120rpx（不抢占内容空间）
 */

import { View } from '@tarojs/components'
import './index.scss'

/** === Loading: 纸页轮廓 + 脉冲动画 === */
export function LoadingIllustration() {
  return (
    <View className='illustration-container loading-illustration'>
      {/* 纸页轮廓 */}
      <svg width='120rpx' height='120rpx' viewBox='0 0 100 100' fill='none'>
        {/* 纸页 */}
        <rect x='20' y='12' width='55' height='72' rx='4' stroke='#c0c0c0' strokeWidth='2' />
        {/* 折角 */}
        <path d='M60 12 L75 27 L60 27 Z' stroke='#c0c0c0' strokeWidth='2' fill='none' />
        {/* 文字行 (脉冲动画) — 模拟真实文章长度变化 */}
        <line x1='28' y1='34' x2='62' y2='34' stroke='#c0c0c0' strokeWidth='2' strokeLinecap='round' className='skeleton-line delay-1' />
        <line x1='28' y1='46' x2='54' y2='46' stroke='#c0c0c0' strokeWidth='2' strokeLinecap='round' className='skeleton-line delay-2' />
        <line x1='28' y1='58' x2='68' y2='58' stroke='#c0c0c0' strokeWidth='2' strokeLinecap='round' className='skeleton-line delay-3' />
        <line x1='28' y1='70' x2='48' y2='70' stroke='#c0c0c0' strokeWidth='2' strokeLinecap='round' className='skeleton-line delay-4' />
      </svg>
    </View>
  )
}

/** === Error: 纸页 + 断裂链条 === */
export function ErrorIllustration() {
  return (
    <View className='illustration-container error-illustration'>
      <svg width='120rpx' height='120rpx' viewBox='0 0 100 100' fill='none'>
        {/* 纸页 */}
        <rect x='20' y='15' width='55' height='70' rx='4' stroke='#c0c0c0' strokeWidth='2' fill='none' />
        {/* 折角 */}
        <path d='M60 15 L75 30 L60 30 Z' stroke='#c0c0c0' strokeWidth='2' fill='none' />
        {/* 正常文字线 */}
        <line x1='28' y1='38' x2='55' y2='38' stroke='#c0c0c0' strokeWidth='2' strokeLinecap='round' />
        <line x1='28' y1='50' x2='50' y2='50' stroke='#c0c0c0' strokeWidth='2' strokeLinecap='round' />
        {/* 断裂链 - 右侧 */}
        <path d='M78 32 C82 37, 78 44, 82 49' stroke='#c0c0c0' strokeWidth='2' strokeLinecap='round' fill='none' />
        {/* 断裂标记 — 圆点表示"中断"而非"破坏"，更低焦虑 */}
        <circle cx='78' cy='58' r='3' stroke='#c0c0c0' strokeWidth='2' fill='none' />
        <line x1='74' y1='66' x2='82' y2='66' stroke='#c0c0c0' strokeWidth='2' strokeLinecap='round' />
      </svg>
    </View>
  )
}

/** === Empty: 空白纸页 === */
export function EmptyIllustration() {
  return (
    <View className='illustration-container empty-illustration'>
      <svg width='120rpx' height='120rpx' viewBox='0 0 100 100' fill='none'>
        {/* 纸页 */}
        <rect x='25' y='18' width='50' height='65' rx='4' stroke='#c0c0c0' strokeWidth='2' fill='none' />
        {/* 折角 */}
        <path d='M58 18 L73 33 L58 33 Z' stroke='#c0c0c0' strokeWidth='2' fill='none' />
        {/* 极少文字线，表达"几乎空白" */}
        <line x1='33' y1='40' x2='55' y2='40' stroke='#d8d8d8' strokeWidth='2' strokeLinecap='round' />
        {/* 横线纹暗示"可书写" */}
        <line x1='33' y1='52' x2='67' y2='52' stroke='#e8e8e8' strokeWidth='1.5' strokeLinecap='round' strokeDasharray='3 3' />
        <line x1='33' y1='60' x2='67' y2='60' stroke='#e8e8e8' strokeWidth='1.5' strokeLinecap='round' strokeDasharray='3 3' />
        <line x1='33' y1='68' x2='67' y2='68' stroke='#e8e8e8' strokeWidth='1.5' strokeLinecap='round' strokeDasharray='3 3' />
      </svg>
    </View>
  )
}

import { View } from '@tarojs/components'
import './index.scss'

/**
 * 轻量级 Lucide 图标组件 - 专为小程序优化
 * 避免引入庞大的 lucide-react 库导致的注入超时
 */

const ICON_PATHS = {
  home: 'm3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z',
  history: 'M12 8v4l3 3m6-3a9 9 0 1 1-18 0 9 9 0 0 1 18 0z',
  user: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2',
  plus: 'M12 5v14M5 12h14',
  chevronLeft: 'm15 18-6-6 6-6',
  book: 'M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2zM22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z',
  languages: 'm5 8 6 6m-7 0 6-6 2-3M2 5h12M7 2h1m14 20-5-10-5 10m2-4h6',
  layers: 'm12 2 2 7 12 12 22 7 12 2M2 17 12 22 22 17M2 12 12 17 22 12',
  sparkles: 'm12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z'
}

interface LucideIconProps {
  name: keyof typeof ICON_PATHS;
  size?: number;
  color?: string;
  strokeWidth?: number;
  className?: string;
}

export default function LucideIcon({ name, size = 24, color = 'currentColor', strokeWidth = 2, className = '' }: LucideIconProps) {
  const path = ICON_PATHS[name]
  
  if (!path) return null

  // 使用 mask-image 方案，这是小程序中最轻量且支持动态变色的方案
  return (
    <View 
      className={`lucide-icon icon-${name} ${className}`}
      style={{
        width: `${size}px`,
        height: `${size}px`,
        backgroundColor: color,
        WebkitMaskImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='${strokeWidth}' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='${path.replace(/ /g, '%20')}'/%3E%3C/svg%3E")`,
        WebkitMaskRepeat: 'no-repeat',
        WebkitMaskPosition: 'center',
        WebkitMaskSize: 'contain'
      }}
    />
  )
}

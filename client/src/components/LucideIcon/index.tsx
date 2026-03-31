import { Text } from '@tarojs/components'
import './index.scss'

/**
 * 轻量级图标组件 - 专为小程序优化
 * 使用 Unicode 符号渲染，确保 100% 兼容
 */

interface LucideIconProps {
  name: string
  size?: number
  color?: string
  strokeWidth?: number
  className?: string
}

// Unicode 符号映射
const ICON_MAP: Record<string, string> = {
  // 导航
  chevronLeft: '\u276E',     // ◪ 左箭头
  chevronRight: '\u276F',   // ▷ 右箭头
  chevronDown: '\u2304',     // ▼ 下箭头
  chevronUp: '\u2303',       // ▲ 上箭头

  // 操作
  plus: '\u002B',            // + 加号
  x: '\u2715',               // ✕ 关闭
  check: '\u2713',           // ✓ 对勾

  // 物体
  book: '\u{1F4D6}',         // 📖 书本
  bookOpen: '\u{1F4D8}',     // 📘 打开的书
  bookmark: '\u{1F516}',     // 🔖 书签
  heart: '\u2665',           // ♥ 心形
  thumbsUp: '\u{1F44D}',     // 👍 点赞
  sparkles: '\u2728',        // ✨ 闪光
  star: '\u2605',            // ★ 星星

  // 状态
  home: '\u2302',            // ⌂ 主页
  user: '\u{1F464}',          // 👤 用户
  history: '\u{1F551}',      // 🕐 时钟
  settings: '\u2699',        // ⚙ 齿轮
  volume2: '\u{1F50A}',      // 🔊 音量

  // 其他
  languages: '\u{1F310}',   // 🌐 语言
  layers: '\u{1F3CB}',        // 🏋 图层
  arrowRight: '\u2192',      // → 右箭头
  arrowLeft: '\u2190',       // ← 左箭头
}

// 备用降级方案：如果 name 不存在，使用简单符号
const FALLBACK_ICONS: Record<string, string> = {
  chevronLeft: '<',
  chevronRight: '>',
  chevronDown: 'v',
  chevronUp: '^',
  plus: '+',
  x: '×',
  book: '📖',
  bookOpen: '📘',
  bookmark: '🔖',
  heart: '♥',
  thumbsUp: '👍',
  sparkles: '✨',
  star: '★',
  home: '⌂',
  user: '👤',
  history: '🕐',
  settings: '⚙',
  volume2: '🔊',
  languages: '🌐',
  layers: '📑',
  arrowRight: '→',
  arrowLeft: '←',
}

export default function LucideIcon({ name, size = 24, color = '#000', className = '' }: LucideIconProps) {
  const iconChar = ICON_MAP[name] || FALLBACK_ICONS[name] || '•'

  return (
    <Text
      className={`lucide-icon ${className}`}
      style={{
        fontSize: `${size}px`,
        color: color,
        lineHeight: 1,
      }}
    >
      {iconChar}
    </Text>
  )
}

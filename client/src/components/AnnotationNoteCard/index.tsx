import { View, Text } from '@tarojs/components'
import LucideIcon from '../LucideIcon'
import './index.scss'

export interface AnnotationNoteCardProps {
  title: string
  isSaved?: boolean
  onSaveToggle?: () => void
  onHelpful?: () => void
  onInaccurate?: () => void
  onFeedback?: () => void
  children?: React.ReactNode
  className?: string
}

export default function AnnotationNoteCard({
  title,
  isSaved,
  onSaveToggle,
  onHelpful,
  onInaccurate,
  onFeedback,
  children,
  className = ''
}: AnnotationNoteCardProps) {
  return (
    <View className={`annotation-note-card ${className}`}>
      {/* Header */}
      <View className="note-card-header">
        <Text className="note-card-title">{title}</Text>
        <View className="note-card-save" onClick={onSaveToggle}>
          <LucideIcon 
            name={isSaved ? "bookmarkCheck" : "bookmark"} 
            size={20} 
            color={isSaved ? "var(--color-ink)" : "var(--reader-muted)"} 
          />
        </View>
      </View>

      {/* Content Body */}
      <View className="note-card-body">
        {children}
      </View>

      {/* Feedback Bar */}
      <View className="note-card-footer">
        <View className="note-card-feedback-actions">
          <View className="feedback-action" onClick={onHelpful}>
            <LucideIcon name="thumbsUp" size={16} color="var(--reader-muted)" />
            <Text className="feedback-text">有帮助</Text>
          </View>
          <View className="feedback-action" onClick={onInaccurate}>
            <LucideIcon name="thumbsDown" size={16} color="var(--reader-muted)" />
            <Text className="feedback-text">不准确</Text>
          </View>
          <View className="feedback-action" onClick={onFeedback}>
            <LucideIcon name="messageSquare" size={16} color="var(--reader-muted)" />
            <Text className="feedback-text">反馈</Text>
          </View>
        </View>
      </View>
    </View>
  )
}

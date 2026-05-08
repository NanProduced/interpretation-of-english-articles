import { useState } from 'react'
import { View, Text } from '@tarojs/components'
import LucideIcon from '../LucideIcon'
import type { ContentSummaryModel, ContentSummaryCompleteness } from '../../types/view/render-scene.vm'
import './index.scss'

interface ContentSummaryCardProps {
  summary: ContentSummaryModel
}

const COMPLETENESS_CONFIG: Record<ContentSummaryCompleteness, { label: string; color: string }> = {
  full: { label: '完整概要', color: 'var(--term-accent)' },
  partial: { label: '部分概要', color: 'var(--logic-accent)' },
  minimal: { label: '片段概要', color: 'var(--text-muted)' },
}

const SECTION_CONFIG = [
  { key: 'researchQuestion', label: '研究问题', icon: 'help-circle' },
  { key: 'methodology', label: '研究方法', icon: 'microscope' },
  { key: 'keyFindings', label: '核心发现', icon: 'lightbulb' },
  { key: 'limitations', label: '研究局限', icon: 'shield-alert' },
] as const

export default function ContentSummaryCard({ summary }: ContentSummaryCardProps) {
  const [expanded, setExpanded] = useState(false)  // Academic: 默认折叠，避免抢占首屏
  const completeness = COMPLETENESS_CONFIG[summary.completeness]

  const hasStructuredSections =
    summary.researchQuestion ||
    summary.methodology ||
    (summary.keyFindings && summary.keyFindings.length > 0) ||
    (summary.limitations && summary.limitations.length > 0)

  return (
    <View className={`content-summary-card ${expanded ? 'expanded' : 'collapsed'}`}>
      <View className='summary-header' onClick={() => setExpanded(!expanded)}>
        <View className='summary-header-main'>
          <LucideIcon name='file-text' size={16} color='var(--logic-accent)' />
          <Text className='summary-title'>内容概要</Text>
          <View className='completeness-tag' style={{ color: completeness.color, borderColor: completeness.color }}>
            <Text className='completeness-text'>{completeness.label}</Text>
          </View>
        </View>
        <View className='summary-toggle'>
          <LucideIcon
            name={expanded ? 'chevron-up' : 'chevron-down'}
            size={16}
            color='var(--text-muted)'
          />
        </View>
      </View>

      <View className={`summary-body ${expanded ? 'show' : 'hide'}`}>
        <View className='overview-section'>
          <Text className='overview-text'>{summary.overview}</Text>
        </View>

        {hasStructuredSections && (
          <View className='structured-sections'>
            {summary.researchQuestion && (
              <View className='structured-item'>
                <View className='structured-label'>
                  <LucideIcon name='help-circle' size={12} color='var(--term-accent)' />
                  <Text className='structured-label-text'>研究问题</Text>
                </View>
                <Text className='structured-content'>{summary.researchQuestion}</Text>
              </View>
            )}

            {summary.methodology && (
              <View className='structured-item'>
                <View className='structured-label'>
                  <LucideIcon name='microscope' size={12} color='var(--term-accent)' />
                  <Text className='structured-label-text'>研究方法</Text>
                </View>
                <Text className='structured-content'>{summary.methodology}</Text>
              </View>
            )}

            {summary.keyFindings && summary.keyFindings.length > 0 && (
              <View className='structured-item'>
                <View className='structured-label'>
                  <LucideIcon name='lightbulb' size={12} color='var(--logic-accent)' />
                  <Text className='structured-label-text'>核心发现</Text>
                </View>
                <View className='findings-list'>
                  {summary.keyFindings.map((finding, idx) => (
                    <View key={idx} className='finding-item'>
                      <View className='finding-dot' />
                      <Text className='finding-text'>{finding}</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}

            {summary.limitations && summary.limitations.length > 0 && (
              <View className='structured-item'>
                <View className='structured-label'>
                  <LucideIcon name='shield-alert' size={12} color='var(--logic-accent)' />
                  <Text className='structured-label-text'>研究局限</Text>
                </View>
                <View className='findings-list'>
                  {summary.limitations.map((item, idx) => (
                    <View key={idx} className='finding-item'>
                      <View className='finding-dot is-limitation' />
                      <Text className='finding-text'>{item}</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}
          </View>
        )}
      </View>
    </View>
  )
}

import { useState } from 'react'
import { View, Text } from '@tarojs/components'
import LucideIcon from '../LucideIcon'
import { DocumentSummaryModel } from '../../types/view/render-scene.vm'
import './index.scss'

export interface AcademicDocumentSummaryProps {
  summary: DocumentSummaryModel
}

export default function AcademicDocumentSummary({ summary }: AcademicDocumentSummaryProps) {
  const [isExpanded, setIsExpanded] = useState(true)

  const hasContent = 
    summary.researchProblemZh || 
    summary.methodologyZh || 
    summary.keyFindingsZh || 
    summary.limitationsZh || 
    summary.overallSignificanceZh

  if (!hasContent) return null

  const sections = [
    {
      key: 'researchProblem',
      label: '研究问题',
      icon: 'help-circle',
      content: summary.researchProblemZh,
      color: 'var(--summary-research-accent)',
    },
    {
      key: 'methodology',
      label: '研究方法',
      icon: 'wrench',
      content: summary.methodologyZh,
      color: 'var(--summary-method-accent)',
    },
    {
      key: 'keyFindings',
      label: '核心发现',
      icon: 'lightbulb',
      content: summary.keyFindingsZh,
      color: 'var(--summary-finding-accent)',
    },
    {
      key: 'limitations',
      label: '研究限制',
      icon: 'alert-triangle',
      content: summary.limitationsZh,
      color: 'var(--summary-limit-accent)',
    },
    {
      key: 'overallSignificance',
      label: '整体意义',
      icon: 'award',
      content: summary.overallSignificanceZh,
      color: 'var(--summary-significance-accent)',
    },
  ].filter(s => s.content)

  return (
    <View className='academic-document-summary'>
      <View className='summary-header' onClick={() => setIsExpanded(!isExpanded)}>
        <View className='header-main'>
          <LucideIcon name='file-text' size={20} color='var(--summary-header-accent)' />
          <Text className='header-title'>全文摘要</Text>
        </View>
        <LucideIcon 
          name={isExpanded ? 'chevron-up' : 'chevron-down'} 
          size={18} 
          color='var(--text-muted)' 
        />
      </View>

      {isExpanded && (
        <View className='summary-content'>
          {sections.map((section, idx) => (
            <View key={section.key} className='summary-section' style={{ borderLeftColor: section.color }}>
              <View className='section-header'>
                <LucideIcon name={section.icon} size={14} color={section.color} />
                <Text className='section-label' style={{ color: section.color }}>{section.label}</Text>
              </View>
              <Text className='section-content'>{section.content}</Text>
            </View>
          ))}
        </View>
      )}
    </View>
  )
}

import { useState } from 'react'
import { View, Text } from '@tarojs/components'
import LucideIcon from '../LucideIcon'
import { ParagraphRoleModel } from '../../types/view/render-scene.vm'
import './index.scss'

export interface AcademicParagraphRoleProps {
  role: ParagraphRoleModel
  order: number
}

const ROLE_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
  definition: { icon: 'book-open', color: 'var(--role-definition-accent)', label: '定义' },
  background: { icon: 'layers', color: 'var(--role-background-accent)', label: '背景' },
  problem_statement: { icon: 'alert-circle', color: 'var(--role-problem-accent)', label: '问题提出' },
  methodology: { icon: 'wrench', color: 'var(--role-method-accent)', label: '方法' },
  evidence: { icon: 'search', color: 'var(--role-evidence-accent)', label: '证据' },
  result: { icon: 'check-circle', color: 'var(--role-result-accent)', label: '结果' },
  limitation: { icon: 'alert-triangle', color: 'var(--role-limit-accent)', label: '限制' },
  transition: { icon: 'arrow-right', color: 'var(--role-transition-accent)', label: '过渡' },
  discussion: { icon: 'message-circle', color: 'var(--role-discussion-accent)', label: '讨论' },
  conclusion: { icon: 'flag', color: 'var(--role-conclusion-accent)', label: '结论' },
}

export default function AcademicParagraphRole({ role, order }: AcademicParagraphRoleProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const config = ROLE_CONFIG[role.role] || ROLE_CONFIG.background

  return (
    <View className='academic-paragraph-role' style={{ borderLeftColor: config.color }}>
      <View className='role-header' onClick={() => setIsExpanded(!isExpanded)}>
        <View className='header-main'>
          <View className='order-badge' style={{ backgroundColor: config.color }}>
            <Text className='order-text'>{order}</Text>
          </View>
          <LucideIcon name={config.icon} size={16} color={config.color} />
          <Text className='role-label' style={{ color: config.color }}>{role.label}</Text>
        </View>
        <LucideIcon 
          name={isExpanded ? 'chevron-up' : 'chevron-down'} 
          size={16} 
          color='var(--text-muted)' 
        />
      </View>

      {isExpanded && (
        <View className='role-content'>
          <View className='summary-section'>
            <Text className='section-label'>段落摘要</Text>
            <Text className='section-content'>{role.summaryZh}</Text>
          </View>
          {role.keyClaim && (
            <View className='claim-section'>
              <Text className='section-label'>核心主张</Text>
              <Text className='section-content claim'>{role.keyClaim}</Text>
            </View>
          )}
        </View>
      )}
    </View>
  )
}

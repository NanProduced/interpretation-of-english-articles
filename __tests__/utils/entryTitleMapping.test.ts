/**
 * entryTitleMapping 工具函数单元测试
 * 
 * 测试覆盖：
 * - 各类型枚举值的正确映射
 * - 大小写不敏感匹配
 * - 边界情况处理 (空值、未知值)
 * - 批量映射功能
 */

import { getMappedEntryTitle, batchMapEntries, LOGIC_TITLE_MAP, INTERPRETATION_TITLE_MAP, GRAMMAR_TITLE_MAP } from '../../../src/utils/entryTitleMapping'

describe('getMappedEntryTitle', () => {
  
  // ============================================================
  // Logic Note 类型测试
  // ============================================================
  describe('logic_note 类型', () => {
    test('应正确映射 elaboration 为详细阐述', () => {
      expect(getMappedEntryTitle('logic_note', 'elaboration', '')).toBe('详细阐述')
    })
    
    test('应正确映射 contrast 为对比论证', () => {
      expect(getMappedEntryTitle('logic_note', 'contrast', '')).toBe('对比论证')
    })
    
    test('应正确映射 concession 为让步转折', () => {
      expect(getMappedEntryTitle('logic_note', 'concession', '')).toBe('让步转折')
    })
    
    test('应对大小写不敏感 - ELABORATION', () => {
      expect(getMappedEntryTitle('logic_note', 'ELABORATION', '')).toBe('详细阐述')
    })
    
    test('应对大小写不敏感 - Contrast', () => {
      expect(getMappedEntryTitle('logic_note', 'Contrast', '')).toBe('对比论证')
    })
    
    test('应处理首尾空格 - "  elaboration  "', () => {
      expect(getMappedEntryTitle('logic_note', '  elaboration  ', '')).toBe('详细阐述')
    })
    
    test('未知枚举值应返回默认文案', () => {
      expect(getMappedEntryTitle('logic_note', 'unknown_logic_type', '')).toBe('逻辑关系')
    })
    
    test('空字符串应返回 fallback', () => {
      expect(getMappedEntryTitle('logic_note', '', '默认标签')).toBe('默认标签')
    })
    
    test('undefined 应返回 fallback', () => {
      expect(getMappedEntryTitle('logic_note', undefined, '默认标签')).toBe('默认标签')
    })
  })
  
  // ============================================================
  // Interpretation Note 类型测试
  // ============================================================
  describe('interpretation_note 类型', () => {
    test('应正确映射 disambiguation 为消除歧义', () => {
      expect(getMappedEntryTitle('interpretation_note', 'disambiguation', '')).toBe('消除歧义')
    })
    
    test('应正确映射 decontextualization 为语境还原', () => {
      expect(getMappedEntryTitle('interpretation_note', 'decontextualization', '')).toBe('语境还原')
    })
    
    test('应正确映射 clarification 为澄清说明', () => {
      expect(getMappedEntryTitle('interpretation_note', 'clarification', '')).toBe('澄清说明')
    })
    
    test('应正确映射 implication 为隐含意义', () => {
      expect(getMappedEntryTitle('interpretation_note', 'implication', '')).toBe('隐含意义')
    })
    
    test('未知枚举值应返回默认文案', () => {
      expect(getMappedEntryTitle('interpretation_note', 'unknown_type', '')).toBe('解释说明')
    })
  })
  
  // ============================================================
  // Grammar Note 类型测试
  // ============================================================
  describe('grammar_note 类型', () => {
    test('应正确映射 passive_voice 为被动语态', () => {
      expect(getMappedEntryTitle('grammar_note', 'passive_voice', '')).toBe('被动语态')
    })
    
    test('应正确映射 subjunctive_mood 为虚拟语气', () => {
      expect(getMappedEntryTitle('grammar_note', 'subjunctive_mood', '')).toBe('虚拟语气')
    })
    
    test('应正确映射 inversion 为倒装结构', () => {
      expect(getMappedEntryTitle('grammar_note', 'inversion', '')).toBe('倒装结构')
    })
    
    test('未知枚举值应返回默认文案', () => {
      expect(getMappedEntryTitle('grammar_note', 'unknown_grammar', '')).toBe('语法要点')
    })
  })
  
  // ============================================================
  // Term Note 类型测试（特殊行为）
  // ============================================================
  describe('term_note 类型', () => {
    test('已分类术语应翻译 - technical_term', () => {
      expect(getMappedEntryTitle('term_note', 'technical_term', '')).toBe('专业术语')
    })
    
    test('已分类术语应翻译 - domain_jargon', () => {
      expect(getMappedEntryTitle('term_note', 'domain_jargon', '')).toBe('领域行话')
    })
    
    test('具体术语名称应保留原文 - ecocentrism', () => {
      expect(getMappedEntryTitle('term_note', 'ecocentrism', '')).toBe('ecocentrism')
    })
    
    test('具体术语名称应保留原文 - sociocentrists', () => {
      expect(getMappedEntryTitle('term_note', 'sociocentrists', '')).toBe('sociocentrists')
    })
    
    test('空值应返回 fallback', () => {
      expect(getMappedEntryTitle('term_note', '', '术语标注')).toBe('术语标注')
    })
  })
  
  // ============================================================
  // Content Summary 类型测试
  // ============================================================
  describe('content_summary 类型', () => {
    test('应正确映射 overview 为内容概述', () => {
      expect(getMappedEntryTitle('content_summary', 'overview', '')).toBe('内容概述')
    })
    
    test('未知类型应返回默认文案', () => {
      expect(getMappedEntryTitle('content_summary', 'unknown_summary', '')).toBe('内容概要')
    })
  })
  
  // ============================================================
  // 边界情况和错误处理
  // ============================================================
  describe('边界情况', () => {
    test('未知 entryType 应返回原标题或 fallback', () => {
      const result = getMappedEntryTitle('unknown_type', 'some_title', 'fallback')
      expect(result).toBe('some_title')
    })
    
    test('未知 entryType + 空标题应返回 fallback', () => {
      expect(getMappedEntryTitle('unknown_type', '', 'fallback')).toBe('fallback')
    })
    
    test('特殊字符不应影响映射', () => {
      expect(getMappedEntryTitle('logic_note', 'elaboration-with-dash', '默认')).toBe('逻辑关系')
    })
  })
})

// ============================================================
// batchMapEntries 函数测试
// ============================================================
describe('batchMapEntries', () => {
  test('应批量映射多个条目', () => {
    const entries = [
      { entryType: 'logic_note', title: 'elaboration', label: '' },
      { entryType: 'interpretation_note', title: 'disambiguation', label: '' },
      { entryType: 'grammar_note', title: 'passive_voice', label: '' },
    ]
    
    const result = batchMapEntries(entries)
    
    expect(result[0].title).toBe('详细阐述')
    expect(result[1].title).toBe('消除歧义')
    expect(result[2].title).toBe('被动语态')
  })
  
  test('应保留条目的其他属性不变', () => {
    const entries = [
      { 
        entryType: 'logic_note', 
        title: 'contrast', 
        label: '',
        id: 'test-123',
        content: 'some content'
      },
    ]
    
    const result = batchMapEntries(entries)
    
    expect(result[0].id).toBe('test-123')
    expect(result[0].content).toBe('some content')
    expect(result[0].title).toBe('对比论证')
  })
  
    test('应处理空数组', () => {
    const result = batchMapEntries([])
    expect(result).toEqual([])
  })
})

// ============================================================
// 映射表完整性检查
// ============================================================
describe('映射表完整性', () => {
  test('LOGIC_TITLE_MAP 应包含所有预期的键', () => {
    const expectedKeys = [
      'elaboration', 'contrast', 'concession', 'rebuttal',
      'causation', 'sequence', 'addition', 'summary',
      'example', 'evidence', 'authority', 'analogy'
    ]
    
    expectedKeys.forEach(key => {
      expect(LOGIC_TITLE_MAP[key]).toBeDefined()
      expect(typeof LOGIC_TITLE_MAP[key]).toBe('string')
      expect(LOGIC_TITLE_MAP[key].length).toBeGreaterThan(0)
    })
  })
  
  test('INTERPRETATION_TITLE_MAP 应包含所有预期的键', () => {
    const expectedKeys = [
      'disambiguation', 'decontextualization', 'clarification',
      'implication', 'reformulation', 'connection',
      'cultural_context', 'historical_context', 'domain_context'
    ]
    
    expectedKeys.forEach(key => {
      expect(INTERPRETATION_TITLE_MAP[key]).toBeDefined()
      expect(typeof INTERPRETATION_TITLE_MAP[key]).toBe('string')
    })
  })
  
  test('GRAMMAR_TITLE_MAP 应包含所有预期的键', () => {
    const expectedKeys = [
      'passive_voice', 'active_voice',
      'subjunctive_mood', 'conditional_mood', 'imperative_mood',
      'inversion', 'emphasis', 'cleft_sentence', 'existential_there',
      'relative_clause', 'noun_clause', 'adverbial_clause',
      'infinitive', 'gerund', 'participle'
    ]
    
    expectedKeys.forEach(key => {
      expect(GRAMMAR_TITLE_MAP[key]).toBeDefined()
      expect(typeof GRAMMAR_TITLE_MAP[key]).toBe('string')
    })
  })
})

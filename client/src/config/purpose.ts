export type ReadingGoal = 'exam' | 'academic' | 'daily';
export type ServerReadingGoal = 'exam' | 'daily_reading' | 'academic';
export type ReadingVariant =
  | 'gaokao'
  | 'cet'
  | 'kaoyan'
  | 'tem'
  | 'ielts_toefl'
  | 'beginner_reading'
  | 'intermediate_reading'
  | 'intensive_reading'
  | 'academic_general';

export interface VariantOption {
  value: ReadingVariant; // This matches the reading_variant expected by the server
  label: string;
  description?: string;
}

export interface PurposeOption {
  label: string;
  description: string;
  icon: string;
  serverGoal: ServerReadingGoal; // This matches the reading_goal expected by the server
  defaultVariant: ReadingVariant;
  variants?: VariantOption[];
}

export const READING_CONFIG_MAP: Record<ReadingGoal, PurposeOption> = {
  exam: {
    label: '考试备考',
    description: '深度解析真题句式与核心考点',
    icon: 'graduationCap',
    serverGoal: 'exam',
    defaultVariant: 'cet',
    variants: [
      { value: 'gaokao', label: '高考英语', description: '侧重基础语法与完形填空核心句式' },
      { value: 'cet', label: '四六级 (CET-4/6)', description: '精准捕捉考试常用短语与复合句分析' },
      { value: 'kaoyan', label: '考研英语', description: '攻克长难句，还原学术化命题逻辑' },
      { value: 'tem', label: '专业英语 (TEM4/8)', description: '对标专四/专八，强化翻译与改错思维' },
      { value: 'ielts_toefl', label: '雅思/托福', description: '专注于批判性思维与高阶同义替换' }
    ]
  },
  daily: {
    label: '日常阅读',
    description: '在流畅阅读中自然提升积累',
    icon: 'coffee',
    serverGoal: 'daily_reading',
    defaultVariant: 'intermediate_reading',
    variants: [
      { value: 'beginner_reading', label: '入门难度', description: '适合初学者，重点在于词法拆解与直译' },
      { value: 'intermediate_reading', label: '进阶难度', description: '中级进阶，侧重上下文联系与自然翻译' },
      { value: 'intensive_reading', label: '精读练习', description: '逐字逐句深度剖析，适合精读训练' }
    ]
  },
  academic: {
    label: '学术文献',
    description: '识别极其复杂的从句嵌套，辅助科研文献深度理解',
    icon: 'bookOpen',
    serverGoal: 'academic',
    defaultVariant: 'academic_general'
  }
};

export const SERVER_GOAL_TO_UI_GOAL: Record<string, ReadingGoal> = {
  exam: 'exam',
  daily_reading: 'daily',
  academic: 'academic',
};

const LEGACY_VARIANT_ALIASES: Record<string, ReadingVariant> = {
  cet4: 'cet',
  cet6: 'cet',
  kaoyan: 'kaoyan',
  gre: 'kaoyan',
  tem: 'tem',
  ielts: 'ielts_toefl',
  toefl: 'ielts_toefl',
  beginner: 'beginner_reading',
  intermediate: 'intermediate_reading',
  advanced: 'intensive_reading',
};

export const normalizeVariantForGoal = (
  goal: ReadingGoal,
  variant?: string | null
): ReadingVariant => {
  const config = READING_CONFIG_MAP[goal];
  const candidate =
    (variant && LEGACY_VARIANT_ALIASES[variant]) ||
    (variant as ReadingVariant | null) ||
    config.defaultVariant;
  const allowedVariants = config.variants?.map((item) => item.value) || [config.defaultVariant];
  return allowedVariants.includes(candidate) ? candidate : config.defaultVariant;
};

/**
 * 获取显示的标签文本
 */
export const getDisplayLabel = (goal: ReadingGoal, variant?: string | null) => {
  const config = READING_CONFIG_MAP[goal];
  if (!config) return '未知模式';

  const currentVariant = normalizeVariantForGoal(goal, variant);
  if (!config.variants) return config.label;

  const variantLabel = config.variants.find(v => v.value === currentVariant)?.label;
  return variantLabel ? `${config.label} (${variantLabel})` : config.label;
};

/**
 * 获取 API 参数
 */
export const getApiParams = (goal: ReadingGoal, variant?: string | null) => {
  const config = READING_CONFIG_MAP[goal];
  return {
    reading_goal: config.serverGoal,
    reading_variant: normalizeVariantForGoal(goal, variant)
  };
};

export const normalizeServerAnalyzeParams = (
  readingGoal: string,
  readingVariant?: string | null
) => {
  const goal = SERVER_GOAL_TO_UI_GOAL[readingGoal] || 'daily';
  return getApiParams(goal, readingVariant);
};

/**
 * 从服务器返回的原始字段获取友好的显示文本
 */
export const getSafeDisplayLabel = (serverGoal: string, serverVariant?: string | null) => {
  // 兼容驼峰 (dailyReading -> daily_reading)
  const normalizedGoalKey = serverGoal.replace(/([A-Z])/g, "_$1").toLowerCase();
  
  const goal = SERVER_GOAL_TO_UI_GOAL[serverGoal] || SERVER_GOAL_TO_UI_GOAL[normalizedGoalKey] || 'daily';
  return getDisplayLabel(goal, serverVariant);
};

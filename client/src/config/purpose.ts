export type ReadingGoal = 'exam' | 'academic' | 'daily';
export type ServerReadingGoal = 'exam' | 'daily_reading' | 'academic';
export type ReadingVariant =
  | 'gaokao'
  | 'cet'
  | 'gre'
  | 'ielts_toefl'
  | 'beginner_reading'
  | 'intermediate_reading'
  | 'intensive_reading'
  | 'academic_general';

export interface VariantOption {
  value: ReadingVariant; // This matches the reading_variant expected by the server
  label: string;
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
    description: '针对专项考试优化',
    icon: 'graduationCap',
    serverGoal: 'exam',
    defaultVariant: 'cet',
    variants: [
      { value: 'gaokao', label: '高考英语' },
      { value: 'cet', label: '四六级 (CET-4/6)' },
      { value: 'gre', label: '考研/专业英语' },
      { value: 'ielts_toefl', label: '雅思/托福' }
    ]
  },
  daily: {
    label: '日常阅读',
    description: '平滑阅读体验',
    icon: 'coffee',
    serverGoal: 'daily_reading',
    defaultVariant: 'intermediate_reading',
    variants: [
      { value: 'beginner_reading', label: '入门难度' },
      { value: 'intermediate_reading', label: '进阶难度' },
      { value: 'intensive_reading', label: '精读练习' }
    ]
  },
  academic: {
    label: '学术文献',
    description: '严谨术语与结构分析',
    icon: 'bookOpen',
    serverGoal: 'academic',
    defaultVariant: 'academic_general'
  }
};

const LEGACY_VARIANT_ALIASES: Record<string, ReadingVariant> = {
  cet4: 'cet',
  cet6: 'cet',
  kaoyan: 'gre',
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

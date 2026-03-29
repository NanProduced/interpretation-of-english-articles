/**
 * AI 英语文章解读小程序 - 数据 Schema (v0.1.0-draft)
 * 映射自 docs/workflow/schema-v0-draft.md
 */

export interface Span {
  start: number;
  end: number;
}

export interface ArticleParagraph {
  paragraph_id: string;
  text: string;
  start: number;
  end: number;
  sentence_ids: string[];
}

export interface ArticleSentence {
  sentence_id: string;
  paragraph_id: string;
  text: string;
  start: number;
  end: number;
  difficulty_score: number;
  is_difficult: boolean;
}

export interface Article {
  title: string | null;
  language: string;
  source_type: string;
  source_text: string;
  render_text: string;
  paragraphs: ArticleParagraph[];
  sentences: ArticleSentence[];
}

export interface VocabularyAnnotation {
  annotation_id: string;
  type: 'vocabulary';
  surface: string;
  lemma: string;
  span: Span;
  sentence_id: string;
  phrase_type: 'word' | 'phrase';
  context_gloss_zh: string;
  short_explanation_zh: string;
  objective_level: 'basic' | 'intermediate' | 'advanced';
  priority: 'core' | 'expand' | 'reference';
  default_visible: boolean;
  exam_tags?: string[];
  scene_tags?: string[];
}

export interface GrammarPointAnnotation {
  annotation_id: string;
  type: 'grammar_point';
  sentence_id: string;
  span: Span;
  label: string;
  short_explanation_zh: string;
  objective_level: 'basic' | 'intermediate' | 'advanced';
  priority: 'core' | 'expand' | 'reference';
  default_visible: boolean;
}

export interface SentenceComponent {
  label: string;
  text: string;
  span: Span;
}

export interface SentenceComponentAnnotation {
  annotation_id: string;
  type: 'sentence_component';
  sentence_id: string;
  components: SentenceComponent[];
  objective_level: 'basic' | 'intermediate' | 'advanced';
  priority: 'core' | 'expand' | 'reference';
  default_visible: boolean;
}

export interface GrammarErrorAnnotation {
  annotation_id: string;
  type: 'error_flag';
  sentence_id: string;
  span: Span;
  label: string;
  short_explanation_zh: string;
  objective_level: 'basic' | 'intermediate' | 'advanced';
  priority: 'core' | 'expand' | 'reference';
  default_visible: boolean;
}

export type GrammarAnnotation =
  | GrammarPointAnnotation
  | SentenceComponentAnnotation
  | GrammarErrorAnnotation;

export interface DifficultSentenceAnnotation {
  annotation_id: string;
  sentence_id: string;
  span: Span;
  trigger_reason: string[];
  main_clause: string;
  chunks: {
    order: number;
    label: string;
    text: string;
  }[];
  reading_path_zh: string;
  objective_level: 'basic' | 'intermediate' | 'advanced';
  priority: 'core' | 'expand' | 'reference';
  default_visible: boolean;
}

export interface SentenceTranslation {
  sentence_id: string;
  translation_zh: string;
  style: string;
}

export interface KeyPhraseTranslation {
  phrase: string;
  sentence_id: string;
  span: Span;
  translation_zh: string;
}

export interface Translations {
  sentence_translations: SentenceTranslation[];
  full_translation_zh: string;
  key_phrase_translations: KeyPhraseTranslation[];
}

export interface AnalysisResponse {
  schema_version: string;
  request: {
    request_id: string;
    profile_key: string;
    profile_snapshot: Record<string, any>;
    discourse_enabled: boolean;
  };
  status: {
    state: 'success' | 'partial_success' | 'failed';
    degraded: boolean;
    error_code: string | null;
    user_message: string | null;
  };
  article: Article;
  annotations: {
    vocabulary: VocabularyAnnotation[];
    grammar: GrammarAnnotation[];
    difficult_sentences: DifficultSentenceAnnotation[];
  };
  translations: Translations;
  discourse: any | null;
  warnings: {
    code: string;
    message_zh: string;
  }[];
  metrics: {
    vocabulary_count: number;
    grammar_count: number;
    difficult_sentence_count: number;
    sentence_count: number;
    paragraph_count: number;
  };
}

/**
 * 词典 API 响应 DTO
 *
 * 对齐后端 DictResult (server/app/api/routes/dict.py)
 * 使用 snake_case 与后端协议一致
 */

export interface DictMeaningDefinitionDto {
  meaning: string
  example: string | null
  example_translation: string | null
}

export interface DictMeaningDto {
  part_of_speech: string
  definitions: DictMeaningDefinitionDto[]
}

export interface EcdictEntryDto {
  word: string
  lemma: string | null
  phonetic: string | null
  short_meaning: string | null
  meanings: DictMeaningDto[]
  tags: string[]
  exchange: string[]
}

export interface DictResponseDto {
  word: string
  phonetic: string | null
  audio_url: string | null
  meanings: DictMeaningDto[]
  cached: boolean
  provider: string
  entry: EcdictEntryDto | null
}

export interface DictMeaningDefinitionDto {
  meaning: string
  example: string | null
  example_translation: string | null
}

export interface DictMeaningDto {
  part_of_speech: string
  definitions: DictMeaningDefinitionDto[]
}

export interface DictExampleDto {
  example: string
  example_translation: string | null
}

export interface DictPhraseDto {
  phrase: string
  meaning: string | null
}

export interface DictEntryPayloadDto {
  id: number
  word: string
  base_word: string | null
  homograph_no: number | null
  phonetic: string | null
  primary_pos: string | null
  meanings: DictMeaningDto[]
  examples: DictExampleDto[]
  phrases: DictPhraseDto[]
  entry_kind: 'entry' | 'fragment'
}

export interface DictCandidateDto {
  entry_id: number
  label: string
  part_of_speech: string | null
  preview: string | null
  entry_kind: 'entry' | 'fragment'
}

interface DictResponseBaseDto {
  result_type: 'entry' | 'disambiguation'
  query: string
  provider: string
  cached: boolean
}

export interface DictEntryResultDto extends DictResponseBaseDto {
  result_type: 'entry'
  entry: DictEntryPayloadDto
}

export interface DictDisambiguationResultDto extends DictResponseBaseDto {
  result_type: 'disambiguation'
  candidates: DictCandidateDto[]
}

export type DictResponseDto = DictEntryResultDto | DictDisambiguationResultDto

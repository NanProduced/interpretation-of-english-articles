import type {
  DictDisambiguationResultDto,
  DictEntryResultDto,
  DictResponseDto,
} from '@/types/api/dict-response.dto'
import type {
  DictionaryDisambiguationResult,
  DictionaryEntryResult,
  DictionaryResult,
} from '@/types/view/render-scene.vm'

function mapEntryResult(dto: DictEntryResultDto): DictionaryEntryResult {
  return {
    resultType: 'entry',
    query: dto.query,
    provider: dto.provider,
    cached: dto.cached,
    entry: {
      id: dto.entry.id,
      word: dto.entry.word,
      baseWord: dto.entry.base_word ?? undefined,
      homographNo: dto.entry.homograph_no ?? undefined,
      phonetic: dto.entry.phonetic ?? undefined,
      primaryPos: dto.entry.primary_pos ?? undefined,
      meanings: dto.entry.meanings.map((m) => ({
        partOfSpeech: m.part_of_speech,
        definitions: m.definitions.map((d) => ({
          meaning: d.meaning,
          example: d.example ?? undefined,
          exampleTranslation: d.example_translation ?? undefined,
        })),
      })),
      examples: dto.entry.examples.map((item) => ({
        example: item.example,
        exampleTranslation: item.example_translation ?? undefined,
      })),
      phrases: dto.entry.phrases.map((item) => ({
        phrase: item.phrase,
        meaning: item.meaning ?? undefined,
      })),
      entryKind: dto.entry.entry_kind,
    },
  }
}

function mapDisambiguationResult(dto: DictDisambiguationResultDto): DictionaryDisambiguationResult {
  return {
    resultType: 'disambiguation',
    query: dto.query,
    provider: dto.provider,
    cached: dto.cached,
    candidates: dto.candidates.map((item) => ({
      entryId: item.entry_id,
      label: item.label,
      partOfSpeech: item.part_of_speech ?? undefined,
      preview: item.preview ?? undefined,
      entryKind: item.entry_kind,
    })),
  }
}

export function dictResponseDtoToVm(dto: DictResponseDto): DictionaryResult {
  if (dto.result_type === 'entry') {
    return mapEntryResult(dto)
  }
  return mapDisambiguationResult(dto)
}

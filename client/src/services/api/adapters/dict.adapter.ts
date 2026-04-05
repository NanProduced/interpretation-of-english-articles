/**
 * Dict API 适配器
 *
 * 将后端 DictResponseDto (snake_case) 转换为前端 DictionaryResult (camelCase)
 * 字段映射规则：
 *   phonetic      → phonetic (same)
 *   audio_url    → audioUrl
 *   part_of_speech → partOfSpeech
 *   example_translation → exampleTranslation
 */

import type { DictResponseDto } from '@/types/api/dict-response.dto'
import type { DictionaryResult } from '@/types/view/render-scene.vm'

export function dictResponseDtoToVm(dto: DictResponseDto): DictionaryResult {
  return {
    word: dto.word,
    phonetic: dto.phonetic ?? undefined,
    audioUrl: dto.audio_url ?? undefined,
    meanings: dto.meanings.map((m) => ({
      partOfSpeech: m.part_of_speech,
      definitions: m.definitions.map((d) => ({
        meaning: d.meaning,
        example: d.example ?? undefined,
        exampleTranslation: d.example_translation ?? undefined,
      })),
    })),
  }
}

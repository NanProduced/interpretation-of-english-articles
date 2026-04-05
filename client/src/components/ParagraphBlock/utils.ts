/**
 * 英文阅读 UI 的轻量 lexer。
 *
 * 目标不是做通用 NLP tokenization，而是稳定切出“可点英文词”：
 * - 普通单词：word
 * - 带撇号 / 连字符：don't / world's / state-owned
 * - 缩写：U.S. / U.K. / Ph.D. / e.g.
 * - 其他（空格、中文、数字、标点等）：plain
 *
 * 这样可以保证结果页的点击热区稳定，不依赖复杂 tokenizer 框架。
 */

export interface TextToken {
  type: 'word' | 'plain'
  text: string
}

type ScanResult = {
  end: number
  text: string
}

function isAsciiLetter(ch: string | undefined): boolean {
  if (!ch) return false
  const code = ch.charCodeAt(0)
  return (code >= 65 && code <= 90) || (code >= 97 && code <= 122)
}

function isWordConnector(ch: string | undefined): boolean {
  return ch === '\'' || ch === '’' || ch === '-'
}

function scanLetters(text: string, start: number): number {
  let i = start
  while (i < text.length && isAsciiLetter(text[i])) i++
  return i
}

/**
 * 匹配类似 U.S. / U.K. / Ph.D. / e.g. 的缩写。
 * 规则：至少两个「letters + dot」片段才视为缩写。
 */
function scanAbbreviation(text: string, start: number): ScanResult | null {
  let i = start
  let dottedSegments = 0

  while (i < text.length) {
    const lettersEnd = scanLetters(text, i)
    if (lettersEnd === i || text[lettersEnd] !== '.') break

    dottedSegments += 1
    i = lettersEnd + 1

    if (!isAsciiLetter(text[i])) break
  }

  if (dottedSegments < 2) return null
  return { end: i, text: text.slice(start, i) }
}

function scanPlainWord(text: string, start: number): ScanResult | null {
  let i = scanLetters(text, start)
  if (i === start) return null

  while (i < text.length) {
    const connector = text[i]
    if (!isWordConnector(connector)) break

    const next = text[i + 1]
    if (connector === '-') {
      if (!isAsciiLetter(next)) break
      i = scanLetters(text, i + 1)
      continue
    }

    if (connector === '\'' || connector === '’') {
      if (!isAsciiLetter(next)) {
        // students' 这种尾部所有格
        i += 1
        break
      }
      i = scanLetters(text, i + 1)
      continue
    }
  }

  return { end: i, text: text.slice(start, i) }
}

function scanWordLike(text: string, start: number): ScanResult | null {
  const abbreviation = scanAbbreviation(text, start)
  if (abbreviation) {
    let i = abbreviation.end

    while (text[i] === '-') {
      const nextStart = i + 1
      const nextToken = scanAbbreviation(text, nextStart) ?? scanPlainWord(text, nextStart)
      if (!nextToken) break
      i = nextToken.end
    }

    return { end: i, text: text.slice(start, i) }
  }

  return scanPlainWord(text, start)
}

/**
 * 将文本拆分为交替的 token 序列，并合并连续 plain token。
 */
export function tokenizeText(text: string): TextToken[] {
  const tokens: TextToken[] = []
  let i = 0

  while (i < text.length) {
    const wordLike = scanWordLike(text, i)
    if (wordLike) {
      tokens.push({ type: 'word', text: wordLike.text })
      i = wordLike.end
      continue
    }

    let plainEnd = i + 1
    while (plainEnd < text.length && !scanWordLike(text, plainEnd)) {
      plainEnd += 1
    }

    tokens.push({ type: 'plain', text: text.slice(i, plainEnd) })
    i = plainEnd
  }

  const merged: TextToken[] = []
  for (const token of tokens) {
    const last = merged[merged.length - 1]
    if (last && last.type === token.type) {
      last.text += token.text
    } else {
      merged.push(token)
    }
  }

  return merged
}

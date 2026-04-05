/**
 * 英文单词 tokenization 工具
 *
 * 将任意文本拆分为"可点击英文词"和"普通文本"交替的片段。
 * - 英文词（含 contraction、possessive）：{ type: 'word', text }
 * - 其他（空格、中文、标点、数字等）：{ type: 'plain', text }
 *
 * 简单规则：
 *   - [a-zA-Z]+('[a-zA-Z]+)?  → 英文词（支持 don't, student's）
 *   - [a-zA-Z]+-[a-zA-Z]+     → 带连字符的英文词（well-known）
 *   - 其余所有字符              → 普通文本
 */

export interface TextToken {
  type: 'word' | 'plain'
  text: string
}

/** 判断一个纯字符 token 是否为英文 */
function isEnglishWord(text: string): boolean {
  return /^[a-zA-Z]+(-[a-zA-Z]+)*('[a-zA-Z]+)*$/u.test(text)
}

/**
 * 将文本拆分为交替的 token 序列
 * 合并连续同类 token 以减少 React 元素数量
 */
export function tokenizeText(text: string): TextToken[] {
  // 匹配英文词（含 contraction 和 hyphenated）和非英文片段。
  // 注意：这里必须使用 `+` 而不是 `*`，否则会产生零长度匹配，
  // 在 `while (tokenRe.exec())` 循环里卡住小程序渲染线程。
  const tokenRe = /[a-zA-Z]+(?:['-][a-zA-Z]+)*|[^a-zA-Z]+/g
  const tokens: TextToken[] = []
  let match: RegExpExecArray | null

  while ((match = tokenRe.exec(text)) !== null) {
    const t = match[0]
    const type: 'word' | 'plain' = isEnglishWord(t) ? 'word' : 'plain'
    // 合并相邻同类 token
    const last = tokens[tokens.length - 1]
    if (last && last.type === type) {
      last.text += t
    } else {
      tokens.push({ type, text: t })
    }
  }

  return tokens
}

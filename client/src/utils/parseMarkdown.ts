/**
 * 简单的 Markdown 解析工具
 * 支持：**粗体**、*斜体*、`行内代码`、- 列表项、\n\n 段落分隔
 * 不支持：语义化标题（## 标题）、编号列表（1. item）、代码块（``` ```）
 * 小程序环境使用，不引入外部库
 */

interface ParsedSegment {
  text: string
  bold?: boolean
  italic?: boolean
  code?: boolean
  list?: boolean
  paragraph?: boolean
}

/**
 * 解析 Markdown 文本为带样式的片段数组
 */
export function parseMarkdown(text: string): ParsedSegment[] {
  const result: ParsedSegment[] = []

  // 按行分割处理
  const lines = text.split('\n')

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmedLine = line.trim()

    // 空行处理
    if (trimmedLine === '') {
      continue
    }

    // 解析无序列表项 (- 或 * 开头)
    if (/^[-*]\s/.test(trimmedLine)) {
      const listContent = trimmedLine.replace(/^[-*]\s/, '')
      result.push({ text: '• ' + listContent, list: true })
      continue
    }

    // 处理行内样式
    // 先处理代码 `code`
    let processedLine = trimmedLine
    const segments: ParsedSegment[] = []
    let lastIndex = 0

    // 匹配代码块 `code`
    const codeRegex = /`([^`]+)`/g
    let codeMatch

    while ((codeMatch = codeRegex.exec(processedLine)) !== null) {
      // 处理代码之前的文本
      if (codeMatch.index > lastIndex) {
        const beforeCode = processedLine.slice(lastIndex, codeMatch.index)
        parseInlineStyles(beforeCode, segments)
      }
      // 添加代码
      segments.push({ text: codeMatch[1], code: true })
      lastIndex = codeMatch.index + codeMatch[0].length
    }

    // 处理剩余文本
    if (lastIndex < processedLine.length) {
      parseInlineStyles(processedLine.slice(lastIndex), segments)
    }

    // 添加所有片段
    result.push(...segments)
  }

  return result
}

/**
 * 解析行内样式（粗体、斜体）
 */
function parseInlineStyles(text: string, segments: ParsedSegment[]): void {
  // 优先处理粗体 **text**
  const boldRegex = /\*\*([^*]+)\*\*/g
  let lastIndex = 0
  let match

  while ((match = boldRegex.exec(text)) !== null) {
    // 处理粗体之前的文本
    if (match.index > lastIndex) {
      const beforeBold = text.slice(lastIndex, match.index)
      parseItalic(beforeBold, segments)
    }
    // 添加粗体
    segments.push({ text: match[1], bold: true })
    lastIndex = match.index + match[0].length
  }

  // 处理剩余文本中的斜体
  if (lastIndex < text.length) {
    parseItalic(text.slice(lastIndex), segments)
  }
}

/**
 * 解析斜体 *text*
 */
function parseItalic(text: string, segments: ParsedSegment[]): void {
  // 匹配斜体 *text*（但不是 ** 因为那是粗体）
  const italicRegex = /(?<!\*)\*([^*]+)\*(?!\*)/g
  let lastIndex = 0
  let match

  while ((match = italicRegex.exec(text)) !== null) {
    // 处理斜体之前的文本
    if (match.index > lastIndex) {
      segments.push({ text: text.slice(lastIndex, match.index) })
    }
    // 添加斜体
    segments.push({ text: match[1], italic: true })
    lastIndex = match.index + match[0].length
  }

  // 处理剩余文本
  if (lastIndex < text.length) {
    segments.push({ text: text.slice(lastIndex) })
  }
}

/**
 * 渲染 Markdown 内容为 Taro JSX
 */
export function renderMarkdownContent(
  text: string,
  renderText: (segment: ParsedSegment) => JSX.Element
): JSX.Element[] {
  const segments = parseMarkdown(text)
  return segments.map((segment, index) => renderText(segment))
}

# Workflow 输出格式优化建议

版本：`v3.1-draft`

## 1. 背景

当前 `grammar_note` 和 `sentence_analysis` 在 projection 阶段被拼成 Markdown 文本。这样做的优点是前端接入快，但问题也很明显：

1. 前端难以区分“结构化数据”和“解释文本”
2. 为了展示层次，后端被迫在 Markdown 里塞入 `核心结论`、`锚点定位`、`整句理解`、`阅读顺序拆解` 这类标题
3. 一旦前端希望改版，这些标题就会变成展示噪音

从当前结果页体验看，最突出的症状是：

1. 语法卡片看起来像“把内部调试说明直接展示给用户”
2. 锚点信息本应服务前端定位，却被写进了正文 Markdown
3. 长难句拆解的 `chunks` 已经是结构化数据，但在公开 schema 中被降级成了纯文本

## 2. 结论

应当把下面两类信息彻底分开：

1. `结构化字段`
2. `面向用户的讲解文本`

具体原则：

1. 锚点、步骤、标签属于结构化字段，不应该编码进 Markdown 标题或列表。
2. 中文解释、阅读提示、示例说明才属于 Markdown 内容。
3. Projection 不应该为了“兼容现在的前端”永久牺牲 schema 可演进性。
4. `grammar_note` 与 `sentence_analysis` 必须在语义上拉开边界，不能都退化成“抓从句并解释一下”。

## 3. GrammarNote 优化建议

### 3.1 当前问题

当前公开结构只有：

1. `label`
2. `content`

而 `content` 被拼成了：

```md
**核心结论**

...

**锚点定位**

- **subject**: `...`
- **verb**: `...`
```

这会导致：

1. 标题语言很“后台化”
2. 锚点明明已经在 `InlineMark.anchor` 里，仍然在正文里重复一遍
3. `grammar_note` 的信息边界不清，容易和 `sentence_analysis` 同质化

### 3.2 建议的目标结构

建议未来把 `grammar_note` 暴露成：

```json
{
  "id": "...",
  "sentence_id": "s1",
  "entry_type": "grammar_note",
  "label": "who 引导的定语从句作主语",
  "content_md": "Anyone who forgets this ... 整体作主语。理解时先抓主干 Anyone becomes ...",
  "spans": [
    {"text": "Anyone who forgets this and tries a joke in the afternoon"},
    {"text": "becomes"}
  ]
}
```

这里的 `spans` 只负责：

1. 锚定原句中的相关文本
2. 供前端做下划线或联动定位

它不负责：

1. 承担句法角色标注
2. 充当 sentence analysis 的成分拆解

### 3.3 过渡期建议

在不改公开 schema 的前提下，workflow agent 的输出约束至少应改成：

1. `note_zh` 直接写面向用户的解释，不要再写 `核心结论`
2. 不要在 `note_zh` 里写 `锚点定位`
3. `label` 就是语法点名称，`note_zh` 直接从解释正文开始
4. `grammar_note` 不应只覆盖从句，也应覆盖倒装、固定句型、近义结构辨析、局部搭配模式等

推荐风格：

```text
Anyone who forgets this and tries a joke in the afternoon 整体作主语，其中 who 引导的定语从句修饰 Anyone。理解时先抓主干 Anyone becomes an 'April Fool' themselves，再回头补 who 从句里的细节。
```

另一个同样合理的 grammar note 例子：

```text
not until 放在句首时，主句通常会触发部分倒装，所以这里先看到助动词，再看到真正的主语和谓语。阅读时先把 not until 当作时间限制条件，不要误读成普通 until 从句。
```

不推荐风格：

```text
**核心结论**
...
**锚点定位**
...
```

## 4. SentenceAnalysis 优化建议

### 4.1 当前问题

`SentenceAnalysis` 内部已经有：

1. `label`
2. `analysis_zh`
3. `chunks`

但 projection 仍把它们拼成：

```md
**整句理解**
...

**阅读顺序拆解**
- **1. 主语**：`...`
```

这会导致：

1. 前端无法把 `chunks` 真正渲染成步骤卡
2. `整句理解`、`阅读顺序拆解` 这些标题在 UI 中显得重复
3. Markdown 变成结构载体，而不是内容载体

### 4.2 建议的目标结构

建议未来把 `sentence_analysis` 暴露成：

```json
{
  "id": "...",
  "sentence_id": "s7",
  "entry_type": "sentence_analysis",
  "label": "复杂并列句与时间状语嵌套",
  "summary_md": "先抓主干：This continues and the victim ends up ...",
  "chunks": [
    {"order": 1, "label": "主干一", "text": "This continues"},
    {"order": 2, "label": "主干二", "text": "the victim ends up taking the message ..."},
    {"order": 3, "label": "until 从句", "text": "until someone feels sorry ..."}
  ]
}
```

### 4.3 过渡期建议

在不改 schema 的前提下，至少应让 `analysis_zh` 保持纯解释文本：

1. 不要写 `整句理解`
2. 不要写 `阅读顺序拆解`
3. 如果要表达阅读顺序，把它自然写进说明里

推荐风格：

```text
先抓主干：This continues and the victim ends up taking the message to several different people，这是两个并列动作。until someone feels sorry for them and shows them what the letter says 补充说明事情会持续到什么时候。阅读时先理解恶作剧持续发生，再补 until 从句里的结果条件。
```

## 5. 对 workflow agent 的输出约束建议

### 5.1 Grammar agent

建议改成：

1. `label` 负责命名语法点
2. `spans` 只负责定位，不在 `note_zh` 中重复输出“锚点定位”
3. `note_zh` 只写讲解正文，可使用轻量 Markdown
4. 讲解长度控制在 `1-3` 句，避免写成教程式小作文
5. 语法点范围应覆盖：
   - 倒装、否定前置、强调
   - 非谓语局部结构
   - 固定句型与搭配模式
   - 易混结构辨析，如 `make sb do` / `make sth done`
   - 局部从句功能

### 5.2 Sentence analysis agent

建议改成：

1. `label` 负责给出句型概括
2. `summary_md` 只写整句理解和阅读顺序提示
3. `chunks` 负责承载结构顺序，不要求 `summary_md` 再把 chunk 名单重写一遍
4. 避免输出“首先/其次/最后”式过长枚举
5. `sentence_analysis` 的任务是拆整句结构，而不是重复解释某个局部语法点

## 6. 当前前端阶段的实际建议

在当前不改后端 schema 的前提下，最务实的做法是：

1. workflow agent 立即停止生成 `核心结论` / `锚点定位` / `整句理解` / `阅读顺序拆解` 这类 Markdown 标题
2. `grammar_note` 先扩展到“局部语法点/句型/辨析/搭配模式”，不要只做从句提示
3. 前端继续使用现有 Markdown 渲染
4. 等结果页 UI 稳定后，再决定是否把 `spans` / `chunks` 提升为公开字段

这样可以先解决“文案奇怪、像调试输出”的问题，同时不给当前联调增加 schema 变更成本。

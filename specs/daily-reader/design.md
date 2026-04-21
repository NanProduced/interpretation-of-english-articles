# Technical Design

## Overview

本次开发分为四层：

1. 文章拉取 Pipeline：自动从外部英文媒体拉取候选文章 → 正文提取 → 内容安全检测 → AI 筛选评分
2. 专用 Workflow：Daily Reader 独立 LangGraph 图，含质量审核与优化节点，生成精读 payload
3. 后端 API + 数据层：`daily_readers` 表 + Daily Reader CRUD API
4. 前端页面：杂志式阅读页 + 首页入口 + 分享

本次明确不做：

- 实时 `/analyze` 触发（预生成模式）
- 复用主线结果页布局
- AI 生成封面图
- 音频朗读（V2 考虑）
- 阅读打卡/连续天数系统

## Data Design

### daily_readers 表

```sql
CREATE TABLE daily_readers (
    id                  TEXT PRIMARY KEY,
    title               TEXT NOT NULL,
    subtitle            TEXT,
    source              TEXT NOT NULL,
    source_url          TEXT NOT NULL,
    publish_date        DATE NOT NULL,
    difficulty          TEXT NOT NULL CHECK (difficulty IN ('A2', 'B1', 'B2', 'C1')),
    read_time_minutes   INTEGER NOT NULL,
    tags                JSONB NOT NULL DEFAULT '[]'::jsonb,

    cover_image_url     TEXT,
    cover_theme         TEXT NOT NULL DEFAULT 'editorial_warm',

    body_json           JSONB NOT NULL,
    highlights_json     JSONB NOT NULL DEFAULT '[]'::jsonb,
    footer_analysis_json JSONB NOT NULL,

    status              TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    score               REAL,

    content_sec_check   JSONB NOT NULL DEFAULT '{}'::jsonb,
    original_text_hash  TEXT,
    pipeline_source     TEXT,
    pipeline_meta       JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at        TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE daily_readers IS '每日精读文章表，存储预生成的精读内容 payload。每天最多 3 篇已发布文章，由应用层保证，数据库不做 UNIQUE 约束。';

CREATE INDEX idx_daily_readers_status_date ON daily_readers(status, publish_date DESC);
CREATE INDEX idx_daily_readers_published ON daily_readers(publish_date DESC)
    WHERE status = 'published';

CREATE TRIGGER trg_daily_readers_set_updated_at
BEFORE UPDATE ON daily_readers
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMENT ON COLUMN daily_readers.id IS '文章 ID，格式 daily_{YYYY}_{MM}_{DD}_{NNN}。';
COMMENT ON COLUMN daily_readers.source IS '来源媒体名称，如 The Guardian、BBC News。';
COMMENT ON COLUMN daily_readers.source_url IS '原文链接，用于版权标注和引导用户访问。';
COMMENT ON COLUMN daily_readers.cover_theme IS '封面氛围主题，用于无封面图时的渐变色渲染。';
COMMENT ON COLUMN daily_readers.body_json IS '正文段落数据，包含段落文本和高亮锚点。';
COMMENT ON COLUMN daily_readers.highlights_json IS '正文高亮标注数据，vocab_highlight/phrase_gloss/context_gloss。';
COMMENT ON COLUMN daily_readers.footer_analysis_json IS '文末解析数据，summary/structure/key_expressions/full_analysis/discussion_questions。';
COMMENT ON COLUMN daily_readers.content_sec_check IS '微信内容安全检测结果，含 trace_id、suggest、label 等。';
COMMENT ON COLUMN daily_readers.original_text_hash IS '原文 SHA256，用于去重校验。';
COMMENT ON COLUMN daily_readers.pipeline_source IS '拉取来源标识，如 guardian_api、bbc_rss。';
COMMENT ON COLUMN daily_readers.pipeline_meta IS 'Pipeline 运行元数据，含评分详情、提取日志、workflow 审核记录等。';
```

### body_json 结构

```json
{
  "paragraphs": [
    {
      "id": "p_0",
      "text": "The shift toward hybrid work has been one of the most significant changes...",
      "highlights": [
        {
          "anchor": "hybrid work",
          "start": 15,
          "end": 26,
          "type": "vocab_highlight",
          "gloss": "混合办公"
        }
      ]
    }
  ]
}
```

### highlights_json 结构

```json
[
  {
    "id": "hl_001",
    "type": "vocab_highlight",
    "text": "hybrid work",
    "gloss": "混合办公",
    "paragraph_id": "p_0",
    "start": 15,
    "end": 26,
    "detail": {
      "phonetic": "/ˈhaɪbrɪd wɜːrk/",
      "pos": "noun phrase",
      "context_explanation": "指结合远程办公和到岗办公的工作模式"
    }
  },
  {
    "id": "hl_002",
    "type": "phrase_gloss",
    "text": "in-person collaboration",
    "gloss": "面对面协作",
    "paragraph_id": "p_2",
    "start": 40,
    "end": 62
  }
]
```

### footer_analysis_json 结构

```json
{
  "summary": "The article argues that hybrid work is not a temporary compromise but a permanent shift in how we define productivity.",
  "thesis_and_intent": {
    "thesis": "Hybrid work represents a fundamental redefinition of workplace productivity rather than a pandemic-era concession.",
    "author_intent": "To persuade readers that the hybrid model is here to stay and organizations must adapt their culture accordingly."
  },
  "structure": [
    {
      "label": "Part 1",
      "title": "The Hybrid Shift",
      "summary": "How the pandemic accelerated a change already underway"
    },
    {
      "label": "Part 2",
      "title": "The Debate",
      "summary": "Competing arguments for and against office-first culture"
    },
    {
      "label": "Part 3",
      "title": "What Comes Next",
      "summary": "Principles for making hybrid work sustainable"
    }
  ],
  "key_expressions": [
    {
      "expression": "hybrid work",
      "gloss": "混合办公",
      "context_sentence": "The shift toward hybrid work has been one of the most significant changes..."
    }
  ],
  "misreading_points": [
    {
      "point": "The author is not arguing that remote work is superior to office work.",
      "clarification": "The argument is about flexibility and choice, not about one mode being inherently better."
    }
  ],
  "full_article_analysis": "This article examines the transformation of workplace culture...",
  "discussion_questions": [
    "Do you prefer remote or office work? Why?",
    "What are the cultural trade-offs of hybrid work models?",
    "How might hybrid work affect career advancement differently for different groups?"
  ]
}
```

## Article Pipeline Design

### 文章数量策略

| 阶段 | 数量 | 说明 |
|------|------|------|
| 拉取候选 | ~30 篇/天 | Guardian API 20 篇 + BBC RSS 5 篇 + NPR RSS 5 篇 |
| 提取全文 | ~25 篇/天 | RSS 源约 80% 提取成功率 |
| 内容安全检测 | ~25 篇/天 | 微信 msgSecCheck，约 100% 通过（英文文章极少违规） |
| 长度过滤 | ~15 篇/天 | 400-2500 词区间 |
| AI 评分筛选 | ~5-8 篇/天 | 4 维评分 ≥ 7.0 通过 |
| 封面图过滤 | ~4-6 篇/天 | 必须有封面图（无封面图的文章降级处理，不优先选择） |
| 执行 Workflow | **2-3 篇/天** | 对 top-2~3 执行完整 workflow，来源多样化 |
| 展示到主页 | **2-3 篇/天** | 今日精读（不同来源、不同主题） |

关键原则：

- **每天发布 2-3 篇**，不超过 3 篇，给用户不同类型选择
- **来源多样化**：同一天的 2-3 篇文章应来自不同数据源（如 1 篇 Guardian + 1 篇 BBC），避免每天都是同一来源
- **封面图必须**：文章必须有封面图才能作为精读文章发布，无封面图的文章降级处理（不优先选择，除非当天所有候选文章都无封面图）
- **质量优先**：宁可少发（2 篇）也不要降低质量标准凑 3 篇

### Pipeline 执行时间

Pipeline 在 **UTC+8 每天 8:00-9:00** 之间执行。原因：

- Guardian/BBC 总部在 UK（UTC+0/+1），其文章主要在 UK 工作时间发布，到 UTC+8 次日早晨时已有过去 12-24 小时的丰富内容
- NPR 总部在 US（UTC-5/-4），其文章主要在 US 工作时间发布，到 UTC+8 早晨时也有过去 8-12 小时的内容
- UTC+8 8:00-9:00 是用户开始使用小程序的时间，此时执行可以确保内容是最新的

### 来源轮换策略

```python
SOURCE_ROTATION_POLICY = {
    "max_same_source_per_day": 2,
    "preferred_combinations": [
        {"guardian": 1, "bbc": 1, "npr": 1},
        {"guardian": 2, "bbc": 1},
        {"guardian": 1, "bbc": 1},
        {"guardian": 1, "npr": 1},
        {"bbc": 1, "npr": 1},
    ],
    "topic_diversity": True,
}
```

在 AI 评分后，按以下规则选择 top 候选：

1. 按评分排序
2. 确保来源多样化（同来源不超过 2 篇）
3. 确保主题多样化（避免 3 篇都是科技类）
4. 确保有封面图（无封面图的文章排到后面）
5. 对选中的 2-3 篇执行 Workflow

### 四层架构

```
Layer 1: 发现层 (Discovery)
  ├─ Guardian API (主力) → 全文+封面+标签+字数
  ├─ BBC RSS (辅助) → 标题+摘要+封面 → trafilatura 提取全文
  └─ NPR RSS (补充) → 标题+摘要+封面 → trafilatura 提取全文

Layer 2: 提取层 (Extraction)
  └─ trafilatura → 正文+作者+日期+描述+图片

Layer 2.5: 安全检测层 (Content Security)
  └─ 微信 msgSecCheck → 文本内容安全识别（标题+正文）

Layer 3: 筛选层 (Scoring)
  └─ LLM 评分 → 长度过滤 + 4维评分 + CEFR 估算 + 标签生成
```

### 数据源配置

```python
ARTICLE_SOURCES = {
    "guardian": {
        "type": "api",
        "base_url": "https://content.guardianapis.com",
        "sections": ["science", "technology", "culture", "lifeandstyle", "society"],
        "show_fields": "headline,standfirst,thumbnail,wordcount,body,byline",
        "wordcount_range": (500, 2000),
        "page_size": 20,
    },
    "bbc": {
        "type": "rss",
        "feeds": {
            "science": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
            "technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
            "culture": "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
            "health": "https://feeds.bbci.co.uk/news/health/rss.xml",
            "business": "https://feeds.bbci.co.uk/news/business/rss.xml",
        },
        "image_width_upgrade": {"from": 240, "to": 640},
    },
    "npr": {
        "type": "rss",
        "feeds": {
            "science": "https://feeds.npr.org/1007/rss.xml",
            "technology": "https://feeds.npr.org/1019/rss.xml",
            "culture": "https://feeds.npr.org/1008/rss.xml",
        },
    },
}
```

### 内容安全检测（微信 msgSecCheck）

在提取全文后、AI 评分前，对每篇文章执行微信内容安全检测：

```python
async def check_content_security(title: str, text: str) -> dict:
    access_token = await get_wechat_access_token()
    response = await httpx_client.post(
        "https://api.weixin.qq.com/wxa/msg_sec_check",
        params={"access_token": access_token},
        json={
            "content": text[:2500],
            "version": 2,
            "scene": 3,
            "openid": SYSTEM_OPENID,
            "title": title[:100],
        },
    )
    result = response.json()
    return {
        "suggest": result.get("result", {}).get("suggest", "pass"),
        "label": result.get("result", {}).get("label", 100),
        "trace_id": result.get("trace_id", ""),
        "detail": result.get("detail", []),
    }
```

关键设计点：

- **scene=3**（论坛场景）：最接近"平台发布内容供用户阅读"的场景
- **openid**：使用小程序管理员账号的 openid，通过定时任务（每 90 分钟自动触发一次小程序访问）保活该 openid
- **content 限制**：2500 字上限，英文文章通常不会超限；如超限则截取前 2500 字
- **结果判定**：`suggest=pass` 放行，`suggest=review` 或 `suggest=risky` 拒绝
- **检测时机**：在提取全文后、AI 评分前执行，避免对违规文章浪费 LLM token
- **结果存储**：`content_sec_check` JSONB 字段存储完整检测结果，便于追溯

### Pipeline 执行流程

```python
async def run_daily_pipeline():
    candidates = []

    # Layer 1: Discovery
    guardian_articles = await discover_guardian()
    candidates.extend(guardian_articles)

    rss_articles = await discover_rss_sources()
    candidates.extend(rss_articles)

    # Layer 2: Extraction (for RSS-sourced articles)
    for article in candidates:
        if article.get("needs_extraction"):
            extracted = await extract_with_trafilatura(article["url"])
            if extracted:
                article.update(extracted)

    # Deduplication
    candidates = await deduplicate(candidates)

    # Length filter
    candidates = [a for a in candidates if 400 <= word_count(a) <= 2500]

    # Layer 2.5: Content Security Check
    safe_candidates = []
    for article in candidates:
        sec_result = await check_content_security(article["title"], article["text"])
        article["content_sec_check"] = sec_result
        if sec_result["suggest"] == "pass":
            safe_candidates.append(article)

    # Layer 3: AI Scoring
    scored = []
    for article in safe_candidates:
        result = await score_article(article)
        if result.score >= 7.0:
            article["score"] = result.score
            article["difficulty"] = result.difficulty
            article["tags"] = result.tags
            scored.append(article)

    # Select top candidates with source/topic diversity and cover image priority
    scored.sort(key=lambda a: (a.get("cover_image_url") is not None, a["score"]), reverse=True)
    selected = select_diverse_candidates(scored, max_count=max_count + 2, max_same_source=2)

    # Execute workflow for each candidate (candidate queue mode)
    # Oversample by 2 to allow for workflow failures/aborts
    results = []
    for candidate in selected:
        if len(results) >= max_count:
            break
        payload = await run_daily_reader_workflow(candidate)
        if payload is not None:
            await store_daily_reader(payload)
            results.append(payload)

    # If not enough, try remaining candidates from scored list
    if len(results) < max_count:
        remaining = [s for s in scored if s not in selected]
        for candidate in remaining:
            if len(results) >= max_count:
                break
            payload = await run_daily_reader_workflow(candidate)
            if payload is not None:
                await store_daily_reader(payload)
                results.append(payload)

    return results
```

## Daily Reader Workflow Design

### 图定义

```python
daily_reader_graph = StateGraph(DailyReaderState)

daily_reader_graph.add_node("light_normalize", light_normalize_node)
daily_reader_graph.add_node("vocab_highlight", vocab_highlight_node)
daily_reader_graph.add_node("phrase_context_gloss", phrase_context_gloss_node)
daily_reader_graph.add_node("footer_analysis", footer_analysis_node)
daily_reader_graph.add_node("full_interpretation", full_interpretation_node)
daily_reader_graph.add_node("quality_review", quality_review_node)
daily_reader_graph.add_node("refinement", refinement_node)
daily_reader_graph.add_node("daily_projection", daily_projection_node)

daily_reader_graph.add_edge(START, "light_normalize")
daily_reader_graph.add_edge("light_normalize", "vocab_highlight")
daily_reader_graph.add_edge("vocab_highlight", "phrase_context_gloss")
daily_reader_graph.add_edge("phrase_context_gloss", "footer_analysis")
daily_reader_graph.add_edge("footer_analysis", "full_interpretation")
daily_reader_graph.add_edge("full_interpretation", "quality_review")
daily_reader_graph.add_conditional_edges(
    "quality_review",
    _should_refine,
    {True: "refinement", False: "daily_projection"},
)
daily_reader_graph.add_edge("refinement", "daily_projection")
daily_reader_graph.add_edge("daily_projection", END)
```

### 节点职责

| 节点 | 类型 | 输入 | 输出 | 职责 | 推荐模型 |
|------|------|------|------|------|---------|
| light_normalize | 确定性 | 原文文本 | 归一化文本 + 段落切分 | 轻量清洗（去除 HTML、统一空白、段落切分），不做 repair | 无（不调用 LLM） |
| vocab_highlight | LLM | 归一化段落 | 词汇高亮锚点 | 标注核心生词，每段不超过 3-5 个，优先标注 B1-C1 级词汇 | 标注级模型 |
| phrase_context_gloss | LLM | 段落 + 词汇高亮 | 短语/语境高亮 | 标注关键短语和少量语境解释，克制数量 | 标注级模型 |
| footer_analysis | LLM | 全文 + 所有高亮 | footer_analysis JSON | 生成摘要、主旨、结构、关键表达、易误读点、讨论问题 | **最强模型** |
| full_interpretation | LLM | 全文 + footer_analysis | 全篇解析文本 | 生成连贯的讲解式全篇解析（非逐句拆解） | **最强模型** |
| quality_review | LLM | 所有前序输出 | 审核结果 + 修改建议 | 审核高亮质量、解析准确性、标注一致性、遗漏检查 | **最强模型** |
| refinement | LLM | 审核结果 + 所有前序输出 | 修正后的输出 | 根据审核建议修正问题（仅执行一轮） | **最强模型** |
| daily_projection | 确定性 | 所有节点输出 | daily_reader payload | 组装最终 payload，投影为前端协议格式 | 无（不调用 LLM） |

### 质量审核节点设计

quality_review 是整个 workflow 的核心质量保障节点。由于没有人工审核，AI 审核必须覆盖以下维度：

```python
class QualityReviewResult(BaseModel):
    passed: bool
    issues: list[QualityIssue]
    overall_score: float

class QualityIssue(BaseModel):
    dimension: str
    severity: str
    description: str
    suggestion: str

REVIEW_DIMENSIONS = [
    "highlight_accuracy",
    "highlight_density",
    "footer_completeness",
    "footer_accuracy",
    "interpretation_coherence",
    "annotation_consistency",
]
```

审核判定逻辑：

- `passed=True`：无严重问题，直接进入 daily_projection
- `passed=False`：存在可修正问题，进入 refinement
- 如果 refinement 后仍不通过（由 daily_projection 的后置检查判定），则该文章标记为 `draft` 状态，Pipeline 尝试下一篇候选

### Refinement 约束

- **仅执行一轮**：refinement → daily_projection → END，不再二次审核
- refinement 节点只修正 quality_review 指出的具体问题，不重新生成全部内容
- 如果问题无法修正（如文章本身不适合精读），refinement 可以返回 `abort=True`，Pipeline 尝试下一篇候选

### 模型路由配置

Daily Reader 使用独立的模型路由，复用现有 `ModelRoute` + `ModelSelection` 体系：

```python
# 新增 ModelRoute 值
ModelRoute = Literal[
    "annotation_generation",
    "daily_annotation",
    "daily_analysis",
    "daily_review",
]

# 路由与节点映射
DAILY_READER_MODEL_ROUTES = {
    "vocab_highlight": "daily_annotation",
    "phrase_context_gloss": "daily_annotation",
    "footer_analysis": "daily_analysis",
    "full_interpretation": "daily_analysis",
    "quality_review": "daily_review",
    "refinement": "daily_review",
}
```

配置示例（`model_profiles_json`）：

```json
{
  "daily_annotation": {
    "profile": "claude_sonnet",
    "model_settings": {"temperature": 0.3}
  },
  "daily_analysis": {
    "profile": "claude_opus",
    "model_settings": {"temperature": 0.5}
  },
  "daily_review": {
    "profile": "claude_opus",
    "model_settings": {"temperature": 0.2}
  }
}
```

设计要点：

- `daily_annotation`：词汇/短语标注，可用标准模型（如 Claude Sonnet），temperature 偏低保证一致性
- `daily_analysis`：文末解析 + 全篇解析，用最强模型（如 Claude Opus），temperature 适中保证创造性
- `daily_review`：质量审核，用最强模型，temperature 最低保证判断准确性
- 所有路由支持 `fallback_profiles`，与主线模型路由体系完全一致

### Prompt 策略要点

Daily Reader 专用 Prompt 与主线的关键差异：

| 维度 | 主线 Learning | Daily Reader |
|------|--------------|--------------|
| 标注密度 | 按用户目标动态调整 | 固定克制（每段 3-5 个） |
| 语法标注 | 包含 grammar_note | 不包含 |
| 翻译 | 逐句翻译 | 不逐句翻译，仅短语/语境释义 |
| 全篇解析 | 无 | 核心差异化能力 |
| 文末分析 | 无 | 核心差异化能力 |
| 质量审核 | repair（条件触发） | quality_review（必经节点） |
| 优化修正 | repair 后直接投影 | refinement（条件触发，仅一轮） |
| 输入质量假设 | 不稳定，需防御 | 已筛选+安全检测通过，高质量 |

## API Design

### 用户侧 API

#### GET /daily-reader/today

获取今日精读文章列表（2-3 篇）。

响应体：

```python
class DailyReaderArticleResponse(BaseModel):
    id: str
    title: str
    subtitle: str | None
    source: str
    source_url: str
    publish_date: date
    difficulty: str
    read_time_minutes: int
    tags: list[str]
    cover_image_url: str | None
    cover_theme: str
    body: dict
    highlights: list[dict]
    footer_analysis: dict

class DailyReaderTodayResponse(BaseModel):
    articles: list[DailyReaderArticleResponse]
```

无今日文章时返回空列表。

#### GET /daily-reader/{id}

获取指定文章的完整 payload。

#### GET /daily-reader

获取已发布文章列表（分页）。

查询参数：

- `cursor`: 游标（publish_date，可选）
- `limit`: 每页条数，默认 10

响应体：

```python
class DailyReaderListItem(BaseModel):
    id: str
    title: str
    subtitle: str | None
    source: str
    publish_date: date
    difficulty: str
    read_time_minutes: int
    tags: list[str]
    cover_image_url: str | None
    cover_theme: str

class DailyReaderListResponse(BaseModel):
    items: list[DailyReaderListItem]
    cursor: str | None
    has_more: bool
```

### 管理 API

#### POST /daily-reader/admin/generate

触发 Pipeline 生成今日文章（2-3 篇）。

请求体：

```python
class DailyReaderGenerateRequest(BaseModel):
    force: bool = False
    source_preference: str | None = None
    max_count: int = 3
```

响应体：

```python
class DailyReaderGenerateResponse(BaseModel):
    task_id: str
    status: str
    message: str
```

此接口为异步执行，返回 task_id 供轮询状态。

#### POST /daily-reader/admin/publish

发布指定文章为今日精读。

请求体：

```python
class DailyReaderPublishRequest(BaseModel):
    id: str
```

#### POST /daily-reader/admin/unpublish

取消发布指定文章（将 status 改回 draft）。

请求体：

```python
class DailyReaderUnpublishRequest(BaseModel):
    id: str
```

#### DELETE /daily-reader/admin/{id}

删除指定文章（仅 draft 状态可删除）。

#### GET /daily-reader/admin/drafts

获取所有 draft 状态文章列表（供人工审核/选择）。

#### POST /daily-reader/admin/retry

重新对指定 draft 文章执行 Workflow（如审核不通过后修复 prompt 重试）。

请求体：

```python
class DailyReaderRetryRequest(BaseModel):
    id: str
```

所有管理 API 使用 API Key 认证，预留后续接入小程序云开发-云后台调用。

## Frontend Design

### 页面结构

新增页面：`pages/daily-reader/index`

### 组件拆分

| 组件 | 职责 |
|------|------|
| `DailyReaderHeader` | 页头：标题、来源、日期、难度、时长、标签、封面图/氛围渐变 |
| `DailyReaderBody` | 正文：杂志式排版、高亮渲染、点词交互 |
| `DailyReaderFooterAnalysis` | 文末解析：摘要、结构、关键表达、全篇解析（可折叠）、讨论问题、原文来源链接 |
| `DailyReaderBottomSheet` | 底部弹窗：词典详情 / 语境解释（已替换为复用 WordPopup） |
| `DailyReaderProgress` | 阅读进度条 |
| `DailyReaderHighlightWord` | 高亮词组件：轻量背景色块，点击触发 mini 卡片 |

### 词典交互

精读页复用现有 `WordPopup` 组件，通过 `daily-reader-highlight.adapter.ts` 将 `DailyReaderHighlight` 转换为 `InlineMarkModel`：

- 点击高亮词 → `highlightToInlineMark()` 转换 → `WordPopup mode='mini'` 展示 AI 标注 + 词典摘要
- 点击 mini 卡片展开 → `WordPopup mode='full'` 展示完整词典详情
- 点击非高亮词 → `WordPopup mode='mini'` 直接调用 `/dict` API 查询

### 首页入口

改造 `pages/home/index.tsx` 中的推荐卡片区域：

- 替换硬编码 mock 数据为 `GET /daily-reader/today` 动态数据
- 展示 2-3 张杂志封面式卡片（横向滑动或纵向排列），每张含标题+来源+难度+封面图/渐变
- 卡片视觉：杂志封面式（非列表），与主线输入区视觉明显区分
- 点击导航到 `pages/daily-reader/index?id={articleId}`
- 无今日文章时优雅降级（隐藏卡片区域或显示 fallback）
- "每日精选"标题旁显示"更多 →"链接，导航到归档页

### 归档页

新增 `pages/daily-reader-archive/index`：

- 展示所有已发布文章（逆序分页），每条含标题、来源、日期、难度、阅读时长、封面缩略图
- 使用 `GET /daily-reader` 分页 API
- 点击文章跳转到精读页
- 精读页底部也有"往期精选 →"入口指向归档页

### 状态管理

新增 `client/src/stores/daily-reader.ts`：

```typescript
interface DailyReaderState {
  todayArticles: DailyReaderArticle[]
  articleList: DailyReaderListItem[]
  loading: boolean
  error: string | null
  fetchToday: () => Promise<void>
  fetchList: (cursor?: string) => Promise<void>
}
```

### 类型定义

新增 `client/src/types/api/daily-reader.dto.ts` 和 `client/src/types/view/daily-reader.vm.ts`。

### 分享

使用 Taro 的 `Button open-type="share"` 配合 `onShareAppMessage` 生命周期：

- 分享标题：文章标题
- 分享描述：文章副标题/摘要
- 分享路径：`/pages/daily-reader/index?id={articleId}`

## Code Architecture

### Backend Modules

新增文件：

- `server/db/migrations/0003_daily_reader.sql` — daily_readers 表
- `server/app/schemas/daily_reader.py` — Pydantic models
- `server/app/services/daily_reader/service.py` — CRUD 业务逻辑
- `server/app/services/daily_reader/pipeline.py` — 文章拉取 Pipeline（含来源轮换和封面图优先逻辑）
- `server/app/services/daily_reader/discovery.py` — 发现层（Guardian API + RSS）
- `server/app/services/daily_reader/extraction.py` — 提取层（trafilatura）
- `server/app/services/daily_reader/content_security.py` — 微信内容安全检测
- `server/app/services/daily_reader/scoring.py` — 筛选层（AI 评分）
- `server/app/workflow/daily_reader_workflow.py` — 专用 LangGraph 图
- `server/app/agents/daily_vocab_agent.py` — 词汇高亮 Agent
- `server/app/agents/daily_footer_agent.py` — 文末分析 Agent
- `server/app/agents/daily_interpretation_agent.py` — 全篇解析 Agent
- `server/app/agents/daily_review_agent.py` — 质量审核 Agent
- `server/app/agents/daily_refinement_agent.py` — 优化修正 Agent
- `server/app/services/analysis/prompting/daily_prompt_strategy.py` — Daily 专用 Prompt 策略
- `server/app/api/routes/daily_reader.py` — 用户侧路由
- `server/app/api/routes/daily_reader_admin.py` — 管理 API 路由

修改文件：

- `server/app/api/router.py` — 注册新路由
- `server/app/llm/routes.py` — 新增 daily_annotation / daily_analysis / daily_review 路由
- `server/requirements.txt` — 新增 feedparser、trafilatura（实际为 pyproject.toml）

### Frontend Modules

新增文件：

- `client/src/pages/daily-reader/index.tsx` — 每日精读页
- `client/src/pages/daily-reader-archive/index.tsx` — 往期精选归档页
- `client/src/components/DailyReaderHeader/index.tsx` — 页头组件
- `client/src/components/DailyReaderBody/index.tsx` — 正文组件
- `client/src/components/DailyReaderFooterAnalysis/index.tsx` — 文末解析组件
- `client/src/components/DailyReaderBottomSheet/index.tsx` — 底部弹窗（已替换为 WordPopup 复用）
- `client/src/components/DailyReaderProgress/index.tsx` — 进度条
- `client/src/components/DailyReaderHighlightWord/index.tsx` — 高亮词组件
- `client/src/stores/daily-reader.ts` — Zustand store
- `client/src/services/api/daily-reader.client.ts` — API client
- `client/src/services/api/adapters/daily-reader.adapter.ts` — DTO → VM 转换
- `client/src/services/api/adapters/daily-reader-highlight.adapter.ts` — Highlight → InlineMarkModel 适配
- `client/src/types/api/daily-reader.dto.ts` — 后端 DTO
- `client/src/types/view/daily-reader.vm.ts` — 前端 VM

修改文件：

- `client/src/app.config.ts` — 注册新页面
- `client/src/pages/home/index.tsx` — 替换静态卡片为动态数据

## Rollout Strategy

按四阶段交付：

### Phase 1 — 文章拉取 Pipeline + 专用 Workflow + 数据入库

- 创建 migration
- Pipeline 四层实现（discovery → extraction → content_security → scoring）
- Daily Reader Workflow 8 节点实现（含 quality_review + refinement）
- 模型路由扩展（daily_annotation / daily_analysis / daily_review）
- Pipeline 端到端验证（手动触发）

### Phase 2 — 后端 Daily Reader API

- Schema + Service + Routes
- 用户侧 API（today / by-id / list）
- 管理 API（generate / publish）

### Phase 3 — 前端每日精读页面

- 页面 + 6 个核心组件
- 点词查词交互（复用词典能力）
- 首页入口改造
- 分享功能

### Phase 4 — 验证与收尾

- 编译检查
- 端到端验证
- 视觉走查

## Test Strategy

- Python: 编译检查新增 schema / route / service / workflow
- TypeScript: `tsc --noEmit`
- Pipeline 端到端验证：
  - 手动触发 `POST /daily-reader/admin/generate` → 数据库有记录
  - `GET /daily-reader/today` → 返回今日文章 payload
  - `GET /daily-reader` → 返回文章列表
  - 内容安全检测：违规文章被过滤，安全文章通过
  - Workflow 审核：quality_review 节点正常执行，refinement 条件触发
- 前端验证：
  - 首页卡片 → 点击 → 进入每日精读页
  - 正文阅读 → 点词 → mini 卡片 → bottom sheet
  - 文末解析区 → 折叠/展开全篇解析
  - 分享 → 生成分享卡片

## Open Questions

1. **音频朗读是否纳入 V1**
   → 暂不纳入。V1 专注杂志式阅读体验，音频朗读作为 V2 增强。

2. **是否需要阅读打卡/连续天数**
   → 暂不做。避免学习压力感，与"消费型"页面定位冲突。仅做轻量进度指示。

3. **文章拉取频率**
   → 每天一次（UTC+8 8:00-9:00），手动触发作为补充。不需要更频繁。

4. **Guardian API 商用授权**
   → 初期非商用免费。如后续商业化，需与 Guardian 谈授权或切换到纯 RSS 源。

5. **微信 msgSecCheck 的 openid 来源**
   → 已决策：使用小程序管理员账号的 openid，通过定时任务（每 90 分钟）保活。

6. **原文来源链接展示**
   → 已决策：在文末解析区展示"原文来自 {source} →"可点击链接，分享卡片中也包含来源信息。

7. **管理 API 的调用方式**
   → 预留充足的 admin API 接口，后续可接入小程序云开发-云后台调用。当前阶段通过 API Key 认证 + 手动 HTTP 调用。

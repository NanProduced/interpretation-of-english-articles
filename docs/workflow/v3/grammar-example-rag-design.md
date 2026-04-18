# Grammar Example RAG 设计文档

## 1. 问题背景与目标

### 1.1 当前问题

当前系统在 `example_strategy.py` 中使用硬编码的 few-shot 示例：

```python
# 示例：考研语法示例是静态硬编码的
KAOYAN_GRAMMAR_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="grammar",
        sentence_text="The approach, which was initially designed for urban areas...",
        output_fragment='{"type": "grammar_note", "spans": [...], "label": "非限制性定语从句 + 主谓分离", ...}',
    ),
    # ... 仅 2-3 个示例
]
```

**局限性**：
- 每个 variant 仅 2-3 个语法示例，覆盖范围极有限
- 静态示例无法匹配用户输入的多样化句法结构
- 讲解风格（如考研 vs 专八 vs 雅思）的匹配依赖人工选择

### 1.2 设计目标

| 目标 | 说明 |
|------|------|
| 精准性 | 检索出的示例在"句法结构"和"讲解风格"上与目标高度相似 |
| 性能 | 不因为"全文逐句检索"导致显著延迟 |
| 可靠性 | RAG 异常时优雅回退到 baseline，不中断工作流 |
| 范围控制 | 本阶段仅增强 `grammar_note` 和 `sentence_analysis`，不涉及词汇/翻译 |

---

## 2. 集成位置设计

### 2.1 推荐集成点

```
┌─────────────────────────────────────────────────────────────────┐
│                    parallel_agents_node                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  1. build_grammar_bundle(plan)                              │  │
│  │     └──→ 调用 get_grammar_example_strategy(plan)           │  │
│  │          └──→ 当前：返回硬编码示例                          │  │
│  │                                                              │  │
│  │  2. GrammarAgentDeps(examples=...)  ←── 注入点             │  │
│  │                                                              │  │
│  │  3. _run_grammar_llm_span()                                 │  │
│  │     └──→ build_agent_prompt(examples=...)                   │  │
│  │          └──→ examples 被拼入 <examples> section           │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 两种集成方案对比

| 方案 | 位置 | 优点 | 缺点 |
|------|------|------|------|
| **A. strategy_builder 层** | `build_grammar_bundle` 内部 | 与现有策略架构一致，对 node 透明 | 无法访问 `prepared_input.sentences`（目标句子） |
| **B. _run_parallel_agents 层** | `analyze_nodes.py` 中 | 可直接访问目标句子，可做 per-sentence 增强 | 需要修改 node 代码 |

### 2.3 推荐方案：混合策略

**Phase 1（当前）：全局增强模式**

在 `_run_parallel_agents` 中，基于 **全文句子的句法特征聚合** 检索示例：

```python
# 伪代码示意
async def _run_parallel_agents(state: AnalyzeState, ...):
    prepared_input = state["prepared_input"]
    plan = state["goal_execution_plan"]
    
    # 1. 获取 baseline bundle
    grammar_bundle = build_grammar_bundle(plan)
    
    # 2. 如果启用 RAG，尝试增强示例
    if plan.few_shot_mode == "rag":
        rag_examples = await _try_retrieve_grammar_examples(
            sentences=prepared_input.sentences,
            variant_id=plan.variant_id,
            grammar_focus=plan.policy.grammar_focus,
        )
        # 合并：RAG 示例优先，不足时用 baseline 补充
        grammar_bundle = _merge_examples(grammar_bundle, rag_examples)
    
    # 3. 构建 deps
    grammar_deps = GrammarAgentDeps(
        sentences=sentences_data,
        prompt_strategy=grammar_bundle.prompt_strategy,
        examples=grammar_bundle.example_strategy.examples,
    )
```

**Phase 2（未来）：Per-Sentence 精细增强**

如果后续需要对每个句子独立检索，可扩展 `GrammarAgentDeps` 或在 prompt 层面做结构化增强。

---

## 3. 检索 Query 设计

### 3.1 语法学习的特殊性

普通文本 RAG 使用语义相似度，但语法学习的相似性维度不同：

| 维度 | 普通文本 RAG | 语法示例 RAG |
|------|-------------|--------------|
| 相似性基础 | 语义内容 | 句法结构 + 讲解风格 |
| 关键特征 | 词向量、主题 | 从句类型、结构复杂度、修辞功能 |
| 目标匹配 | "讲的是什么" | "怎么讲的、为什么这样写" |

### 3.2 Query 构造策略

#### 3.2.1 三层 Query 架构

```
┌──────────────────────────────────────────────────────────────┐
│                    Grammar RAG Query                          │
├──────────────────────────────────────────────────────────────┤
│  Layer 1: Context Filter（粗过滤）                            │
│  ├── variant_id: "kaoyan" / "ielts_toefl" / "tem" / ...    │
│  ├── grammar_focus: "structural" / "rhetorical" / ...       │
│  └── 作用：仅检索相同学习场景的示例                            │
├──────────────────────────────────────────────────────────────┤
│  Layer 2: Syntactic Signature（句法特征向量）                  │
│  ├── clause_types: [定语从句, 状语从句, 名词性从句, ...]      │
│  ├── structure_complexity: 嵌套层数 / 从句数量                │
│  ├── special_features: [倒装, 虚拟, 分词状语, 插入语, ...]   │
│  └── 作用：匹配"句法结构相似性"                                │
├──────────────────────────────────────────────────────────────┤
│  Layer 3: Semantic Boost（语义辅助增强）                      │
│  ├── 句子原文的语义向量（可选）                                 │
│  └── 作用：当结构特征不足时的 fallback                         │
└──────────────────────────────────────────────────────────────┘
```

#### 3.2.2 Syntactic Signature 详细设计

**问题**：如何在不运行完整句法分析器的情况下获取句法特征？

**方案**：轻量级规则 + LLM 结构化提取的混合策略

```python
# 轻量级句法特征提取（规则部分）
@dataclass
class SyntacticSignature:
    # 从句类型特征（可通过关键词规则检测）
    has_relative_clause: bool = False  # who/which/that/whose/where 引导定语
    has_adverbial_clause: bool = False  # because/when/if/although/while 引导
    has_noun_clause: bool = False       # that/what/whether 引导主语/宾语/同位语
    
    # 特殊结构特征
    has_inversion: bool = False         # 否定词前置 / only 前置 / 虚拟倒装
    has_subjunctive: bool = False       # would have / had done / were
    has_participle_phrase: bool = False # 现在分词/过去分词短语作状语/定语
    has_appositive: bool = False        # 同位语结构
    has_parenthetical: bool = False     # 插入语
    
    # 复杂度特征
    clause_count: int = 0               # 从句数量估计
    word_count: int = 0                 # 词数
    complexity_score: float = 0.0       # 综合复杂度分

# 规则检测示例（简化）
def _extract_signature_by_rules(text: str) -> SyntacticSignature:
    sig = SyntacticSignature()
    sig.word_count = len(text.split())
    
    # 定语从句标记词
    relative_markers = {"who", "which", "that", "whose", "whom", "where", "when"}
    words = set(re.findall(r'\b\w+\b', text.lower()))
    sig.has_relative_clause = bool(words & relative_markers)
    
    # 特殊结构：倒装标记
    inversion_patterns = [
        r'^(Rarely|Never|Seldom|Hardly|Little|Only)\s+(has|have|did|had|do|does|is|are|was|were)',
        r'^(Had|Should|Were)\s+\w+',  # 虚拟倒装
    ]
    sig.has_inversion = any(re.search(p, text) for p in inversion_patterns)
    
    return sig
```

#### 3.2.3 Query 向量化策略

**推荐方案**：混合检索（Hybrid Search）

```
┌────────────────────────────────────────────────────────────────┐
│                      Hybrid Search Pipeline                     │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  输入：目标句子列表 + 上下文信息                                  │
│       ┌──────────────────────────────────────────────────┐    │
│       │  sentences: ["The study suggests that...", ...]  │    │
│       │  variant_id: "kaoyan"                             │    │
│       │  grammar_focus: "structural"                       │    │
│       └──────────────────────────────────────────────────┘    │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Step 1: 全文句法特征聚合                                  │  │
│  │  - 对每个句子提取 SyntacticSignature                      │  │
│  │  - 聚合：统计全文主要结构类型（如"3句含定语从句，2句含分词 │  │
│  │    状语"）                                                 │  │
│  │  - 输出：AggregatedSyntacticProfile                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Step 2: 构造检索 Query                                    │  │
│  │                                                             │  │
│  │  Query A: 预过滤（Metadata Filter）                        │  │
│  │  ├── variant_id == "kaoyan"                                │  │
│  │  └── grammar_focus in ["structural", "explicit_exam"]    │  │
│  │                                                             │  │
│  │  Query B: 结构向量（Dense Vector）                         │  │
│  │  ├── 把 SyntacticSignature 转为结构化文本描述               │  │
│  │  │   例："包含定语从句、分词状语，复杂度中等"                │  │
│  │  └── 使用 Embedding 模型向量化                              │  │
│  │                                                             │  │
│  │  Query C: 语义向量（可选 Dense Vector）                     │  │
│  │  └── 代表性句子（最长/最复杂的 1-2 句）的语义向量          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Step 3: 混合检索与重排                                    │  │
│  │  - 先 Query A 过滤候选集                                   │  │
│  │  - 再 Query B + Query C 做相似度检索                       │  │
│  │  - 可选：Cross-Encoder 做精细重排（成本较高）               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

#### 3.2.4 为什么用"结构化文本描述"而非 One-hot？

| 方案 | 优点 | 缺点 |
|------|------|------|
| One-hot 编码 | 精确、稀疏 | 难以泛化（"定语从句"与"非限制性定语从句"是完全不同的向量） |
| **结构化文本描述** | 语义可泛化、与现有 Embedding 模型兼容 | 需要构造自然语言 |

**示例**：
```python
# SyntacticSignature 转结构化描述
def _signature_to_text(sig: SyntacticSignature) -> str:
    features = []
    if sig.has_relative_clause:
        features.append("包含定语从句")
    if sig.has_adverbial_clause:
        features.append("包含状语从句")
    if sig.has_noun_clause:
        features.append("包含名词性从句")
    if sig.has_inversion:
        features.append("使用倒装结构")
    if sig.has_subjunctive:
        features.append("使用虚拟语气")
    if sig.has_participle_phrase:
        features.append("包含分词短语")
    
    if sig.word_count > 30:
        complexity = "长难句"
    elif sig.word_count > 20:
        complexity = "中等复杂句"
    else:
        complexity = "简单句"
    
    if not features:
        return f"这是一个{complexity}，结构相对简单"
    return f"这是一个{complexity}，{'、'.join(features)}"
```

---

## 4. 数据模型建议

### 4.1 示例库 Schema

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


# ========== 核心数据模型 ==========

class GrammarExampleIndex(BaseModel):
    """RAG 索引中的语法示例条目。
    
    存储在 Vector DB 中，用于检索。
    """
    
    # 主键
    example_id: str = Field(description="示例唯一标识")
    
    # ========== 检索用字段（Filter + Vector）==========
    # Layer 1: Context Filter（精确匹配）
    variant_id: str = Field(
        description="学习场景：beginner_reading, kaoyan, cet, kaoyan, tem, ielts_toefl, academic"
    )
    grammar_focus: str = Field(
        description="语法侧重点：explicit_split, balanced, structural_logic, explicit_exam, speed_support, structural, rhetorical, info_extraction"
    )
    
    # Layer 2: Syntactic Signature（用于生成结构向量）
    syntactic_signature: dict = Field(
        description="句法特征的 JSON 表示，对应 SyntacticSignature"
    )
    structure_description: str = Field(
        description="结构的自然语言描述，用于 Embedding"
    )
    
    # Layer 3: Semantic（用于生成语义向量）
    sentence_text: str = Field(description="示例句子原文")
    
    # ========== 业务字段 ==========
    example_type: Literal["grammar", "sentence_analysis"] = Field(
        description="示例类型：grammar_note 或 sentence_analysis"
    )
    
    # 输出示例（用于 few-shot）
    output_fragment: str = Field(
        description="JSON 格式的输出示例，与当前 ExampleEntry.output_fragment 兼容"
    )
    
    # 元数据
    source: Optional[str] = Field(
        default=None,
        description="来源：如 'manual_curated', 'user_contributed', 'generated'"
    )
    quality_score: Optional[float] = Field(
        default=None,
        description="质量评分，可用于重排"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    
    # ========== 向量字段（由 Vector DB 管理）==========
    # structure_vector: List[float]  # structure_description 的 Embedding
    # semantic_vector: List[float]   # sentence_text 的 Embedding


class GrammarExampleRetrievalResult(BaseModel):
    """检索结果封装。"""
    
    example_id: str
    example_type: Literal["grammar", "sentence_analysis"]
    sentence_text: str
    output_fragment: str
    
    # 检索元数据
    similarity_score: float
    matched_structure: str
    matched_variant: str


class RagAugmentedExampleStrategy(BaseModel):
    """RAG 增强后的示例策略。
    
    与现有 ExampleStrategy 兼容，但增加来源追踪。
    """
    
    examples: list[dict] = Field(
        description="ExampleEntry 格式的示例列表"
    )
    selection_mode: Literal["baseline", "rag", "manual"] = "rag"
    
    # RAG 特定字段
    rag_metadata: dict = Field(
        default_factory=dict,
        description="RAG 过程元数据：{retrieved_count: int, fallback_to_baseline: bool, errors: list}"
    )
```

### 4.2 数据流转图

```
┌────────────────────────────────────────────────────────────────────────┐
│                         数据流转：示例库构建                              │
├────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐                                                   │
│  │  现有硬编码示例   │  example_strategy.py 中的 BEGINNER_, KAOYAN_ 等  │
│  │  (Baseline)      │                                                   │
│  └────────┬─────────┘                                                   │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Step 1: 示例增强与结构化                                           │  │
│  │  - 为每个硬编码示例提取 SyntacticSignature                          │  │
│  │  - 生成 structure_description                                       │  │
│  │  - 补充 variant_id / grammar_focus 元数据                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Step 2: 向量化与索引                                               │  │
│  │  - structure_description → structure_vector (Embedding)           │  │
│  │  - sentence_text → semantic_vector (Embedding)                    │  │
│  │  - 写入 Vector DB（如 Chroma / FAISS / Pinecone）                 │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│                         数据流转：检索时                                  │
├────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  输入：目标句子列表 + variant_id + grammar_focus                         │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Step 1: 目标特征提取                                               │  │
│  │  - 对每个目标句子提取 SyntacticSignature                           │  │
│  │  - 聚合成 AggregatedSyntacticProfile                               │  │
│  │  - 生成 query_structure_description                                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Step 2: 混合检索                                                   │  │
│  │  Filter: variant_id + grammar_focus                                │  │
│  │  Vector: structure_vector 相似度（主） + semantic_vector（辅）     │  │
│  │  Top-K: 3-5 个结果                                                 │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Step 3: 结果融合                                                   │  │
│  │  - 如果 RAG 结果数量充足 → 使用 RAG 示例                            │  │
│  │  - 如果数量不足 → 用 baseline 示例补充                               │  │
│  │  - 去重：避免重复的结构类型                                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│           │                                                              │
│           ▼                                                              │
│  输出：RagAugmentedExampleStrategy → 注入 GrammarAgentDeps              │
│                                                                          │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 5. 性能优化策略

### 5.1 性能约束分析

当前工作流的性能特点：

| 环节 | 当前耗时 | RAG 可能增加的开销 |
|------|----------|-------------------|
| 输入准备 | ~10ms | - |
| 特征提取 | - | ~50-100ms（规则 + 轻量处理） |
| **检索** | - | **关键瓶颈** |
| LLM 调用 | 主要耗时 | 不变 |
| 后处理 | ~50ms | - |

**核心问题**：全文逐句检索（假设 10 句 × 每次检索 100ms = 额外 1s）不可接受。

### 5.2 优化方案：全文聚合检索

#### 方案核心

```
当前设计（逐句检索，性能差）：
┌────────────────────────────────────────────────────────────┐
│  Sentence 1 → 特征提取 → 检索 → 结果 1                      │
│  Sentence 2 → 特征提取 → 检索 → 结果 2                      │
│  Sentence 3 → 特征提取 → 检索 → 结果 3                      │
│  ...                                                         │
│  Sentence N → 特征提取 → 检索 → 结果 N                      │
│  问题：N 次检索调用，延迟线性增长                             │
└────────────────────────────────────────────────────────────┘

优化设计（聚合检索，性能好）：
┌────────────────────────────────────────────────────────────┐
│  Sentence 1 → 特征提取 ─┐                                    │
│  Sentence 2 → 特征提取 ─┤                                    │
│  Sentence 3 → 特征提取 ─┼→ 聚合 → 生成聚合 Query → 1 次检索 │
│  ...                    │                                    │
│  Sentence N → 特征提取 ─┘                                    │
│  优势：仅 1 次检索调用，延迟恒定                              │
└────────────────────────────────────────────────────────────┘
```

#### 聚合策略详细设计

```python
@dataclass
class AggregatedSyntacticProfile:
    """全文句法特征聚合结果。"""
    
    # 主要结构类型（按出现频率排序）
    dominant_structures: list[str]
    
    # 复杂度分布
    complexity_distribution: dict[str, int]  # {"simple": 3, "medium": 5, "complex": 2}
    
    # 特殊结构标记
    has_special_structures: list[str]  # ["inversion", "subjunctive", "participle"]
    
    # 代表性句子（用于语义向量）
    representative_sentences: list[str]  # 最长/最复杂的 1-2 句


def aggregate_syntactic_profiles(
    signatures: list[SyntacticSignature],
    sentences: list[str],
) -> AggregatedSyntacticProfile:
    """聚合多个句子的句法特征。"""
    
    # 1. 统计结构频率
    structure_counts = Counter()
    for sig in signatures:
        if sig.has_relative_clause:
            structure_counts["relative_clause"] += 1
        if sig.has_adverbial_clause:
            structure_counts["adverbial_clause"] += 1
        if sig.has_noun_clause:
            structure_counts["noun_clause"] += 1
        if sig.has_inversion:
            structure_counts["inversion"] += 1
        if sig.has_subjunctive:
            structure_counts["subjunctive"] += 1
        if sig.has_participle_phrase:
            structure_counts["participle_phrase"] += 1
    
    # 2. 按频率排序的主要结构
    dominant_structures = [
        struct for struct, count in structure_counts.most_common(3)
        if count > 0
    ]
    
    # 3. 复杂度分布
    complexity_counts = {"simple": 0, "medium": 0, "complex": 0}
    for sig in signatures:
        if sig.word_count > 30:
            complexity_counts["complex"] += 1
        elif sig.word_count > 20:
            complexity_counts["medium"] += 1
        else:
            complexity_counts["simple"] += 1
    
    # 4. 特殊结构标记
    special_structures = []
    if structure_counts.get("inversion", 0) > 0:
        special_structures.append("inversion")
    if structure_counts.get("subjunctive", 0) > 0:
        special_structures.append("subjunctive")
    
    # 5. 代表性句子（最长的 2 句）
    sentence_with_len = [(s, len(s.split())) for s in sentences]
    sentence_with_len.sort(key=lambda x: x[1], reverse=True)
    representative_sentences = [s for s, _ in sentence_with_len[:2]]
    
    return AggregatedSyntacticProfile(
        dominant_structures=dominant_structures,
        complexity_distribution=complexity_counts,
        has_special_structures=special_structures,
        representative_sentences=representative_sentences,
    )


def build_aggregated_query(profile: AggregatedSyntacticProfile) -> str:
    """从聚合特征构建检索 Query 文本。"""
    parts = []
    
    # 描述复杂度
    total = sum(profile.complexity_distribution.values())
    complex_ratio = profile.complexity_distribution["complex"] / total if total > 0 else 0
    if complex_ratio > 0.5:
        parts.append("这是一篇包含较多长难句的文章")
    elif complex_ratio > 0.2:
        parts.append("这是一篇包含一些长难句的文章")
    else:
        parts.append("这是一篇结构相对简单的文章")
    
    # 描述主要结构
    if profile.dominant_structures:
        structure_names = {
            "relative_clause": "定语从句",
            "adverbial_clause": "状语从句",
            "noun_clause": "名词性从句",
            "participle_phrase": "分词短语",
        }
        structures_zh = [structure_names.get(s, s) for s in profile.dominant_structures]
        parts.append(f"主要句子结构包括：{'、'.join(structures_zh)}")
    
    # 特殊结构
    if "inversion" in profile.has_special_structures:
        parts.append("包含倒装结构")
    if "subjunctive" in profile.has_special_structures:
        parts.append("包含虚拟语气")
    
    return "。".join(parts)
```

### 5.3 额外性能优化

| 优化策略 | 预期效果 | 实现复杂度 |
|----------|----------|------------|
| **聚合检索（核心）** | 从 N 次检索降至 1 次 | 中 |
| 本地缓存 | 相同 Query 直接返回 | 低 |
| 异步检索 | 与 LLM 调用重叠（如果可行） | 中 |
| 轻量级 Embedding 模型 | 比 text-embedding-3-small 更快 | 中 |

---

## 6. Fallback 与错误处理设计

### 6.1 设计原则

```
RAG 增强 = 锦上添花，而非必需品

原则 1: 任何 RAG 错误不应导致工作流中断
原则 2: 始终有 baseline 作为保底
原则 3: 错误应被记录和监控，但不暴露给用户
```

### 6.2 错误场景与处理策略

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any
import logging
import asyncio

logger = logging.getLogger(__name__)


class RagErrorType(Enum):
    """RAG 错误类型。"""
    CONFIG_ERROR = "config_error"       # 配置错误（如 Vector DB 未初始化）
    RETRIEVAL_ERROR = "retrieval_error" # 检索调用失败
    TIMEOUT_ERROR = "timeout_error"     # 检索超时
    INSUFFICIENT_RESULTS = "insufficient_results"  # 结果数量不足


@dataclass
class RagRetrievalOutcome:
    """RAG 检索结果封装。"""
    success: bool
    examples: list[dict]  # ExampleEntry 格式
    error_type: Optional[RagErrorType] = None
    error_message: Optional[str] = None
    used_fallback: bool = False


async def try_retrieve_grammar_examples_with_fallback(
    sentences: list[dict],
    variant_id: str,
    grammar_focus: str,
    baseline_examples: list[dict],
    retrieval_timeout: float = 2.0,  # 严格超时：2 秒
    min_required_examples: int = 2,
) -> RagRetrievalOutcome:
    """
    尝试 RAG 检索，失败时自动 fallback 到 baseline。
    
    核心设计：
    1. 严格超时（2 秒），避免阻塞整个工作流
    2. 所有异常被捕获，不向上抛出
    3. 结果数量不足时用 baseline 补充
    """
    
    # ========== Step 1: 检查 RAG 是否可用 ==========
    rag_service = get_rag_service()  # 获取全局 RAG 服务实例
    if rag_service is None or not rag_service.is_available():
        logger.warning("RAG service not available, using baseline examples")
        return RagRetrievalOutcome(
            success=False,
            examples=baseline_examples,
            error_type=RagErrorType.CONFIG_ERROR,
            error_message="RAG service not configured or unavailable",
            used_fallback=True,
        )
    
    # ========== Step 2: 尝试检索（带超时）==========
    try:
        # 特征提取（本地计算，不计入检索超时）
        signatures = [_extract_signature_by_rules(s["text"]) for s in sentences]
        profile = aggregate_syntactic_profiles(
            signatures,
            [s["text"] for s in sentences],
        )
        query_text = build_aggregated_query(profile)
        
        # 检索调用（严格超时）
        retrieved_examples = await asyncio.wait_for(
            rag_service.retrieve(
                query_text=query_text,
                variant_id=variant_id,
                grammar_focus=grammar_focus,
                top_k=5,
            ),
            timeout=retrieval_timeout,
        )
        
        # ========== Step 3: 检查结果充足性 ==========
        if len(retrieved_examples) >= min_required_examples:
            # 结果充足：使用 RAG 结果
            logger.info(
                f"RAG retrieval successful: {len(retrieved_examples)} examples retrieved "
                f"for variant={variant_id}, focus={grammar_focus}"
            )
            return RagRetrievalOutcome(
                success=True,
                examples=retrieved_examples,
                used_fallback=False,
            )
        else:
            # 结果不足：混合 RAG + baseline
            logger.warning(
                f"RAG returned only {len(retrieved_examples)} examples "
                f"(need {min_required_examples}), supplementing with baseline"
            )
            
            # 去重合并
            seen_sentences = {e["sentence_text"] for e in retrieved_examples}
            supplementary = [
                e for e in baseline_examples
                if e["sentence_text"] not in seen_sentences
            ][: (min_required_examples - len(retrieved_examples))]
            
            merged = retrieved_examples + supplementary
            
            return RagRetrievalOutcome(
                success=True,  # 部分成功也算成功
                examples=merged,
                error_type=RagErrorType.INSUFFICIENT_RESULTS,
                error_message=f"Insufficient results: {len(retrieved_examples)} < {min_required_examples}",
                used_fallback=True,
            )
    
    except asyncio.TimeoutError:
        logger.error(f"RAG retrieval timed out after {retrieval_timeout}s")
        return RagRetrievalOutcome(
            success=False,
            examples=baseline_examples,
            error_type=RagErrorType.TIMEOUT_ERROR,
            error_message=f"Retrieval timed out after {retrieval_timeout}s",
            used_fallback=True,
        )
    
    except Exception as e:
        logger.exception("RAG retrieval failed with unexpected error")
        return RagRetrievalOutcome(
            success=False,
            examples=baseline_examples,
            error_type=RagErrorType.RETRIEVAL_ERROR,
            error_message=str(e),
            used_fallback=True,
        )
```

### 6.3 状态流转图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        RAG 执行状态流转                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  起始状态                                                                 │
│      │                                                                    │
│      ▼                                                                    │
│  ┌─────────────────┐                                                      │
│  │ 检查 RAG 可用性 │                                                      │
│  └────────┬────────┘                                                      │
│           │                                                                │
│     ┌─────┴─────┐                                                         │
│     │           │                                                         │
│   可用        不可用                                                       │
│     │           │                                                         │
│     │           ▼                                                         │
│     │    ┌──────────────────┐                                             │
│     │    │  Return Baseline │ ←── Fallback 1: 配置错误                  │
│     │    └──────────────────┘                                             │
│     │                                                                      │
│     ▼                                                                      │
│  ┌─────────────────┐                                                      │
│  │  特征提取       │  ←── 本地计算，不会超时                              │
│  │  构建 Query     │                                                       │
│  └────────┬────────┘                                                      │
│           │                                                                │
│           ▼                                                                │
│  ┌─────────────────────────┐                                               │
│  │  调用 Vector DB 检索    │  ←── 带 2s 超时                             │
│  │  (with timeout)         │                                               │
│  └────────┬────────────────┘                                               │
│           │                                                                 │
│     ┌─────┴─────┬──────────┐                                               │
│     │           │          │                                               │
│   成功        超时      异常                                                │
│     │           │          │                                               │
│     │           ▼          ▼                                               │
│     │    ┌──────────────────────────┐                                     │
│     │    │  Return Baseline         │ ←── Fallback 2: 运行时错误         │
│     │    │  (记录错误日志)           │                                     │
│     │    └──────────────────────────┘                                     │
│     │                                                                      │
│     ▼                                                                      │
│  ┌─────────────────┐                                                      │
│  │ 结果数量检查    │                                                      │
│  └────────┬────────┘                                                      │
│           │                                                                │
│     ┌─────┴─────┐                                                         │
│     │           │                                                         │
│   充足        不足                                                         │
│     │           │                                                         │
│     │           ▼                                                         │
│     │    ┌──────────────────────────┐                                     │
│     │    │  RAG 结果 + Baseline 补充 │ ←── Fallback 3: 结果不足          │
│     │    └──────────────────────────┘                                     │
│     │                                                                      │
│     ▼                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  构建 RagAugmentedExampleStrategy，注入 GrammarAgentDeps          │   │
│  │  - 记录 rag_metadata（是否使用 fallback、错误类型等）               │   │
│  │  - 用于后续监控和分析                                               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.4 监控与可观测性

```python
# RAG 过程中收集的元数据示例
rag_metadata = {
    "attempted": True,
    "success": True,
    "used_fallback": False,
    "error_type": None,
    "error_message": None,
    
    # 性能指标
    "retrieval_latency_ms": 150,
    "feature_extraction_ms": 80,
    
    # 结果指标
    "retrieved_count": 4,
    "baseline_supplement_count": 0,
    "similarity_scores": [0.85, 0.78, 0.72, 0.65],
    
    # 匹配特征
    "matched_structures": ["定语从句", "分词状语"],
    "query_text": "这是一篇包含较多长难句的文章，主要句子结构包括：定语从句、分词状语",
}

# 这些元数据会：
# 1. 存入 LangSmith trace（通过 current_run）
# 2. 写入应用日志
# 3. 可用于后续 A/B 测试分析
```

---

## 7. 集成到现有代码的详细方案

### 7.1 需要修改/新增的文件

| 文件路径 | 操作 | 说明 |
|----------|------|------|
| `app/services/analysis/prompting/example_strategy.py` | 修改 | 扩展 `get_grammar_example_strategy` 支持 RAG 模式 |
| `app/workflow/analyze_nodes.py` | 修改 | 在 `_run_parallel_agents` 中集成 RAG 检索 |
| `app/services/analysis/rag/` | **新增** | RAG 相关模块目录 |
| `app/services/analysis/rag/__init__.py` | 新增 | 模块初始化 |
| `app/services/analysis/rag/grammar_rag_service.py` | 新增 | 核心 RAG 服务 |
| `app/services/analysis/rag/syntactic_extractor.py` | 新增 | 句法特征提取器 |
| `app/config/settings.py` | 修改 | 添加 RAG 相关配置项 |

### 7.2 关键代码修改点

#### 修改 1: `analyze_nodes.py` - 集成 RAG

```python
# 在 _run_parallel_agents 中

async def _run_parallel_agents(
    state: AnalyzeState,
    model_selection: ModelSelection | None,
) -> dict[str, Any]:
    """并行运行三个 agent。"""
    prepared_input = state["prepared_input"]
    plan = state["goal_execution_plan"]

    sentences_data = [
        {"sentence_id": s.sentence_id, "text": s.text}
        for s in prepared_input.sentences
    ]

    vocab_bundle = build_vocabulary_bundle(plan)
    grammar_bundle = build_grammar_bundle(plan)
    translation_bundle = build_translation_bundle(plan)

    # ========== 新增：RAG 增强语法示例 ==========
    if plan.few_shot_mode == "rag":
        from app.services.analysis.rag import get_grammar_rag_service
        
        rag_service = get_grammar_rag_service()
        if rag_service and rag_service.is_available():
            # 尝试 RAG 检索，失败时自动 fallback
            rag_outcome = await rag_service.retrieve_with_fallback(
                sentences=sentences_data,
                variant_id=plan.variant_id,
                grammar_focus=plan.policy.grammar_focus,
                baseline_examples=[
                    e.__dict__ for e in grammar_bundle.example_strategy.examples
                ],
            )
            
            # 替换 example_strategy
            grammar_bundle = StrategyBundle(
                prompt_strategy=grammar_bundle.prompt_strategy,
                example_strategy=ExampleStrategy(
                    examples=[ExampleEntry(**e) for e in rag_outcome.examples],
                    selection_mode="rag" if rag_outcome.success else "baseline",
                ),
            )
            
            # 记录 RAG 元数据（用于 trace）
            state["_rag_metadata"] = {
                "success": rag_outcome.success,
                "used_fallback": rag_outcome.used_fallback,
                "error_type": rag_outcome.error_type.value if rag_outcome.error_type else None,
            }
    # ========== RAG 增强结束 ==========

    vocab_deps = VocabularyAgentDeps(
        sentences=sentences_data,
        prompt_strategy=vocab_bundle.prompt_strategy,
        examples=vocab_bundle.example_strategy.examples,
    )
    grammar_deps = GrammarAgentDeps(
        sentences=sentences_data,
        prompt_strategy=grammar_bundle.prompt_strategy,
        examples=grammar_bundle.example_strategy.examples,
    )
    # ... 后续不变
```

#### 修改 2: 新增 `syntactic_extractor.py`

```python
"""轻量级句法特征提取器。"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class SyntacticSignature:
    """句子的句法特征签名。"""
    
    # 从句类型
    has_relative_clause: bool = False
    has_adverbial_clause: bool = False
    has_noun_clause: bool = False
    
    # 特殊结构
    has_inversion: bool = False
    has_subjunctive: bool = False
    has_participle_phrase: bool = False
    has_appositive: bool = False
    has_parenthetical: bool = False
    
    # 复杂度
    clause_count: int = 0
    word_count: int = 0
    complexity_score: float = 0.0
    
    def to_dict(self) -> dict:
        return asdict(self)


class SyntacticExtractor:
    """轻量级句法特征提取器。"""
    
    # 定语从句关系代词
    RELATIVE_PRONOUNS = {"who", "whom", "whose", "which", "that", "where", "when", "why"}
    
    # 状语从句连词
    ADVERBIAL_CONJUNCTIONS = {
        "because", "since", "as", "when", "while", "if", "unless",
        "although", "though", "even", "until", "before", "after",
    }
    
    # 名词性从句引导词
    NOUN_CLAUSE_MARKERS = {"that", "what", "whether", "if", "who", "how", "why"}
    
    # 倒装模式
    INVERSION_PATTERNS = [
        re.compile(r'^(Rarely|Never|Seldom|Hardly|Little|Scarcely|Only)\s+(has|have|did|had|do|does|is|are|was|were|will|would|could|can|may|might)', re.IGNORECASE),
        re.compile(r'^(Had|Should|Were)\s+\w+', re.IGNORECASE),  # 虚拟倒装
    ]
    
    # 虚拟语气标记
    SUBJUNCTIVE_PATTERNS = [
        re.compile(r'\bwould\s+have\s+\w+ed', re.IGNORECASE),
        re.compile(r'\bcould\s+have\s+\w+ed', re.IGNORECASE),
        re.compile(r'\bshould\s+have\s+\w+ed', re.IGNORECASE),
    ]
    
    def extract(self, text: str) -> SyntacticSignature:
        """从句子文本提取句法特征。"""
        sig = SyntacticSignature()
        
        # 词数
        words = re.findall(r'\b[a-zA-Z]+\b', text)
        sig.word_count = len(words)
        word_set = set(w.lower() for w in words)
        
        # 定语从句检测
        sig.has_relative_clause = bool(word_set & self.RELATIVE_PRONOUNS)
        
        # 状语从句检测
        sig.has_adverbial_clause = bool(word_set & self.ADVERBIAL_CONJUNCTIONS)
        
        # 名词性从句检测
        sig.has_noun_clause = bool(word_set & self.NOUN_CLAUSE_MARKERS)
        
        # 倒装检测
        sig.has_inversion = any(p.search(text) for p in self.INVERSION_PATTERNS)
        
        # 虚拟语气检测
        sig.has_subjunctive = any(p.search(text) for p in self.SUBJUNCTIVE_PATTERNS)
        
        # 分词短语检测（简化：看句首是否有 -ed/-ing 形式）
        first_word_match = re.match(r'^([A-Za-z]+(?:ed|ing))\b', text.strip())
        if first_word_match:
            first_word = first_word_match.group(1).lower()
            # 排除常见的形容词（如 interesting, interested 作为形容词）
            # 简单策略：只要是 -ed/-ing 开头，且不是常见介词/连词
            not_ignored = first_word not in {"according", "including", "regarding"}
            sig.has_participle_phrase = not_ignored
        
        # 复杂度评分
        clause_markers_count = sum([
            sig.has_relative_clause,
            sig.has_adverbial_clause,
            sig.has_noun_clause,
        ])
        sig.clause_count = clause_markers_count
        
        # 综合复杂度分 (0-1)
        complexity_components = [
            clause_markers_count * 0.2,
            min(sig.word_count / 30, 1.0) * 0.4,
            sig.has_inversion * 0.2,
            sig.has_subjunctive * 0.2,
        ]
        sig.complexity_score = min(sum(complexity_components), 1.0)
        
        return sig
    
    def signature_to_description(self, sig: SyntacticSignature) -> str:
        """将特征签名转换为自然语言描述（用于 Embedding）。"""
        features = []
        
        if sig.has_relative_clause:
            features.append("包含定语从句")
        if sig.has_adverbial_clause:
            features.append("包含状语从句")
        if sig.has_noun_clause:
            features.append("包含名词性从句")
        if sig.has_inversion:
            features.append("使用倒装结构")
        if sig.has_subjunctive:
            features.append("使用虚拟语气")
        if sig.has_participle_phrase:
            features.append("包含分词短语")
        
        # 复杂度描述
        if sig.complexity_score > 0.7:
            complexity = "长难句"
        elif sig.complexity_score > 0.4:
            complexity = "中等复杂句"
        else:
            complexity = "简单句"
        
        if not features:
            return f"这是一个{complexity}，结构相对简单"
        
        return f"这是一个{complexity}，{'、'.join(features)}"
```

---

## 8. 实施路线图

### Phase 1: 基础设施（Week 1）

- [ ] 设计并实现 `SyntacticExtractor`
- [ ] 搭建 Vector DB 接口（抽象层，支持 Chroma/FAISS 切换）
- [ ] 将现有硬编码示例转换为索引格式
- [ ] 为现有示例生成特征签名和向量

### Phase 2: 核心集成（Week 2）

- [ ] 实现 `GrammarRagService`（检索 + fallback）
- [ ] 修改 `analyze_nodes.py` 集成 RAG
- [ ] 添加配置项（RAG 开关、超时时间、Vector DB 地址等）
- [ ] 实现完整的错误处理和日志记录

### Phase 3: 验证与优化（Week 3）

- [ ] 性能测试：确认 RAG 延迟在可接受范围
- [ ] 质量评估：对比 baseline vs RAG 的输出质量
- [ ] 边界测试：异常场景、超时、配置缺失等
- [ ] 监控与可观测性完善

### Phase 4: 数据增强（后续）

- [ ] 收集高质量用户标注作为新示例
- [ ] 建立示例质量评分机制
- [ ] 探索 LLM 辅助生成新示例

---

## 9. 配置建议

```python
# settings.py 中新增配置项

@dataclass
class GrammarRagSettings:
    # 开关
    enabled: bool = False
    
    # Vector DB 配置
    vector_db_type: Literal["chroma", "faiss", "pinecone"] = "chroma"
    vector_db_path: str = "./data/grammar_examples"
    collection_name: str = "grammar_examples"
    
    # 检索配置
    retrieval_timeout: float = 2.0  # 秒
    top_k: int = 5
    min_required_examples: int = 2
    
    # 相似度权重
    structure_weight: float = 0.7  # 结构相似度权重
    semantic_weight: float = 0.3   # 语义相似度权重
    
    # Embedding 配置
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
```

---

## 10. 风险与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| Vector DB 不可用 | 中 | 高 | 强 Fallback 机制，始终可用 baseline |
| 检索超时 | 高 | 中 | 严格超时（2s），自动 fallback |
| 检索质量差 | 中 | 中 | 结果不足时用 baseline 补充；持续迭代示例库 |
| 特征提取不准确 | 高 | 低 | 规则提取只是近似，结合语义向量互补；未来可引入 LLM 结构化提取 |
| 示例库覆盖不足 | 中 | 中 | 从现有硬编码示例开始，逐步补充 |

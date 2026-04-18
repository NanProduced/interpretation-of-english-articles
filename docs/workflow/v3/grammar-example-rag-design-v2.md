# Grammar Example RAG 设计文档（v2）

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

### 1.2 v2 版本要解决的核心问题

**问题 1：全文聚合的"结构掩盖"问题**

```
假设文章包含：
- 7句：普通定语从句（简单、常见）
- 2句：分词短语作状语（中等）
- 1句：否定词前置倒装（稀有、高价值）

原始聚合 Query：
"这篇文章主要结构：定语从句，还有一些分词短语和倒装"

问题：
- 检索结果会被大量"定语从句"示例主导
- 那个稀有的"倒装"结构可能找不到匹配的示例
- 用户最需要学习的复杂结构被淹没了
```

**问题 2：正则提取的准确率问题**

```
正则匹配的问题：

句子 1: "The boy who is wearing a red hat is my brother."
正则检测：who 存在 → has_relative_clause=True ✓ 正确

句子 2: "Who is coming to the party?"
正则检测：who 存在 → has_relative_clause=True ✗ 错误（这是疑问句，不是定语从句）

句子 3: "Never before have I seen such beauty."
正则检测：Never before 不是严格的"Never + 助动词" → 可能漏检
```

### 1.3 设计目标

| 目标 | 说明 |
|------|------|
| 精准性 | 检索出的示例在"句法结构"和"讲解风格"上与目标高度相似 |
| **结构公平性** | 稀有高价值结构（如倒装、虚拟）不会被普通结构淹没 |
| **提取准确性** | 利用 LLM 结构化输出能力，提升句法特征提取准确率 |
| 性能 | 不因为"全文逐句检索"导致显著延迟 |
| 可靠性 | RAG 异常时优雅回退到 baseline，不中断工作流 |
| 范围控制 | 本阶段仅增强 `grammar_note` 和 `sentence_analysis`，不涉及词汇/翻译 |

---

## 2. 关键架构改进

### 2.1 改进 1：分簇多路检索

**核心思想**：不再做"全文聚合"，而是按"结构类型优先级"分簇，每簇独立检索。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    分簇多路检索架构                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  输入：句子列表（10句）                                                   │
│       ┌──────────────────────────────────────────────────────────────┐  │
│       │  S1: 定语从句    S2: 定语从句    S3: 定语从句               │  │
│       │  S4: 定语从句    S5: 定语从句    S6: 定语从句               │  │
│       │  S7: 定语从句    S8: 分词短语    S9: 分词短语               │  │
│       │  S10: 倒装（否定词前置）                                       │  │
│       └──────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Step 1: 分簇（按结构类型优先级）                                   │  │
│  │                                                                    │  │
│  │  优先级定义（高 → 低）：                                            │  │
│  │  1. 特殊句式：倒装、虚拟、强调（最稀有，最需要匹配示例）            │  │
│  │  2. 非谓语结构：分词短语、不定式短语                                 │  │
│  │  3. 复杂从句：定语从句、状语从句、名词性从句                         │  │
│  │  4. 其他特殊结构：同位语、插入语、独立主格                           │  │
│  │                                                                    │  │
│  │  分簇结果：                                                         │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │ 簇 A（优先级 1）：倒装簇                                      │  │  │
│  │  │  - 成员：S10（倒装）                                          │  │  │
│  │  │  - 数量：1 句（虽然少，但优先级最高）                          │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │ 簇 B（优先级 2）：分词短语簇                                  │  │  │
│  │  │  - 成员：S8, S9                                              │  │  │
│  │  │  - 数量：2 句                                                │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │ 簇 C（优先级 3）：定语从句簇                                  │  │  │
│  │  │  - 成员：S1-S7                                               │  │  │
│  │  │  - 数量：7 句（最多，但优先级最低）                            │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Step 2: 每簇独立构造 Query                                        │  │
│  │                                                                    │  │
│  │  簇 A Query："包含倒装结构的句子，如 Never had she felt..."       │  │
│  │  簇 B Query："包含分词短语作状语的句子，如 Influenced by..."      │  │
│  │  簇 C Query："包含定语从句的句子，如 The book that..."            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Step 3: 多路并行检索                                              │  │
│  │                                                                    │  │
│  │  簇 A 检索 → [倒装示例1, 倒装示例2]  ←── 稀有结构找到匹配示例！    │  │
│  │  簇 B 检索 → [分词示例1, 分词示例2]                               │  │
│  │  簇 C 检索 → [定语示例1, 定语示例2]                               │  │
│  │                                                                    │  │
│  │  关键优势：                                                        │  │
│  │  - 每个簇独立检索，不会互相干扰                                    │  │
│  │  - 稀有结构（倒装）不会被普通结构（定语从句）淹没                  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Step 4: 按优先级合并结果                                          │  │
│  │                                                                    │  │
│  │  合并策略：                                                        │  │
│  │  1. 按簇优先级排序：特殊句式 > 非谓语 > 从句                      │  │
│  │  2. 每簇取 Top-2 示例                                             │  │
│  │  3. 去重 + 总数限制（Top-5）                                      │  │
│  │                                                                    │  │
│  │  最终示例列表：                                                    │  │
│  │  [倒装示例1, 倒装示例2, 分词示例1, 分词示例2, 定语示例1]          │  │
│  │                                                                    │  │
│  │  对比原始方案：                                                    │  │
│  │  原始方案可能返回：[定语示例1, 定语示例2, 定语示例3, 定语示例4, ...] │  │
│  │  （倒装结构完全被淹没！）                                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 改进 2：LLM 增强的分层提取器

**核心思想**：利用项目已有的 `pydantic_ai.Agent` 架构，实现"规则快速过滤 + LLM 结构化确认"的分层策略。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    LLM 增强的分层提取器架构                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  与现有架构的兼容性：                                                    │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  现有 Agent 模式（grammar_agent.py）：                             │  │
│  │                                                                    │  │
│  │  @lru_cache(maxsize=1)                                             │  │
│  │  def get_grammar_agent() -> Agent[GrammarAgentDeps, GrammarDraft]: │  │
│  │      return Agent[GrammarAgentDeps, GrammarDraft](                │  │
│  │          model=None,                                               │  │
│  │          output_type=GrammarDraft,  ←── 强类型输出                │  │
│  │          deps_type=GrammarAgentDeps,                              │  │
│  │          instructions=GRAMMAR_INSTRUCTIONS,                       │  │
│  │          name="grammar_agent",                                     │  │
│  │          retries=2,                                                │  │
│  │          output_retries=2,                                         │  │
│  │          instrument=False,                                         │  │
│  │      )                                                             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  我们可以复用完全相同的模式！                                            │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  三种运行模式（可配置）：                                           │  │
│  │                                                                    │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │  │
│  │  │  模式 A       │  │  模式 B       │  │  模式 C       │           │  │
│  │  │  (成本优先)   │  │  (平衡模式)   │  │  (质量优先)   │           │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │  │
│  │         │                 │                 │                      │  │
│  │         ▼                 ▼                 ▼                      │  │
│  │  ┌──────────────────────────────────────────────────────────┐   │  │
│  │  │  Level 1: 规则快速过滤（0 cost）                           │   │  │
│  │  │                                                            │   │  │
│  │  │  使用轻量级正则，快速提取：                                  │   │  │
│  │  │  - 词数、句子长度                                          │   │  │
│  │  │  - 明显的标记词（who/which/that 等）                       │   │  │
│  │  │  - 句首特殊结构（Never/Had/Should 等）                      │   │  │
│  │  │                                                            │   │  │
│  │  │  输出：                                                     │   │  │
│  │  │  - 初步特征签名                                             │   │  │
│  │  │  - 置信度标记（高/中/低）                                   │   │  │
│  │  │    - 高："Never had she..." → 明确倒装                      │   │  │
│  │  │    - 中："who is..." → 可能定语从句，也可能疑问句           │   │  │
│  │  │    - 低：复杂句、歧义句                                      │   │  │
│  │  └──────────────────────────────────────────────────────────┘   │  │
│  │                          │                                         │  │
│  │                          ▼                                         │  │
│  │  ┌──────────────────────────────────────────────────────────┐   │  │
│  │  │  Level 2: LLM 结构化确认（仅对中/低置信度）                │   │  │
│  │  │                                                            │   │  │
│  │  │  复用现有架构：                                             │   │  │
│  │  │  - 基于 pydantic_ai.Agent                                 │   │  │
│  │  │  - output_type = LLMSyntacticSignature（强类型）           │   │  │
│  │  │  - 复用 MODEL_ROUTE_ANNOTATION_GENERATION                 │   │  │
│  │  │                                                            │   │  │
│  │  │  优势：                                                     │   │  │
│  │  │  - 批量处理：一次调用分析多句                               │   │  │
│  │  │  - 输出量小：仅结构标签，不是完整分析                       │   │  │
│  │  │  - token 消耗低：比 grammar_agent 轻量很多                 │   │  │
│  │  └──────────────────────────────────────────────────────────┘   │  │
│  │                          │                                         │  │
│  │                          ▼                                         │  │
│  │  ┌──────────────────────────────────────────────────────────┐   │  │
│  │  │  Level 3: 结果融合                                         │   │  │
│  │  │                                                            │   │  │
│  │  │  融合策略：                                                 │   │  │
│  │  │  - 高置信度规则结果：直接使用                               │   │  │
│  │  │  - LLM 确认结果：覆盖规则结果                               │   │  │
│  │  │  - 添加置信度元数据：用于后续监控和优化                     │   │  │
│  │  └──────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  各模式的成本-质量权衡：                                                 │
│  ┌──────────────┬─────────────────┬─────────────────┐                 │
│  │    模式       │   LLM 调用量   │   预期准确率   │                 │
│  ├──────────────┼─────────────────┼─────────────────┤                 │
│  │  规则优先     │     0%          │     ~60-70%    │                 │
│  │  混合模式     │    ~20-40%      │     ~85-90%    │                 │
│  │  质量优先     │    100%         │     ~90-95%    │                 │
│  └──────────────┴─────────────────┴─────────────────┘                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 分簇多路检索详细设计

### 3.1 结构类型优先级定义

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Callable
from collections import defaultdict


class StructureClusterType(Enum):
    """结构簇类型，按优先级排序（高 → 低）。
    
    优先级设计原则：
    1. 越稀有的结构，优先级越高（用户越需要示例）
    2. 越复杂的结构，优先级越高（规则提取越不准确）
    """
    
    # ========== 优先级 1：特殊句式（最稀有，最需要匹配示例）==========
    # 这些结构在示例库中可能数量很少，但用户遇到时非常需要参考
    INVERSION = "inversion"           # 倒装结构
    SUBJUNCTIVE = "subjunctive"       # 虚拟语气
    EMPHASIS = "emphasis"             # 强调结构（it is...that）
    
    # ========== 优先级 2：非谓语结构 ==========
    # 这些结构比从句更难识别，规则提取准确率较低
    PARTICIPLE_PHRASE = "participle"  # 分词短语（现在/过去分词作状语/定语）
    INFINITIVE_PHRASE = "infinitive"  # 不定式短语
    
    # ========== 优先级 3：复杂从句 ==========
    # 这些结构相对常见，规则提取有一定准确率
    RELATIVE_CLAUSE = "relative"      # 定语从句
    ADVERBIAL_CLAUSE = "adverbial"    # 状语从句
    NOUN_CLAUSE = "noun"              # 名词性从句（主语/宾语/同位语/表语）
    
    # ========== 优先级 4：其他特殊结构 ==========
    APPOSITIVE = "appositive"         # 同位语结构
    PARENTHETICAL = "parenthetical"   # 插入语
    ABSOLUTE_CONSTRUCTION = "absolute" # 独立主格结构


# 簇优先级映射（数字越小优先级越高）
CLUSTER_PRIORITY: Dict[StructureClusterType, int] = {
    # 优先级 1
    StructureClusterType.INVERSION: 1,
    StructureClusterType.SUBJUNCTIVE: 1,
    StructureClusterType.EMPHASIS: 1,
    
    # 优先级 2
    StructureClusterType.PARTICIPLE_PHRASE: 2,
    StructureClusterType.INFINITIVE_PHRASE: 2,
    
    # 优先级 3
    StructureClusterType.RELATIVE_CLAUSE: 3,
    StructureClusterType.ADVERBIAL_CLAUSE: 3,
    StructureClusterType.NOUN_CLAUSE: 3,
    
    # 优先级 4
    StructureClusterType.APPOSITIVE: 4,
    StructureClusterType.PARENTHETICAL: 4,
    StructureClusterType.ABSOLUTE_CONSTRUCTION: 4,
}
```

### 3.2 分簇算法

```python
@dataclass
class SyntacticSignature:
    """统一的句法特征签名。"""
    
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
    
    # 来源和置信度
    source: str = "rules"  # "rules" or "llm"
    confidence: str = "high"  # "high", "medium", "low"


@dataclass
class StructureCluster:
    """一个结构簇，包含一组具有相同结构类型的句子。"""
    
    cluster_type: StructureClusterType
    sentences: List[Dict]              # 簇内句子列表
    signatures: List[SyntacticSignature]  # 对应的特征签名
    
    # 簇元数据
    sentence_count: int = 0
    has_high_confidence: bool = True   # 是否所有句子都有高置信度特征
    
    def __post_init__(self):
        self.sentence_count = len(self.sentences)


class StructureClusterer:
    """句子结构分簇器。"""
    
    def __init__(self):
        pass
    
    def cluster_sentences(
        self,
        sentences: List[Dict],
        signatures: List[SyntacticSignature],
    ) -> List[StructureCluster]:
        """
        对句子列表进行结构分簇。
        
        核心策略：
        1. 每个句子提取所有可能的结构特征
        2. 按最高优先级的特征进行"主簇"分配
        3. 低优先级特征如果数量足够，也可以独立成"次簇"
        
        关键设计：一个句子可以属于多个簇！
        - 例如："Never had she seen a man who was so tall."
        - 这个句子既有倒装（优先级 1），又有定语从句（优先级 3）
        - 它应该同时属于"倒装簇"和"定语从句簇"
        - 这样在合并结果时，倒装的示例会先出现
        """
        
        if len(sentences) != len(signatures):
            raise ValueError("sentences and signatures length mismatch")
        
        # Step 1: 统计各结构类型的句子数量
        structure_counts = defaultdict(int)
        structure_members = defaultdict(list)  # cluster_type -> list of (sentence, sig, index)
        
        for idx, (sent, sig) in enumerate(zip(sentences, signatures)):
            # 找出这个句子的所有结构类型（按优先级排序）
            structure_types = self._get_structure_types(sig)
            
            for st in structure_types:
                structure_counts[st] += 1
                structure_members[st].append((sent, sig, idx))
        
        # Step 2: 确定簇列表
        # - 按优先级排序所有有句子的结构类型
        # - 每个类型如果句子数 >= 1，独立成簇
        
        clusters = []
        
        # 按优先级排序
        sorted_types = sorted(
            structure_counts.keys(),
            key=lambda st: CLUSTER_PRIORITY.get(st, 999)
        )
        
        for cluster_type in sorted_types:
            members = structure_members[cluster_type]
            
            if len(members) >= 1:
                # 检查这个簇的置信度
                all_high_confidence = all(
                    m[1].confidence == "high" for m in members
                )
                
                cluster = StructureCluster(
                    cluster_type=cluster_type,
                    sentences=[m[0] for m in members],
                    signatures=[m[1] for m in members],
                    has_high_confidence=all_high_confidence,
                )
                clusters.append(cluster)
        
        # Step 3: 如果没有任何结构簇（所有句子都是简单句）
        if not clusters:
            # 创建一个"通用复杂句"簇
            # 使用所有句子，特征签名为空（表示通用）
            cluster = StructureCluster(
                cluster_type=StructureClusterType.RELATIVE_CLAUSE,  # 默认使用最常见的类型
                sentences=sentences,
                signatures=signatures,
                has_high_confidence=True,
            )
            clusters.append(cluster)
        
        return clusters
    
    def _get_structure_types(
        self,
        sig: SyntacticSignature,
    ) -> List[StructureClusterType]:
        """从特征签名提取结构类型列表（按优先级排序）。"""
        
        types = []
        
        # 优先级 1
        if sig.has_inversion:
            types.append(StructureClusterType.INVERSION)
        if sig.has_subjunctive:
            types.append(StructureClusterType.SUBJUNCTIVE)
        
        # 优先级 2
        if sig.has_participle_phrase:
            types.append(StructureClusterType.PARTICIPLE_PHRASE)
        
        # 优先级 3
        if sig.has_relative_clause:
            types.append(StructureClusterType.RELATIVE_CLAUSE)
        if sig.has_adverbial_clause:
            types.append(StructureClusterType.ADVERBIAL_CLAUSE)
        if sig.has_noun_clause:
            types.append(StructureClusterType.NOUN_CLAUSE)
        
        # 优先级 4
        if sig.has_appositive:
            types.append(StructureClusterType.APPOSITIVE)
        if sig.has_parenthetical:
            types.append(StructureClusterType.PARENTHETICAL)
        
        return types
```

### 3.3 每簇 Query 构造

```python
@dataclass
class ClusterRetrievalQuery:
    """每个簇的检索 Query。"""
    
    cluster_type: StructureClusterType
    query_text: str                   # 用于向量化的文本描述
    filter_metadata: Dict              # 用于预过滤的元数据
    representative_sentences: List[str] # 簇内代表性句子（用于语义辅助）


class ClusterQueryBuilder:
    """为每个簇构造检索 Query。"""
    
    # 结构类型到中文描述的映射
    CLUSTER_DESCRIPTIONS: Dict[StructureClusterType, str] = {
        # 优先级 1
        StructureClusterType.INVERSION: "倒装结构（否定词前置、only前置、虚拟条件倒装等）",
        StructureClusterType.SUBJUNCTIVE: "虚拟语气（与事实相反的假设、愿望等）",
        StructureClusterType.EMPHASIS: "强调结构（it is...that/who 等）",
        
        # 优先级 2
        StructureClusterType.PARTICIPLE_PHRASE: "分词短语作状语或定语（现在分词/过去分词短语）",
        StructureClusterType.INFINITIVE_PHRASE: "不定式短语（to do 结构作状语、定语、主语等）",
        
        # 优先级 3
        StructureClusterType.RELATIVE_CLAUSE: "定语从句（who/which/that 等引导，修饰名词）",
        StructureClusterType.ADVERBIAL_CLAUSE: "状语从句（because/when/if/although 等引导）",
        StructureClusterType.NOUN_CLAUSE: "名词性从句（主语/宾语/同位语/表语从句）",
        
        # 优先级 4
        StructureClusterType.APPOSITIVE: "同位语结构（名词解释或说明另一个名词）",
        StructureClusterType.PARENTHETICAL: "插入语（句子中插入的补充说明成分）",
        StructureClusterType.ABSOLUTE_CONSTRUCTION: "独立主格结构（名词/代词 + 分词/形容词/介词短语等）",
    }
    
    def build_query(
        self,
        cluster: StructureCluster,
        variant_id: str,
        grammar_focus: str,
    ) -> ClusterRetrievalQuery:
        """为一个簇构造检索 Query。"""
        
        # 基础描述
        base_desc = self.CLUSTER_DESCRIPTIONS.get(
            cluster.cluster_type,
            "复杂句子结构"
        )
        
        # 计算簇内平均复杂度
        if cluster.signatures:
            avg_complexity = sum(
                sig.complexity_score for sig in cluster.signatures
            ) / len(cluster.signatures)
        else:
            avg_complexity = 0.5
        
        if avg_complexity > 0.7:
            complexity_desc = "长难句"
        elif avg_complexity > 0.4:
            complexity_desc = "中等复杂句"
        else:
            complexity_desc = "一般句子"
        
        # 构造 Query 文本（用于向量化）
        query_parts = [
            f"这是一个包含{base_desc}的{complexity_desc}",
            f"需要讲解{self.CLUSTER_DESCRIPTIONS.get(cluster.cluster_type, '此结构')}的用法和分析方法",
        ]
        
        # 如果簇内有代表性句子，补充描述
        if cluster.sentences:
            # 取最长的句子作为代表
            longest = max(cluster.sentences, key=lambda s: len(s.get("text", "").split()))
            text = longest.get("text", "")[:150]
            if text:
                query_parts.append(f"类似这样的句子：{text}")
        
        query_text = "。".join(query_parts)
        
        # 构造过滤元数据
        filter_metadata = {
            "variant_id": variant_id,
            "grammar_focus": grammar_focus,
            "cluster_type": cluster.cluster_type.value,
        }
        
        # 代表性句子（用于语义辅助检索）
        representative_sentences = []
        if len(cluster.sentences) >= 2:
            # 取最长的 2 句
            sorted_sents = sorted(
                cluster.sentences,
                key=lambda s: len(s.get("text", "").split()),
                reverse=True
            )
            representative_sentences = [s.get("text", "") for s in sorted_sents[:2]]
        
        return ClusterRetrievalQuery(
            cluster_type=cluster.cluster_type,
            query_text=query_text,
            filter_metadata=filter_metadata,
            representative_sentences=representative_sentences,
        )
```

### 3.4 多路检索与结果合并

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


@dataclass
class ClusterRetrievalResult:
    """单个簇的检索结果。"""
    
    cluster_type: StructureClusterType
    examples: List[Dict]  # ExampleEntry 格式
    similarity_scores: List[float]
    query_used: str
    retrieval_latency_ms: float = 0.0
    success: bool = True


@dataclass
class MultiRouteRetrievalOutcome:
    """多路检索的最终结果。"""
    
    success: bool
    examples: List[Dict]  # 合并后的示例列表
    
    # 各簇的结果（用于监控）
    cluster_results: List[ClusterRetrievalResult] = field(default_factory=list)
    
    # 元数据
    total_clusters: int = 0
    used_fallback: bool = False
    error_message: Optional[str] = None


class MultiRouteRetriever:
    """多路检索器：每个簇独立检索，然后合并结果。"""
    
    def __init__(
        self,
        vector_db: "VectorDBClient",
        clusterer: StructureClusterer,
        query_builder: ClusterQueryBuilder,
        settings: "GrammarRagSettings",
    ):
        self.vector_db = vector_db
        self.clusterer = clusterer
        self.query_builder = query_builder
        self.settings = settings
    
    async def retrieve(
        self,
        sentences: List[Dict],
        signatures: List[SyntacticSignature],
        variant_id: str,
        grammar_focus: str,
        baseline_examples: Optional[List[Dict]] = None,
    ) -> MultiRouteRetrievalOutcome:
        """
        执行多路检索。
        
        流程：
        1. 分簇
        2. 每簇构造 Query
        3. 每簇并行检索
        4. 按优先级合并结果
        5. 不足时用 baseline 补充
        """
        
        start_time = time.time()
        cluster_results = []
        
        try:
            # Step 1: 分簇
            clusters = self.clusterer.cluster_sentences(sentences, signatures)
            
            if not clusters:
                # 没有簇，直接返回 baseline
                return MultiRouteRetrievalOutcome(
                    success=True,
                    examples=baseline_examples or [],
                    total_clusters=0,
                    used_fallback=baseline_examples is not None,
                )
            
            # Step 2: 每簇构造 Query
            queries = []
            for cluster in clusters:
                query = self.query_builder.build_query(
                    cluster=cluster,
                    variant_id=variant_id,
                    grammar_focus=grammar_focus,
                )
                queries.append((cluster.cluster_type, query))
            
            # Step 3: 并行检索所有簇
            retrieval_tasks = []
            for cluster_type, query in queries:
                task = self._retrieve_single_cluster(
                    cluster_type=cluster_type,
                    query=query,
                    top_k_per_cluster=self.settings.top_k_per_cluster,
                )
                retrieval_tasks.append(task)
            
            # 并行执行（带总超时）
            raw_results = await asyncio.wait_for(
                asyncio.gather(*retrieval_tasks, return_exceptions=True),
                timeout=self.settings.total_retrieval_timeout,
            )
            
            # Step 4: 处理检索结果
            valid_results = []
            all_examples = []
            
            for result in raw_results:
                if isinstance(result, Exception):
                    # 单个簇检索失败，记录但不中断
                    logger.warning(f"Cluster retrieval failed: {result}")
                    continue
                
                valid_results.append(result)
                
                # 按优先级添加示例（高优先级簇的示例在前）
                # 注意：clusters 已经按优先级排序，所以 raw_results 也按优先级排序
                all_examples.extend(result.examples)
            
            # Step 5: 去重 + 限制总数
            all_examples = self._deduplicate_and_limit(
                all_examples,
                max_total=self.settings.max_total_examples,
            )
            
            # Step 6: 如果数量不足，用 baseline 补充
            if len(all_examples) < self.settings.min_required_examples:
                if baseline_examples:
                    # 去重合并
                    seen = {e.get("sentence_text", "") for e in all_examples}
                    supplementary = [
                        e for e in baseline_examples
                        if e.get("sentence_text", "") not in seen
                    ][: (self.settings.min_required_examples - len(all_examples))]
                    all_examples.extend(supplementary)
            
            total_time_ms = (time.time() - start_time) * 1000
            
            return MultiRouteRetrievalOutcome(
                success=True,
                examples=all_examples,
                cluster_results=valid_results,
                total_clusters=len(clusters),
                used_fallback=len(all_examples) < self.settings.min_required_examples,
            )
        
        except asyncio.TimeoutError:
            # 总超时，返回 baseline
            logger.error(f"Multi-route retrieval timed out after {self.settings.total_retrieval_timeout}s")
            return MultiRouteRetrievalOutcome(
                success=False,
                examples=baseline_examples or [],
                total_clusters=0,
                used_fallback=True,
                error_message=f"Retrieval timed out after {self.settings.total_retrieval_timeout}s",
            )
        
        except Exception as e:
            # 其他错误，返回 baseline
            logger.exception("Multi-route retrieval failed with unexpected error")
            return MultiRouteRetrievalOutcome(
                success=False,
                examples=baseline_examples or [],
                total_clusters=0,
                used_fallback=True,
                error_message=str(e),
            )
    
    async def _retrieve_single_cluster(
        self,
        cluster_type: StructureClusterType,
        query: ClusterRetrievalQuery,
        top_k_per_cluster: int,
    ) -> ClusterRetrievalResult:
        """检索单个簇的示例。"""
        
        start_time = time.time()
        
        try:
            # 调用 Vector DB 检索（带单簇超时）
            result = await asyncio.wait_for(
                self.vector_db.search(
                    query_text=query.query_text,
                    filter_metadata=query.filter_metadata,
                    top_k=top_k_per_cluster,
                ),
                timeout=self.settings.per_cluster_timeout,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            return ClusterRetrievalResult(
                cluster_type=cluster_type,
                examples=result.examples,
                similarity_scores=result.scores,
                query_used=query.query_text,
                retrieval_latency_ms=latency_ms,
                success=True,
            )
        
        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(f"Cluster {cluster_type.value} retrieval timed out")
            return ClusterRetrievalResult(
                cluster_type=cluster_type,
                examples=[],
                similarity_scores=[],
                query_used=query.query_text,
                retrieval_latency_ms=latency_ms,
                success=False,
            )
        
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(f"Cluster {cluster_type.value} retrieval failed: {e}")
            return ClusterRetrievalResult(
                cluster_type=cluster_type,
                examples=[],
                similarity_scores=[],
                query_used=query.query_text,
                retrieval_latency_ms=latency_ms,
                success=False,
            )
    
    def _deduplicate_and_limit(
        self,
        examples: List[Dict],
        max_total: int,
    ) -> List[Dict]:
        """去重并限制总数。
        
        关键：保持原有顺序（高优先级簇的示例在前）
        """
        
        seen = set()
        result = []
        
        for example in examples:
            text = example.get("sentence_text", "")
            if text and text not in seen:
                seen.add(text)
                result.append(example)
                if len(result) >= max_total:
                    break
        
        return result
```

---

## 4. LLM 增强的特征提取器详细设计

### 4.1 句法分析 Agent 设计

```python
"""轻量级句法特征提取 Agent。

设计原则：
1. 复用现有 pydantic_ai.Agent 架构
2. output_type 强类型，确保结构化输出
3. 批量处理：一次调用分析多句
4. 轻量级：仅提取结构标签，不做完整语法分析
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Dict, Optional, Literal

from pydantic_ai import Agent
from pydantic import BaseModel, Field


# ========== 输出 Schema（强类型）==========

class LLMSyntacticSignature(BaseModel):
    """LLM 提取的单句句法特征。
    
    这个 schema 定义了 LLM 的输出格式，确保结构化输出。
    与现有的 SyntacticSignature 对应，但包含更详细的置信度。
    """
    
    sentence_index: int = Field(description="句子在输入列表中的索引")
    
    # ========== 从句类型 ==========
    has_relative_clause: bool = Field(
        default=False,
        description="是否包含定语从句（who/which/that 等引导，修饰名词）。注意：who/which/that 引导疑问句时不算。"
    )
    has_adverbial_clause: bool = Field(
        default=False,
        description="是否包含状语从句（because/when/if/although/while/since/as/unless/until 等引导，表时间、原因、条件、让步、方式等）"
    )
    has_noun_clause: bool = Field(
        default=False,
        description="是否包含名词性从句（主语从句、宾语从句、表语从句、同位语从句）。注意：that 在同位语从句中不作成分，在定语从句中作成分。"
    )
    
    # ========== 特殊结构 ==========
    has_inversion: bool = Field(
        default=False,
        description="是否包含倒装结构。包括：1) 否定词前置（Never/Rarely/Seldom/Hardly/Little/Scarcely + 助动词）；2) Only 前置（Only + 状语 + 助动词）；3) 虚拟条件倒装（Had/Should/Were + 主语）"
    )
    has_subjunctive: bool = Field(
        default=False,
        description="是否包含虚拟语气。包括：1) would have + 过去分词；2) could have + 过去分词；3) should have + 过去分词；4) had done（虚拟条件句）；5) were（虚拟现在时）"
    )
    has_participle_phrase: bool = Field(
        default=False,
        description="是否包含分词短语作状语或定语。包括现在分词短语（-ing）和过去分词短语（-ed）。注意：interesting/interested 等作形容词时不算。"
    )
    has_appositive: bool = Field(
        default=False,
        description="是否包含同位语结构。名词或名词短语解释或说明另一个名词，常由 that 引导（that 在同位语从句中不作成分）"
    )
    has_parenthetical: bool = Field(
        default=False,
        description="是否包含插入语。句子中插入的补充说明成分，常由逗号、破折号或括号分隔"
    )
    
    # ========== 复杂度评估 ==========
    complexity_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="句子复杂度评分，0=简单句（主谓宾完整，无从句），0.5=中等复杂（含一个从句或简单分词短语），1.0=极复杂长难句（多层嵌套、多从句、特殊结构组合）"
    )
    
    # ========== 置信度 ==========
    confidence: Literal["high", "medium", "low"] = Field(
        default="high",
        description="LLM 对自身判断的置信度。high=结构清晰，判断确定；medium=有一定歧义，但倾向于某个判断；low=结构复杂或歧义较大，判断不确定"
    )
    
    # ========== 可选：详细说明（用于调试）==========
    reasoning: Optional[str] = Field(
        default=None,
        description="可选：LLM 的推理过程说明（用于调试和优化）"
    )


class LLMSyntacticAnalysisResult(BaseModel):
    """LLM 批量句法分析结果。"""
    
    sentences: List[LLMSyntacticSignature] = Field(
        description="每个输入句子的句法特征列表，顺序与输入一致"
    )


# ========== Agent 依赖 ==========

@dataclass
class SyntacticAnalysisDeps:
    """句法分析 Agent 的依赖。"""
    
    sentences: List[Dict[str, object]]  # [{"sentence_id": "s1", "text": "..."}]


# ========== Prompt 构建 ==========

SYNTACTIC_ANALYSIS_INSTRUCTIONS = """
你是一位英语句法分析助手。你的任务是分析输入的英文句子，提取结构化的句法特征。

## 你的目标
- 快速、准确地识别句子的句法结构类型
- 不需要做完整的语法分析，只需要标记关键结构特征
- 输出必须严格符合 JSON 格式

## 重要区分（容易误判的情况）

### 1. 定语从句 vs 疑问句
- 定语从句：who/which/that 引导的从句修饰名词
  - 例："The book that I bought is interesting."（that 修饰 book）
- 疑问句：who/which/that 位于句首，引导问句
  - 例："Who is coming to the party?"（这是疑问句，不是定语从句）
  - 例："Which book do you like?"（这是疑问句，不是定语从句）

### 2. 定语从句 vs 同位语从句
- 定语从句：that/which 在从句中作成分（主语或宾语）
  - 例："The news that he told me surprised us."（that 在从句中作 told 的宾语）
- 同位语从句：that 在从句中不作成分，只起连接作用
  - 例："The news that he won surprised us."（that 不作成分，从句解释 news 的内容）

### 3. 分词短语 vs 形容词
- 分词短语作状语/定语：-ing/-ed 形式在句中作状语或定语
  - 例："Influenced by the speech, he decided to study harder."（Influenced 作状语）
  - 例："The book written by Lu Xun is famous."（written 作定语）
- 形容词：-ing/-ed 形式作表语或定语，表示状态
  - 例："The movie is interesting."（interesting 是形容词）
  - 例："I am interested in this topic."（interested 是形容词）

### 4. 虚拟语气 vs 真实条件句
- 虚拟语气：与事实相反的假设
  - 例："If I were you, I would try."（与现在事实相反）
  - 例："He would have passed if he had studied."（与过去事实相反）
- 真实条件句：可能发生的情况
  - 例："If it rains, we will stay at home."（可能下雨）

## 结构类型定义

### 从句类型
1. **定语从句（has_relative_clause）**
   - 由 who/whom/whose/which/that/where/when/why 引导
   - 修饰名词或代词
   - 关键：从句在句子中作定语
   - 引导词在从句中作成分（主语或宾语）

2. **状语从句（has_adverbial_clause）**
   - 由 because/when/if/although/while/since/as/unless/until/before/after 等引导
   - 表时间、原因、条件、让步、方式等
   - 关键：从句在句子中作状语

3. **名词性从句（has_noun_clause）**
   - 由 that/what/whether/if/who/how/why 等引导
   - 在句子中作主语、宾语、表语或同位语
   - 例："That he passed the exam surprised everyone."（主语从句）
   - 例："I think that he is right."（宾语从句）
   - 例："The fact that he passed surprised us."（同位语从句）

### 特殊结构
4. **倒装结构（has_inversion）**
   - 否定词前置：Never/Rarely/Seldom/Hardly/Little/Scarcely + 助动词 + 主语
   - Only 前置：Only + 状语 + 助动词 + 主语
   - 虚拟条件倒装：Had/Should/Were + 主语（省略 if）
   - 例："Never had she felt so alone."
   - 例："Had I known, I would have come."

5. **虚拟语气（has_subjunctive）**
   - would have + 过去分词
   - could have + 过去分词
   - should have + 过去分词
   - had done（虚拟条件句）
   - were（虚拟现在时，主语是单数时也用 were）
   - 例："If I were you, I would try."
   - 例："He would have passed if he had studied."

6. **分词短语（has_participle_phrase）**
   - 现在分词短语（-ing）作状语或定语（表主动关系）
   - 过去分词短语（-ed）作状语或定语（表被动关系）
   - 例："Influenced by the speech, he decided to study harder."
   - 例："The book written by Lu Xun is famous."

7. **同位语结构（has_appositive）**
   - 名词或名词短语解释或说明另一个名词
   - 常由 that 引导（that 在同位语从句中不作成分）
   - 例："The news that he won excited us."
   - 例："My friend John is coming."

8. **插入语（has_parenthetical）**
   - 句子中插入的补充说明成分
   - 常由逗号、破折号或括号分隔
   - 例："The solution, I think, is correct."
   - 例："This decision - and it is important - affects us all."

## 复杂度评分
- 0.0 - 0.3：简单句（主谓宾完整，无从句）
- 0.3 - 0.6：中等复杂（含一个从句或简单分词短语）
- 0.6 - 1.0：复杂句（多层嵌套、多从句、特殊结构组合）

## 置信度标记
- high：结构清晰，判断确定
- medium：有一定歧义，但倾向于某个判断
- low：结构复杂或歧义较大，判断不确定

## 输出要求
1. 对每个输入句子，输出对应的 LLMSyntacticSignature
2. 严格按定义判断，注意区分容易误判的情况
3. 如果不确定，标记 confidence 为 medium 或 low
4. 输出必须是有效的 JSON 格式

## 输入格式
你会收到一个句子列表，每个句子有 sentence_id 和 text。
""".strip()


def build_syntactic_analysis_prompt(deps: SyntacticAnalysisDeps) -> str:
    """构建句法分析的 prompt。"""
    
    lines = ["请分析以下句子的句法特征：", ""]
    
    for idx, sent in enumerate(deps.sentences):
        sent_id = sent.get("sentence_id", f"s{idx+1}")
        text = sent.get("text", "")
        lines.append(f"句子 {idx + 1} ({sent_id}):")
        lines.append(f"  文本：{text}")
        lines.append("")
    
    lines.append("请输出 JSON 格式的分析结果。")
    
    return "\n".join(lines)


# ========== Agent 定义 ==========

@lru_cache(maxsize=1)
def get_syntactic_analysis_agent() -> Agent[SyntacticAnalysisDeps, LLMSyntacticAnalysisResult]:
    """获取句法分析 Agent 实例。
    
    复用现有的 Agent 架构模式：
    - model=None: 运行时通过 run_agent_with_route 指定
    - output_type=LLMSyntacticAnalysisResult: 强类型输出
    - deps_type=SyntacticAnalysisDeps: 依赖类型
    """
    
    return Agent[SyntacticAnalysisDeps, LLMSyntacticAnalysisResult](
        model=None,
        output_type=LLMSyntacticAnalysisResult,
        deps_type=SyntacticAnalysisDeps,
        instructions=SYNTACTIC_ANALYSIS_INSTRUCTIONS,
        name="syntactic_analysis_agent",
        retries=1,  # 轻量级，少重试
        output_retries=1,
        instrument=False,
    )


# ========== 运行器（复用现有模式）==========

async def run_syntactic_analysis_agent(
    deps: SyntacticAnalysisDeps,
    model_selection: Optional["ModelSelection"] = None,
) -> "RunResult[LLMSyntacticAnalysisResult]":
    """运行句法分析 Agent。
    
    复用现有的 run_agent_with_route 和 MODEL_ROUTE_ANNOTATION_GENERATION。
    与 grammar_agent、vocabulary_agent 等使用相同的调用方式。
    """
    
    from app.llm.agent_runner import run_agent_with_route
    from app.llm.routes import MODEL_ROUTE_ANNOTATION_GENERATION
    
    return await run_agent_with_route(
        agent=get_syntactic_analysis_agent(),
        prompt=build_syntactic_analysis_prompt(deps),
        deps=deps,
        route=MODEL_ROUTE_ANNOTATION_GENERATION,
        model_selection=model_selection,
    )
```

### 4.2 分层提取器实现

```python
"""分层句法特征提取器。

三种运行模式：
- MODE_RULES_ONLY: 仅使用规则（最快，成本最低）
- MODE_HYBRID: 规则 + LLM 确认（平衡）
- MODE_LLM_ONLY: 仅使用 LLM（最准确，成本最高）
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Tuple
import logging
import re

logger = logging.getLogger(__name__)


class ExtractionMode(Enum):
    """提取模式。"""
    MODE_RULES_ONLY = "rules_only"      # 仅规则
    MODE_HYBRID = "hybrid"               # 规则 + LLM 确认
    MODE_LLM_ONLY = "llm_only"           # 仅 LLM


class RuleBasedExtractor:
    """基于规则的句法特征提取器（轻量级）。
    
    这是第一层提取器，用于快速过滤。
    注意：规则提取可能不准确，特别是在复杂句子中。
    """
    
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
        re.compile(r'^(Had|Should|Were)\s+\w+', re.IGNORECASE),
    ]
    
    # 虚拟语气标记
    SUBJUNCTIVE_PATTERNS = [
        re.compile(r'\bwould\s+have\s+\w+ed', re.IGNORECASE),
        re.compile(r'\bcould\s+have\s+\w+ed', re.IGNORECASE),
        re.compile(r'\bshould\s+have\s+\w+ed', re.IGNORECASE),
    ]
    
    def extract(self, text: str) -> SyntacticSignature:
        """提取句法特征。
        
        注意：这是启发式规则，可能不准确。
        置信度标记用于决定是否需要 LLM 确认。
        """
        
        sig = SyntacticSignature(source="rules")
        
        # 词数
        words = re.findall(r'\b[a-zA-Z]+\b', text)
        sig.word_count = len(words)
        word_set = set(w.lower() for w in words)
        
        # 从句检测（启发式）
        sig.has_relative_clause = bool(word_set & self.RELATIVE_PRONOUNS)
        sig.has_adverbial_clause = bool(word_set & self.ADVERBIAL_CONJUNCTIONS)
        sig.has_noun_clause = bool(word_set & self.NOUN_CLAUSE_MARKERS)
        
        # 特殊结构检测
        sig.has_inversion = any(p.search(text) for p in self.INVERSION_PATTERNS)
        sig.has_subjunctive = any(p.search(text) for p in self.SUBJUNCTIVE_PATTERNS)
        
        # 分词短语检测（简化）
        first_word_match = re.match(r'^([A-Za-z]+(?:ed|ing))\b', text.strip())
        if first_word_match:
            first_word = first_word_match.group(1).lower()
            # 排除常见的介词/连词
            not_ignored = first_word not in {"according", "including", "regarding"}
            sig.has_participle_phrase = not_ignored
        
        # ========== 置信度计算 ==========
        # 这是规则提取的关键：标记哪些结果可能不准确
        
        if sig.has_inversion or sig.has_subjunctive:
            # 倒装和虚拟语气的规则检测相对准确
            sig.confidence = "high"
        elif sig.has_relative_clause or sig.has_adverbial_clause or sig.has_noun_clause:
            # 从句检测容易误判（who 可能是疑问句，that 可能是同位语等）
            sig.confidence = "medium"
        else:
            # 没有检测到特殊结构，置信度高
            sig.confidence = "high"
        
        # 额外：如果句子以 who/which/what/that 开头，可能是疑问句
        # 降低定语从句的置信度
        if re.match(r'^(Who|Which|What|That)\s', text.strip()):
            if sig.has_relative_clause:
                sig.confidence = "low"  # 很可能是疑问句，不是定语从句
        
        # ========== 复杂度评分 ==========
        clause_count = sum([
            sig.has_relative_clause,
            sig.has_adverbial_clause,
            sig.has_noun_clause,
        ])
        sig.clause_count = clause_count
        
        complexity_components = [
            clause_count * 0.2,
            min(sig.word_count / 30, 1.0) * 0.4,
            sig.has_inversion * 0.2,
            sig.has_subjunctive * 0.2,
        ]
        sig.complexity_score = min(sum(complexity_components), 1.0)
        
        return sig


class LLMAugmentedExtractor:
    """LLM 增强的分层提取器。
    
    根据配置选择提取策略：
    - MODE_RULES_ONLY: 仅规则
    - MODE_HYBRID: 规则 + LLM 确认低置信度句子
    - MODE_LLM_ONLY: 所有句子用 LLM
    """
    
    def __init__(
        self,
        mode: ExtractionMode = ExtractionMode.MODE_HYBRID,
        rule_extractor: Optional[RuleBasedExtractor] = None,
        llm_confidence_threshold: str = "medium",  # 低于此置信度的规则结果需要 LLM 确认
    ):
        self.mode = mode
        self.rule_extractor = rule_extractor or RuleBasedExtractor()
        self.llm_confidence_threshold = llm_confidence_threshold
    
    async def extract_batch(
        self,
        sentences: List[Dict],  # [{"sentence_id": "s1", "text": "..."}]
        model_selection: Optional["ModelSelection"] = None,
    ) -> List[SyntacticSignature]:
        """
        批量提取句子的句法特征。
        
        根据运行模式选择策略：
        - MODE_RULES_ONLY: 仅规则
        - MODE_HYBRID: 规则 + LLM 确认低置信度句子
        - MODE_LLM_ONLY: 所有句子用 LLM
        """
        
        if self.mode == ExtractionMode.MODE_RULES_ONLY:
            # 模式 A：仅规则
            return [self.rule_extractor.extract(s.get("text", "")) for s in sentences]
        
        if self.mode == ExtractionMode.MODE_LLM_ONLY:
            # 模式 C：仅 LLM
            return await self._extract_with_llm(sentences, model_selection)
        
        # 模式 B：混合模式
        # Step 1: 先用规则提取所有句子
        rule_results = [self.rule_extractor.extract(s.get("text", "")) for s in sentences]
        
        # Step 2: 找出需要 LLM 确认的句子（低置信度）
        need_llm_indices = []
        need_llm_sentences = []
        
        for idx, (sent, sig) in enumerate(zip(sentences, rule_results)):
            if self._needs_llm_confirmation(sig):
                need_llm_indices.append(idx)
                need_llm_sentences.append(sent)
        
        if not need_llm_sentences:
            # 所有句子都是高置信度，直接返回规则结果
            logger.debug("All sentences have high confidence, using rule results only")
            return rule_results
        
        logger.info(f"Calling LLM for {len(need_llm_sentences)} low-confidence sentences (total: {len(sentences)})")
        
        # Step 3: 用 LLM 确认低置信度句子
        try:
            llm_results = await self._extract_with_llm(
                need_llm_sentences,
                model_selection,
            )
            
            # Step 4: 融合结果
            final_results = rule_results.copy()
            for need_idx, llm_idx in zip(need_llm_indices, range(len(llm_results))):
                # 用 LLM 结果覆盖规则结果
                final_results[need_idx] = llm_results[llm_idx]
            
            return final_results
            
        except Exception as e:
            # LLM 调用失败，回退到规则结果
            logger.warning(f"LLM extraction failed, falling back to rules: {e}")
            return rule_results
    
    def _needs_llm_confirmation(self, sig: SyntacticSignature) -> bool:
        """判断一个规则结果是否需要 LLM 确认。
        
        阈值：
        - "high": 只有 high 置信度不需要确认
        - "medium": medium 和 high 都不需要确认（只有 low 需要）
        """
        
        if self.llm_confidence_threshold == "high":
            # 只有高置信度不需要确认
            return sig.confidence != "high"
        elif self.llm_confidence_threshold == "medium":
            # 中等和高置信度不需要确认
            return sig.confidence == "low"
        else:
            # 所有都需要确认（等同于 MODE_LLM_ONLY）
            return True
    
    async def _extract_with_llm(
        self,
        sentences: List[Dict],
        model_selection: Optional["ModelSelection"],
    ) -> List[SyntacticSignature]:
        """使用 LLM 提取句法特征。
        
        批量处理：一次调用分析多句。
        将 LLM 输出转换为统一的 SyntacticSignature 格式。
        """
        
        from app.services.analysis.rag.syntactic_analysis_agent import (
            SyntacticAnalysisDeps,
            run_syntactic_analysis_agent,
        )
        
        # 构建 deps
        deps = SyntacticAnalysisDeps(sentences=sentences)
        
        # 运行 Agent
        result = await run_syntactic_analysis_agent(
            deps=deps,
            model_selection=model_selection,
        )
        
        # 获取输出
        output = result.output if hasattr(result, "output") else result
        
        # 转换为统一格式
        signatures = []
        for idx, llm_sig in enumerate(output.sentences):
            sig = SyntacticSignature(
                source="llm",
                confidence=llm_sig.confidence,
            )
            
            # 复制特征
            sig.has_relative_clause = llm_sig.has_relative_clause
            sig.has_adverbial_clause = llm_sig.has_adverbial_clause
            sig.has_noun_clause = llm_sig.has_noun_clause
            sig.has_inversion = llm_sig.has_inversion
            sig.has_subjunctive = llm_sig.has_subjunctive
            sig.has_participle_phrase = llm_sig.has_participle_phrase
            sig.has_appositive = llm_sig.has_appositive
            sig.has_parenthetical = llm_sig.has_parenthetical
            sig.complexity_score = llm_sig.complexity_score
            
            # 计算 clause_count
            sig.clause_count = sum([
                sig.has_relative_clause,
                sig.has_adverbial_clause,
                sig.has_noun_clause,
            ])
            
            # 词数（从原句子获取）
            if 0 <= idx < len(sentences):
                sig.word_count = len(sentences[idx].get("text", "").split())
            
            signatures.append(sig)
        
        return signatures
```

---

## 5. 配置选项

```python
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class GrammarRagSettings:
    """Grammar RAG 配置（v2 扩展版）。"""
    
    # ========== 开关 ==========
    enabled: bool = False
    
    # ========== 特征提取配置 ==========
    # 提取模式
    # - "rules_only": 仅规则（最快，成本最低）
    # - "hybrid": 规则 + LLM 确认（平衡模式，推荐）
    # - "llm_only": 仅 LLM（最准确，成本最高）
    extraction_mode: Literal["rules_only", "hybrid", "llm_only"] = "hybrid"
    
    # 混合模式下的置信度阈值
    # - "high": 只有 high 置信度不需要 LLM 确认（更多句子用 LLM）
    # - "medium": medium 和 high 都不需要确认（更少句子用 LLM）
    llm_confidence_threshold: Literal["high", "medium"] = "medium"
    
    # ========== Vector DB 配置 ==========
    vector_db_type: Literal["chroma", "faiss", "pinecone"] = "chroma"
    vector_db_path: str = "./data/grammar_examples"
    collection_name: str = "grammar_examples"
    
    # ========== 检索配置 ==========
    # 每簇检索数量
    top_k_per_cluster: int = 2
    
    # 每簇最大数量限制（避免总数量过多）
    max_total_examples: int = 5
    
    # 最小需要的示例数量（不足时用 baseline 补充）
    min_required_examples: int = 2
    
    # 单簇检索超时
    per_cluster_timeout: float = 1.0
    
    # 总检索超时（所有簇）
    total_retrieval_timeout: float = 3.0
    
    # ========== 相似度权重 ==========
    structure_weight: float = 0.7
    semantic_weight: float = 0.3
    
    # ========== Embedding 配置 ==========
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
```

---

## 6. 实施路线图（v2 更新）

### Phase 1: 基础设施（Week 1-2）

- [x] 设计 v2 架构（分簇检索 + LLM 增强提取）
- [ ] 实现 `RuleBasedExtractor`（规则提取器）
- [ ] 实现 `SyntacticAnalysisAgent`（LLM 句法分析 Agent）
  - [ ] 定义 `LLMSyntacticSignature` 和 `LLMSyntacticAnalysisResult` Schema
  - [ ] 编写详细的 Prompt（包含易混淆情况的区分）
  - [ ] 实现 `run_syntactic_analysis_agent` 运行器
- [ ] 实现 `LLMAugmentedExtractor`（分层提取器）
- [ ] 搭建 Vector DB 抽象层
- [ ] 将现有硬编码示例转换为索引格式

### Phase 2: 核心检索（Week 3-4）

- [ ] 实现 `StructureClusterer`（结构分簇器）
  - [ ] 定义 `StructureClusterType` 优先级枚举
  - [ ] 实现分簇算法（一个句子可属于多个簇）
- [ ] 实现 `ClusterQueryBuilder`（每簇 Query 构造器）
- [ ] 实现 `MultiRouteRetriever`（多路检索器）
  - [ ] 每簇并行检索
  - [ ] 按优先级合并结果
  - [ ] 去重和数量限制
- [ ] 实现 `GrammarRagService`（核心服务整合）
- [ ] 实现完整的 Fallback 机制

### Phase 3
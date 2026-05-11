# 词典服务架构与查询策略

> 文档状态：**已实施**（最后更新 2026-04-12）
> 本文档整合了 TECD3 本地词典接入设计和查询策略优化两份文档。

---

## 1. 概述

### 1.1 定位

词典服务为「 Claread 透读」小程序提供点词查词能力，核心场景：

- 结果页点词查词
- 结果页点短语查词
- 生词本词条快照

### 1.2 产品要求

1. 普通单词点击后，尽量能命中正确词条
2. 短语点击后，优先命中完整短语，而不是被错误拆成单生词
3. 变形词点击后，尽量能回退到基础词形
4. 返回结构稳定，可被 `WordPopup`、详情弹层和生词本复用

---

## 2. 数据真源与离线导入

### 2.1 真源

词典内容真源：

- [英汉大词典（第三版）.mdx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/.dict/Mdict/TECD3/英汉大词典（第三版）.mdx)
- [英汉大词典（第三版）.mdd](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/.dict/Mdict/TECD3/英汉大词典（第三版）.mdd)
- [tecd3.css](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/.dict/Mdict/TECD3/tecd3.css)

### 2.2 运行时边界

- 不直接在 `/dict` 里读取 `.mdx/.mdd`
- 不在运行时即时解析 HTML
- 不把词典 provider 建在前端

运行时唯一真源：**PostgreSQL** + `/dict` 接口

### 2.3 导入链路

```
TECD3.mdx / TECD3.mdd
    ↓ mdict-utils 解包
unpacked_mdx/*.txt
    ↓ import_tecd3.py
dict_entries / dict_lookup_targets / dict_redirects
    ↓ /dict runtime lookup
```

### 2.4 导入后维护

- 数据重建时，以重新导入为准，不手工修库
- `mdict-utils` 只参与离线解包
- 非特殊情况，禁止删除、清空或重建 `dict_entries` / `dict_lookup_targets` / `dict_redirects`
- 如必须重建，必须先确认 TECD3 重导链路和 `exam_tag` 数据恢复方案可用

---

## 3. 数据库架构

### 3.1 表职责

| 表 | 职责 |
|---|---|
| `dict_entries` | 词条详情真源（词头、音标、义项、例句、短语、原始 HTML） |
| `dict_lookup_targets` | 可查形式 → 词条的检索索引 |
| `dict_redirects` | MDX 跳转、归一化别名等重定向关系 |

### 3.2 `dict_lookup_targets` 字段

| 字段 | 说明 |
|------|------|
| `normalized_form` | 归一化查询词形 |
| `lookup_label` | 显示用标签 |
| `target_label` | 目标词条 |
| `match_kind` | 命中来源：`headword / alias / redirect / nlp / phrase / phrase_template` |
| `lookup_type` | 查询类型：`word / phrase` |
| `rank` | 同形词排序权重 |
| `entry_id` | 关联 `dict_entries.id` |

### 3.3 Schema 基线

- 当前词典 schema 已并入 `db/migrations/0001_initial_schema.sql`
- `dict_lookup_targets.lookup_type` 与短语相关约束已经在初始 schema 中
- 开发期重置数据库时，优先清空非词典业务表，不动 `dict_*` 表

---

## 4. 查询策略（已实施）

### 4.1 总体流程

```
用户点击单词
    ↓
[1] 短语嗅探（spaCy 驱动）
    ↓ 未命中
[2] 表面形式 exact 查询
    ↓ 未命中
[3] Lemma 还原后再试
    ↓ 未命中
[4] 返回 404
```

### 4.2 短语嗅探（spaCy 驱动）

**目的**：不要急着查单词，先利用上下文判断是否存在"更长、更合理"的短语候选。

**候选生成顺序**（`phrase_candidates.py`）：

1. **Matcher 层**：高频有界模式（比较级、`be there for` 等）
2. **子树提取**：点击词的完整依存子树
3. **谓词 Head 提升**：从宾语/介词宾语回溯谓词头
4. **比较结构提取**：ADJ/ADV + than
5. **Anchored N-gram兜底**：窗口 2-4 的有限滑动

**模板归一化**（`phrase_templates.py`）：

```
you / him / her → sb
it / this / that → sth
your / his / her → sb's
```

例如：`be there for you` → `be there for sb`

### 4.3 批量召回与重排

**批量召回**（`db_pg.py`）：

```python
async def lookup_candidates_batch(normalized_forms: list[str]) -> list[CandidateRow]:
    # 一次 ANY() 查询所有候选词形
```

**7 维权重重排**（`providers/tecd3.py`）：

```
优先级维度（从高到低）：
1. phase：context phrase > direct phrase > lemma phrase > lemma direct
2. query_type_match：phrase 查询命中 phrase 索引优先
3. token_count：短语越长越优先
4. match_kind：phrase > headword > redirect > nlp
5. entry_kind：entry > fragment
6. rank：词典内置权重
7. entry_id：保证顺序稳定
```

### 4.4 Lemma 还原

**触发条件**：exact + phrase 都未命中

**实现**（`lemma.py`）：
- 使用 `spaCy` lemmatizer 还原词形
- `studies → study`，`took → take`

### 4.5 缓存隔离

缓存 Key 加入 `context_sentence` 的 MD5 哈希值，确保不同语境的点击不串缓存。

---

## 5. 缓存策略

### 5.1 多级缓存架构

```
前端（小程序）                   后端（FastAPI）                  存储
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
│ 内存 Map     │ →  │ L1 进程内    │ →  │ L2 Redis     │ →  │ PostgreSQL│
│ TTL 5min     │    │ OrderedDict  │    │ TTL 24h      │    │ 真源      │
│ max 200 条   │    │ TTL 24h      │    │ 跨 Worker    │    │          │
│ entry only   │    │ LRU 淘汰     │    │ 降级安全     │    │          │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────┘
```

| 层级 | 实现 | TTL | 容量 | 特性 |
|------|------|-----|------|------|
| 前端 | `dictCache.ts` 内存 Map | 5min | 200 条 | 仅缓存 entry 结果，不占 Taro Storage；LRU 淘汰 |
| L1 | `cache.py` OrderedDict | 24h | 1000 条/Worker | LRU 淘汰；满容量时先清过期再淘汰最旧 10%；hit/miss 计数 |
| L2 | Redis 7.2 | 24h | 按内存限制 | 跨 Worker 共享；不可用时自动降级为纯 L1 |
| 真源 | PostgreSQL | — | — | `dict_entries` / `dict_lookup_targets` / `dict_redirects` |

### 5.2 缓存 Key 格式

```
# lookup 查询缓存
{provider}:{version}:lookup:q={query}:type={type}:ctx={ctx_hash}:occ={occ}:strategy={strategy}

# entry 词条缓存
{provider}:{version}:entry:{entry_id}

# Redis L2 key 前缀
dict:{上述 cache_key}
```

### 5.3 缓存失效

- **版本失效**：词典数据重新导入时递增 `cache_version`（当前 `v4`），旧缓存 key 不再命中
- **语境隔离**：`context_sentence` 的 MD5 哈希值参与 key 计算，不同语境不串缓存
- **TTL 过期**：L1 惰性过期（读取时检查），L2 由 Redis TTL 自动管理
- **主动失效**：`cache.invalidate(key)` / `cache.invalidate_all()` 清除 L1 + L2

### 5.4 降级策略

- Redis 不可用时，L2 读写静默失败，退化为纯 L1 + PostgreSQL
- L1 满容量时：先清除过期条目，仍满则 LRU 淘汰最旧 10%
- 前端缓存未命中时直接发起网络请求，不阻塞用户

### 5.5 HTTP 缓存

- `/dict` 响应头：`Cache-Control: public, max-age=3600`
- `/dict/entry` 响应头：同上
- 词典数据变更频率极低（仅重新导入时变更），1 小时缓存合理

### 5.6 缓存预热

服务启动时预热高频功能词（the/a/is/are 等 36 个）到 L1 + L2，避免冷启动首批请求全部穿透到 DB。

### 5.7 缓存监控

`/health` 端点返回 `dict_cache` 统计信息：

```json
{
  "dict_cache": {
    "l1_size": 128,
    "l1_max_size": 1000,
    "l1_hits": 1024,
    "l1_misses": 256,
    "l2_hits": 180,
    "l2_misses": 76
  }
}
```

---

## 6. 已知数据质量问题

截至当前版本，确认以下问题类型：

### 6.1 词性归一化不稳定

- `ABBREVIATION 缩略词` 没有统一转成 `abbr.`
- `COMBINING FORM` 与 `comb.` 混用

**处理**：导入阶段必须做 POS canonicalization

### 6.2 多例句块被截断

- 同一 `egBlock` 里存在多个 `.ex`，旧逻辑只保留第一个

**处理**：导入阶段保留同一例句块中的多个 example

### 6.2a 释义内多例句被拼接成单字符串

- 当前 `import_tecd3.py` 会把同一释义节点下多条 `<li class="eg">` 用 `；` 拼接到 `definition.example` / `definition.example_translation`
- 这会让前端释义页把多条例句渲染成一个块状段落，影响阅读边注式展示
- 短期前端仅按导入拼接符 `\uFF1B` 做保守拆分展示
- 长期应将 `DictionaryMeaningDefinition` 升级为 `examples: [{ example, example_translation }]`，导入侧保留 `<li class="eg">` 级别结构，API 在迁移期兼容旧 `example` 字段

### 6.3 fragment 与弱结构词条

- TECD3 中存在大量 `fragment`、无稳定词性块的词条

**处理原则**：能保留详情就保留，不在导入阶段做高风险猜测

---

## 7. 直接相关文件

### 核心服务

| 文件 | 说明 |
|------|------|
| `app/services/dictionary/service.py` | 统一入口，请求归一化 |
| `app/services/dictionary/providers/tecd3.py` | TECD3 Provider，批量召回与重排 |
| `app/services/dictionary/db_pg.py` | PostgreSQL 查询接口 |
| `app/services/dictionary/nlp.py` | 词典专用 spaCy pipeline |
| `app/services/dictionary/phrase_candidates.py` | 短语候选生成 |
| `app/services/dictionary/phrase_templates.py` | 模板归一化（sb/sth/sb's） |
| `app/services/dictionary/lemma.py` | Lemma 候选生成 |
| `app/services/dictionary/cache.py` | 两级缓存实现 |
| `app/services/dictionary/schemas.py` | Pydantic 模型 |

### 脚本

| 文件 | 说明 |
|------|------|
| `scripts/import_tecd3.py` | MDX 离线导入 |
| `scripts/backfill_phrases.py` | phrase 索引补齐 |

### 数据库

| 文件 | 说明 |
|------|------|
| `db/migrations/0001_initial_schema.sql` | 初始表结构（含全部业务表 + 词典表） |
| `db/reset_dev_keep_dict.sql` | 仅清空业务表数据，保留 `dict_*` 数据和表结构 |
| `db/reset_full_keep_dict.sql` | DROP 业务表后需配合 0001 重建，保留 `dict_*` 数据 |

---

## 8. 当前不做

- 独立 dict service
- 前端直连词典真源
- 运行时直接读取 MDX/MDD
- 把运行时猜测结果写回 `dict_entries`

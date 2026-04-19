# Technical Design

## Overview

本次改造分为三层：

1. 生词条目模型扩展：以 `lemma` 为主键，补全 `dict_entry_id` 与 `source_refs`
2. 生词本详情增强：详情页优先展示完整词典数据与独立语境卡片
3. 结果页联动标注：分析完成后额外请求词汇匹配接口并渲染 saved-vocab overlay

本次明确不做：

- 复习日程与记忆曲线
- 独立背词模式
- 学习成就和 AI 学习路径分析
- 改造 `/analyze` 主流程
- 修改 `dict_entries`、`dict_lookup_targets`、`dict_redirects` 三张词典表

## Constraints

- 项目尚在开发阶段，不需要数据迁移，可直接重建 `vocabulary_book` 表
- 三张词典表（`dict_entries`、`dict_lookup_targets`、`dict_redirects`）只做只读引用，不修改
- 已有 `GET /dict/entry?id={dict_entry_id}` 接口可直接复用

## Data Design

重建 `vocabulary_book` 表，直接添加 `dict_entry_id` 列，同时将 `source_refs` 标准化到 `payload_json`。

### 数据库表结构

```sql
CREATE TABLE vocabulary_book (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  lemma TEXT NOT NULL,
  display_word TEXT NOT NULL,
  phonetic TEXT,
  part_of_speech TEXT,
  short_meaning TEXT NOT NULL,
  meanings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  exchange TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  source_provider TEXT NOT NULL DEFAULT 'tecd3',
  dict_entry_id BIGINT REFERENCES dict_entries(id) ON DELETE SET NULL,
  source_sentence TEXT,
  source_context TEXT,
  mastery_status TEXT NOT NULL DEFAULT 'new'
    CHECK (mastery_status IN ('new','learning','review','mastered','archived')),
  review_count INTEGER NOT NULL DEFAULT 0,
  last_reviewed_at TIMESTAMPTZ,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_vocabulary_book_user_lemma_lower
  ON vocabulary_book(user_id, LOWER(lemma));
CREATE INDEX idx_vocabulary_book_user_created_at
  ON vocabulary_book(user_id, created_at DESC);
CREATE INDEX idx_vocabulary_book_user_mastery_status
  ON vocabulary_book(user_id, mastery_status);
CREATE INDEX idx_vocabulary_book_dict_entry_id
  ON vocabulary_book(dict_entry_id) WHERE dict_entry_id IS NOT NULL;
```

与旧表的变化：

- 新增 `dict_entry_id BIGINT REFERENCES dict_entries(id) ON DELETE SET NULL` — 稳定引用词典词条
- 移除 `analysis_record_id UUID` — 来源记录关联统一通过 `payload_json.source_refs` 管理
- 新增 `idx_vocabulary_book_dict_entry_id` 索引 — 加速按词典词条反查

### payload_json 结构

```json
{
  "source_refs": [
    {
      "client_record_id": "task-xxx",
      "cloud_record_id": "uuid",
      "source_sentence": "The policy was adopted in 2020.",
      "source_context": null,
      "source_sentence_id": "s1",
      "source_anchor_text": "adopted",
      "source_occurrence": 1,
      "collected_at": "2026-04-19T10:00:00Z"
    }
  ],
  "collected_forms": ["adopted", "adopting"]
}
```

字段说明：

- `source_refs` — 多来源语境数组，每个 ref 对应一次收藏来源
- `collected_forms` — 用户实际收藏过的词形变体列表，用于详情页展示"收藏形态"
- 后续 AI 学习画像字段可以继续扩展在 `payload_json`

顶层兼容字段保留：

- `source_sentence` / `source_context` 继续作为顶层字段，存储最近一次来源，用于列表页快速展示
- `source_refs` 用于详情页和后续扩展

### Vocabulary Domain Model

把"生词本条目"拆成两个层次：

1. 核心词条层
   - `id`
   - `lemma`
   - `display_word`
   - `dict_entry_id`
   - `short_meaning`
   - `meanings_json`
   - `tags / exchange / provider`
   - `mastery_status`

2. 来源语境层
   - `source_refs[]`
   - 每个 ref 对应一次收藏来源
   - 保存 `record_id / sentence_id / anchor_text / occurrence / sentence / context`

这能避免当前"同一词重复收藏"和"来源句被覆盖"的冲突。

## API Design

### Existing `/vocabulary`

扩展 request/response schema，暴露：

- `dict_entry_id`
- `source_refs`
- `collected_forms`

POST `/vocabulary` 请求体更新：

```json
{
  "lemma": "adopt",
  "display_word": "adopted",
  "phonetic": "/əˈdɒpt/",
  "part_of_speech": "v.",
  "short_meaning": "采纳，采用",
  "meanings_json": [...],
  "tags": ["cet4", "cet6"],
  "exchange": ["adopts", "adopted", "adopting"],
  "source_provider": "tecd3",
  "dict_entry_id": 12345,
  "source_sentence": "The policy was adopted in 2020.",
  "source_context": null,
  "payload_json": {
    "source_refs": [...],
    "collected_forms": ["adopted"]
  }
}
```

云端 upsert 逻辑更新：

- 冲突时（同 `user_id + lemma`）不再覆盖 `source_sentence` 等来源字段
- 而是将新来源追加到 `payload_json.source_refs`
- 将新词形追加到 `payload_json.collected_forms`
- 更新 `meanings_json` 等词条信息（取最新）
- 更新顶层 `source_sentence` 为最近一次来源

GET `/vocabulary` 更新：

- 移除 `lite=true` 模式，默认返回完整数据（含 `meanings_json`、`source_sentence`、`payload_json`）
- 或新增 `lite=enhanced` 模式：返回 `source_sentence` 但省略 `meanings_json`（详情页按需加载）

### Existing `/dict`

不修改。vocabulary 详情页通过已有接口获取完整词条：

```text
GET /dict/entry?id={dict_entry_id}
```

### New `/vocabulary/highlights`

新增结果页 overlay 接口：

```text
POST /vocabulary/highlights
```

请求：

```json
{
  "sentences": [
    {
      "sentence_id": "s1",
      "tokens": ["The", "policy", "was", "adopted", "in", "2020"]
    }
  ]
}
```

响应：

```json
{
  "matches": [
    {
      "vocab_id": "uuid",
      "lemma": "adopt",
      "sentence_id": "s1",
      "anchor_text": "adopted",
      "occurrence": 1,
      "mastery_status": "learning"
    }
  ]
}
```

匹配逻辑：

- 对单词：使用 `lemma.py` 的 lemma candidates 与用户生词本 lemma 集合匹配
- 对短语：先做 exact phrase match
- 不改 `/analyze` 主流程
- 只读 `lemma.py` 和 `vocabulary_book`，不涉及 dict 表写操作

性能策略：

- 接口做缓存（按用户 + 句子列表 hash 缓存结果）
- 前端做 debounce（页面渲染完成后 500ms 再请求）
- 匹配算法用 lemma candidates 预计算索引

## Matching Strategy

### Why not merge into `/analyze`

- `/analyze` 应保持"文本解析"职责单一
- 生词本是用户资产，属于登录态数据
- 结果页 overlay 是明显的后置增强，不应该阻塞主结果生成

### Word Matching

建议顺序：

1. `lookupText` / 点击词原文转小写
2. 基础清洗：
   - 去首尾标点
   - 统一引号
   - 处理所有格形式
3. `lemma.py` 生成 lemma candidates
4. 与用户生词本 lemma 集合匹配

### Phrase Matching

建议只做 exact phrase match：

- 第一版不做复杂 n-gram 召回
- 避免和现有 phrase/context annotation 冲突
- 为后续 phrase 学习能力预留扩展点

## Frontend Design

### Result Page

- 分析结果渲染完成后，额外请求 vocabulary highlights
- 将 saved-vocab marks 作为独立 overlay 数据传入 `ParagraphBlock`
- `InlineMark` / `ClickableWord` 的 saved 状态改为独立视觉层

### Saved-Vocab Visual Language

采用"批注感"设计，与现有 `visualTone` 完全独立：

- 浅色圆角背景 + 左侧小竖线（类似纸质书旁批标记）
- 颜色用淡蓝灰色，与现有教学高亮的暖色系区分
- hover/点击态：圆角背景加深 + 显示小书签图标
- 在 active 状态下继续以点击态优先

不建议：

- 再加一层新的底色
- 沿用当前 saved 下划线（容易与超链接混淆）
- 用与 `vocab/phrase/context` 相近的颜色体系

### Vocab Page

- 默认加载完整云端 vocabulary 数据（移除 `lite=true`）
- 增加搜索与掌握状态筛选
- 列表卡片右侧增加来源数量徽标（如 "2 篇"）

列表信息层级：

1. 第一行：单词、音标、掌握态、来源数量徽标
2. 第二行：词性 + 核心释义
3. 第三行：最近收藏语境句 + "还有 N 个语境"
4. 底部：收藏时间、查看详情

详情页信息层级（语境优先）：

1. Hero 区：单词、音标、lemma、收藏形态标签、发音按钮
2. 语境区：来源句子卡片（横向滑动）+ "已收藏于 N 个语境" + "查看原文"按钮
3. 词典区：释义 / 短语 / 例句 tabs
4. 操作区：标记掌握、删除

### Context Card Design

语境卡片采用横向滑动展示：

- 每个卡片显示：来源句子 + 来源文章标题 + 收藏时间 + "查看原文"按钮
- 当前卡片 + 右侧滑动提示 + 计数器 "1/3"
- 单条语境时不需要滑动，直接展示

### Merge Feedback

收藏归并时的用户反馈：

- 当用户收藏 "adopted" 但生词本已有 "adopt" 时
- toast 提示："adopted 已添加到 adopt（第 2 个语境）"
- 而不是静默合并让用户困惑

### Source Context UX

从生词本点击原文的路径拆成两层：

1. 先在详情页看到独立句子语境
2. 再点击"查看原文"

跳转前判断：

- 本地 record 存在且未 tombstone：可跳
- 本地不存在但云端 `/records/by-client-id` 仍可取回：可跳
- 否则不可跳，并提示"原文记录已删除或不可用"

### Pronunciation

详情页 Hero 区增加发音按钮，使用 Free Dictionary API 获取音频：

**音频来源**：[Free Dictionary API](https://dictionaryapi.dev/)

```text
GET https://api.dictionaryapi.dev/api/v2/entries/en/{word}
```

响应中 `phonetics[].audio` 字段提供 MP3 音频 URL：

```json
{
  "word": "adopt",
  "phonetics": [
    { "text": "/əˈdɒpt/", "audio": "" },
    { "text": "/əˈdɑpt/", "audio": "https://api.dictionaryapi.dev/media/pronunciations/en/adopt-us.mp3" }
  ]
}
```

**实现方案**：

- 生词本详情页打开时，用 `display_word` 或 `lemma` 请求 Free Dictionary API
- 从 `phonetics` 数组中筛选第一个有 `audio` URL 的条目（优先美音）
- 缓存音频 URL 到 `payload_json.audio_url`，避免重复请求
- 点击发音按钮时播放缓存的 MP3 URL
- API 不可用或无音频时，隐藏发音按钮（而非显示不可用状态）

**限制与注意事项**：

- Free Dictionary API 无需 API Key，免费使用
- 频率限制：1000 请求/小时/IP，生词本场景（按需单次请求）远低于此限制
- 音频来源为 Wiktionary（CC BY-SA 3.0 协议）
- 部分低频词可能无音频，此时隐藏发音按钮
- 结果页查词卡片暂不加入发音功能，仅在生词本详情页引入

## Navigation Design

从生词本跳结果页时增加 `sentenceId` 参数：

```text
/pages/result/index?recordId={clientRecordId}&mode=replay&sentenceId={sentenceId}
```

结果页在 replay mode 下：

- 读取 `sentenceId`
- 设置 active sentence
- 滚动到句子位置

如果记录被删除：

- 本地 `tombstone` 或云端 `/records/by-client-id/{id}` 返回 404
- 详情页显示"原文记录不可用"

第一版只实现 sentence 级定位，`anchorText` 和 `occurrence` 作为可选参数预留。

## Code Architecture

### Backend Modules

改动面：

- `server/db/migrations/` — 新增 migration 重建 `vocabulary_book` 表
- `server/app/schemas/user_assets/vocabulary.py` — 扩展 schema
- `server/app/api/routes/vocabulary.py` — 更新路由逻辑
- `server/app/services/user_assets/vocabulary.py` — 改造 upsert 合并逻辑
- `server/app/services/dictionary/lemma.py` — 只读复用，不改

职责边界：

- route：组装/返回 DTO
- vocabulary service：生词本数据读写与匹配（upsert 时追加 source_refs 而非覆盖）
- dictionary lemma：词形归并能力（只读）

### Frontend Modules

改动面：

- `client/src/types/view/vocabulary.vm.ts` — 扩展 VM 类型
- `client/src/services/api/vocabulary.client.ts` — 更新 DTO 映射
- `client/src/services/storage/index.ts` — 本地以 lemma 去重 + source refs 合并
- `client/src/pages/vocab/index.tsx` — 列表页升级
- `client/src/components/VocabDetailView/*` — 详情页升级
- `client/src/pages/result/index.tsx` — 收藏逻辑更新 + overlay 数据拉取
- `client/src/components/ParagraphBlock/index.tsx` — 消费 overlay
- `client/src/components/InlineMark/*` — saved-vocab 视觉
- `client/src/components/ClickableWord/*` — saved-vocab 视觉

职责边界：

- `storage`：本地 lemma 合并与 source refs 合并
- `api/vocabulary.client`：云端 DTO 映射
- `result page`：拉取 overlay 数据
- `ParagraphBlock`：消费 overlay，不负责业务请求
- `VocabDetailView`：展示完整词条和来源语境

## Rollout Strategy

按两阶段交付：

### Phase A — 生词本核心体验

- 重建 `vocabulary_book` 表（新增 `dict_entry_id` 列）
- 保存完整 metadata（`dict_entry_id` + `source_refs` + `collected_forms`）
- 本地以 lemma 去重合并
- 生词本详情展示完整词条（通过 `/dict/entry` 按需加载）
- 语境卡片（横向滑动）+ 条件跳转
- 收藏归并用户反馈（toast 提示）
- 发音播放
- 列表来源数量可视化

### Phase B — 结果页联动与搜索

- 结果页 saved-vocab overlay
- 列表搜索/筛选与视觉优化
- 字母索引侧边栏（可选）

这样可以先解决"生词本不好看、不好用、数据不完整"的主问题，再补结果页联动。

## Test Strategy

- Python: 编译检查新增 schema / route / service
- TypeScript: `tsc --noEmit`
- 手工验证链路：
  - 收藏单词 -> 生词本详情展示完整词条
  - 同 lemma 再次收藏 -> 合并 source refs + toast 提示
  - 删除原文记录 -> 生词详情不跳转 + 提示不可用
  - 结果页加载后出现 saved-vocab overlay
  - 详情页发音播放正常

## Open Questions (Resolved)

1. **同 lemma 合并后，列表默认显示"最近一次来源"还是"首次来源"**
   → 最近一次来源。最近收藏的语境记忆更鲜活，与"最新在前"的列表排序一致。

2. **`source_refs` 是否需要设置上限**
   → 建议上限 20 条。避免单条记录过大影响存储和传输性能，20 条足够覆盖绝大多数场景；超出时保留最近 20 条。

3. **结果页 saved-vocab overlay 是否对匿名用户完整开启**
   → 对匿名用户使用本地生词做局部开启。匿名用户没有云端生词本，只能匹配本地存储的词；给未登录用户"尝鲜"体验，同时激励登录。

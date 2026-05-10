# Data & API

## Existing Data

现有 `users` 表：

- `settings_json JSONB`
- `metadata_json JSONB`

现有 `favorite_records` 表已支持：

- `target_type`
- `target_key`
- `analysis_record_id`
- `payload_json`
- `note`

因此：

- 阅读设置保存到用户配置 JSON。
- 句子收藏复用 `favorite_records`；段落收藏字段保留但不作为首版前端交付。
- 用户自行批注新建表。
- “我的摘录”前端按 `target_key` 合并同一句子的收藏、用户批注和解析要点，形成句子级复习资产。

## Reading Settings Shape

建议保存位置：

- 优先：`users.metadata_json.reading_preferences`
- 如果现有 profile API 只支持 `settings`，可先保存到 `settings_json.reading_preferences`，但字段名保持一致，后续可迁移。

JSON shape：

```json
{
  "reading_preferences": {
    "font_size": "standard",
    "line_height": "standard",
    "translation_display": "muted",
    "paper_theme": "paper",
    "updated_at": "2026-05-08T12:00:00Z"
  }
}
```

枚举：

- `font_size`: `small | standard | large | xlarge`
- `line_height`: `compact | standard | loose`
- `translation_display`: `hidden | muted | standard`
- `paper_theme`: `paper | white | sage`

## New Table: user_annotations

```sql
CREATE TABLE user_annotations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  analysis_record_id UUID REFERENCES analysis_records(id) ON DELETE CASCADE,
  annotation_type TEXT NOT NULL CHECK (annotation_type IN ('highlight', 'note')),
  anchor_type TEXT NOT NULL CHECK (anchor_type IN ('sentence', 'paragraph', 'text_range')),
  target_key TEXT NOT NULL,
  paragraph_id TEXT,
  sentence_id TEXT,
  selected_text TEXT NOT NULL,
  start_offset INTEGER,
  end_offset INTEGER,
  text_hash TEXT,
  color TEXT NOT NULL DEFAULT 'soft_green'
    CHECK (color IN ('soft_green', 'soft_blue', 'soft_purple')),
  note TEXT,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  deleted_at TIMESTAMPTZ,
  deleted_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_user_annotations_target UNIQUE (user_id, target_key)
);

CREATE INDEX idx_user_annotations_record_created
  ON user_annotations(user_id, analysis_record_id, created_at DESC)
  WHERE deleted_at IS NULL;

CREATE INDEX idx_user_annotations_sentence
  ON user_annotations(user_id, analysis_record_id, sentence_id)
  WHERE sentence_id IS NOT NULL AND deleted_at IS NULL;
```

`target_key` 生成规则：

- sentence: `record:{record_id}:sentence:{sentence_id}`
- paragraph: `record:{record_id}:paragraph:{paragraph_id}`（后端兼容字段，首版前端不生成）
- text_range: `record:{record_id}:range:{sentence_id}:{start_offset}:{end_offset}:{text_hash}`

小程序首版只使用 `sentence` 锚点。`paragraph`、`text_range`、`start_offset`、`end_offset`、`text_hash`
保留为后端兼容和未来增强能力，不作为当前前端交付范围。

## API

### Reading Preferences

可扩展现有接口：

- `GET /auth/session/me` 返回 `settings.reading_preferences` 或 `metadata.reading_preferences`
- `PATCH /auth/profile` 支持更新 `reading_preferences`

更清晰的后续接口：

- `GET /users/me/reading-preferences`
- `PATCH /users/me/reading-preferences`

首版为了减少 API 面，可先复用 `/auth/profile`。

### User Annotations

新增路由：

- `POST /user-annotations`
- `GET /user-annotations?analysis_record_id={id}`，这里的 `{id}` 必须是云端 `analysis_records.id` UUID；本地 `client_record_id` 只放入 `payload_json.client_record_id`
- `PATCH /user-annotations/{id}`
- `DELETE /user-annotations/{id}`

Create request：

```json
{
  "analysis_record_id": "uuid",
  "annotation_type": "note",
  "anchor_type": "sentence",
  "target_key": "record:xxx:sentence:s2",
  "paragraph_id": "p1",
  "sentence_id": "s2",
  "selected_text": "Advocates typically frame themselves...",
  "color": "soft_green",
  "note": "这里是作者引入两种立场的地方",
  "payload_json": {
    "source": "result_page",
    "translation": "倡导者通常将自己定位为..."
  }
}
```

### Favorites

复用现有：

- `POST /favorites`
- `GET /favorites`
- `DELETE /favorites/target`

句子收藏 request：

```json
{
  "analysis_record_id": "uuid",
  "target_type": "sentence",
  "target_key": "record:xxx:sentence:s2",
  "payload_json": {
    "paragraph_id": "p1",
    "sentence_id": "s2",
    "text": "Advocates typically frame themselves...",
    "translation": "倡导者通常将自己定位为..."
  }
}
```

## Client State

新增本地状态：

- `readingPreferences`
- `selectionContext`
- `selectionToolbarVisible`
- `userAnnotationsBySentenceId`
- `favoriteTargetKeys`
- `excerptGroupsByRecord`
- `excerptFilter`

离线/未登录：

- 已登录：写云端，成功后更新本地缓存。
- 未登录：可以先支持复制；收藏/笔记提示登录或写本地草稿，后续登录再同步。

## Excerpts View Model

“我的摘录”不新增后端聚合接口，首版在前端基于现有数据合成 VM：

- 收藏：来自 `favorite_records` 中 `target_type='sentence'` 的记录。
- 高亮/笔记：来自 `user_annotations`，按 `target_key` 合并到同一句。
- 解析要点：来自分析记录内已存在的 sentence-level 语法/句析数据；只在前端展示，不写回收藏或批注表。

合并规则：

- 主键：`target_key`。
- 文章归组：优先使用 `analysis_record_id`；缺失时使用 payload 中的 client record 标识作为降级。
- 句子排序：使用 `sentence_id` 中可解析出的序号，无法解析时使用 payload 中的顺序字段，最后才按创建时间兜底。
- 同一句同时有收藏、高亮、笔记时只生成一条 sentence item，状态标签并列展示。
- 过滤 `解析` 时，只展示存在语法或句析复习要点的句子；过滤 `全部` 时仍展示完整复习要点。

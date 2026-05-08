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
- 句子/段落收藏复用 `favorite_records`。
- 用户自行批注新建表。

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
    "paragraph_spacing": "standard",
    "translation_display": "muted",
    "paper_theme": "paper",
    "annotation_intensity": "standard",
    "updated_at": "2026-05-08T12:00:00Z"
  }
}
```

枚举：

- `font_size`: `small | standard | large | xlarge`
- `line_height`: `compact | standard | loose`
- `paragraph_spacing`: `compact | standard | loose`
- `translation_display`: `hidden | muted | standard`
- `paper_theme`: `paper | white | sage`
- `annotation_intensity`: `quiet | standard | clear`

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
  color TEXT NOT NULL DEFAULT 'warm_yellow'
    CHECK (color IN ('warm_yellow', 'soft_blue', 'sage_green')),
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
- paragraph: `record:{record_id}:paragraph:{paragraph_id}`
- text_range: `record:{record_id}:range:{sentence_id}:{start_offset}:{end_offset}:{text_hash}`

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
- `GET /user-annotations?analysis_record_id={id}`
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
  "color": "warm_yellow",
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

离线/未登录：

- 已登录：写云端，成功后更新本地缓存。
- 未登录：可以先支持复制；收藏/笔记提示登录或写本地草稿，后续登录再同步。


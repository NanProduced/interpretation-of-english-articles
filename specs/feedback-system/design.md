# Technical Design

## Overview

本次开发分为三层：

1. 数据层：新建 `feedback` 表 + 扩展 `user_credit_ledger` entry_type
2. 后端 API 层：反馈 CRUD + 积分明细查询 + 奖励积分发放
3. 前端交互层：四个反馈场景的组件与页面 + 积分明细页

本次明确不做：

- 微信订阅消息推送
- AI 智能标签分类
- 管理后台前端界面
- 收集用户联系方式

## Data Design

### feedback 表

```sql
CREATE TABLE feedback (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    feedback_scope  TEXT NOT NULL CHECK (feedback_scope IN (
                        'analysis_result',
                        'annotation',
                        'dictionary',
                        'app'
                    )),

    target_id       TEXT NOT NULL,

    analysis_record_id UUID REFERENCES analysis_records(id) ON DELETE CASCADE,

    sentiment       TEXT NOT NULL CHECK (sentiment IN ('positive', 'negative', 'neutral')),

    feedback_type   TEXT NOT NULL,

    annotation_type TEXT,

    content         TEXT,

    context_json    JSONB NOT NULL DEFAULT '{}'::jsonb,

    app_version     TEXT,
    client_platform TEXT NOT NULL DEFAULT 'wechat_miniprogram',

    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
                        'pending', 'adopted', 'resolved', 'dismissed'
                    )),

    reward_points   INTEGER NOT NULL DEFAULT 0,
    reward_granted_at TIMESTAMPTZ,

    admin_note      TEXT,
    reviewed_at     TIMESTAMPTZ,
    reviewed_by     UUID REFERENCES users(id) ON DELETE SET NULL,

    rag_harvested   BOOLEAN NOT NULL DEFAULT FALSE,
    rag_harvested_at TIMESTAMPTZ,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_feedback_user_target_type UNIQUE (user_id, target_id, feedback_type)
);

CREATE INDEX idx_feedback_user_created ON feedback(user_id, created_at DESC);
CREATE INDEX idx_feedback_scope_type ON feedback(feedback_scope, feedback_type);
CREATE INDEX idx_feedback_record ON feedback(analysis_record_id)
    WHERE analysis_record_id IS NOT NULL;
CREATE INDEX idx_feedback_annotation_type ON feedback(annotation_type)
    WHERE annotation_type IS NOT NULL;
CREATE INDEX idx_feedback_sentiment ON feedback(sentiment, feedback_scope);
CREATE INDEX idx_feedback_status ON feedback(status)
    WHERE status = 'pending';
CREATE INDEX idx_feedback_rag_harvested ON feedback(rag_harvested)
    WHERE rag_harvested = FALSE AND feedback_scope IN ('annotation', 'dictionary');
CREATE INDEX idx_feedback_context ON feedback USING GIN(context_json);

CREATE TRIGGER trg_feedback_set_updated_at
BEFORE UPDATE ON feedback
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE feedback IS '用户反馈表，统一存储结果页整体反馈、批注级反馈、词典反馈和应用功能反馈。';
COMMENT ON COLUMN feedback.feedback_scope IS '反馈作用域：analysis_result（结果页整体）、annotation（批注级）、dictionary（词典）、app（应用功能）。';
COMMENT ON COLUMN feedback.target_id IS '反馈目标标识：analysis_result 为 record_id，annotation 为 mark.id/sentence_entry.id，dictionary 为 dict_entry_id 或 word，app 为功能区域标识。';
COMMENT ON COLUMN feedback.sentiment IS '情感倾向：positive（正面）、negative（负面）、neutral（中性）。dictionary 作用域仅允许 negative。';
COMMENT ON COLUMN feedback.feedback_type IS '结构化反馈分类，含义随 feedback_scope 变化。';
COMMENT ON COLUMN feedback.annotation_type IS '标注类型，仅 annotation 作用域有值。';
COMMENT ON COLUMN feedback.context_json IS '反馈时的上下文快照 JSON，用于 RAG 训练数据提取。';
COMMENT ON COLUMN feedback.status IS '处理状态：pending（待处理）、adopted（已采纳，触发奖励）、resolved（已解决）、dismissed（已关闭）。';
COMMENT ON COLUMN feedback.reward_points IS '因反馈被采纳而发放的奖励积分数，0 表示未发放。';
COMMENT ON COLUMN feedback.rag_harvested IS '是否已被用于 RAG 训练数据提取。';
```

### user_credit_ledger entry_type 扩展

```sql
ALTER TABLE user_credit_ledger DROP CONSTRAINT user_credit_ledger_entry_type_check;
ALTER TABLE user_credit_ledger ADD CONSTRAINT user_credit_ledger_entry_type_check
  CHECK (entry_type IN (
    'daily_grant', 'bonus_grant', 'analysis_deduct',
    'manual_adjust', 'refund', 'feedback_reward'
  ));
```

### feedback_type 按场景的枚举定义

```python
FEEDBACK_TYPES_BY_SCOPE = {
    "analysis_result": {
        "positive": ["thumbs_up"],
        "negative": [
            "translation_inaccurate",
            "too_few_annotations",
            "too_many_annotations",
            "wrong_difficulty",
            "other",
        ],
    },
    "annotation": {
        "positive": ["helpful"],
        "negative": [
            "wrong_label",
            "inaccurate",
            "wrong_boundary",
            "should_not_annotate",
            "other",
        ],
    },
    "dictionary": {
        "negative": [
            "wrong_definition",
            "missing_definition",
            "wrong_pos",
            "wrong_phonetic",
            "bad_example",
            "other",
        ],
    },
    "app": {
        "neutral": [
            "bug_report",
            "feature_request",
            "quota_issue",
            "input_page_issue",
            "ux_issue",
            "other",
        ],
    },
}
```

### context_json 按场景的结构定义

**annotation 场景**（必填）：

```json
{
  "mark_id": "im_a1b2c3d4e5f6",
  "mark_data": {},
  "source_sentence": "原文句子",
  "translation": "中文翻译",
  "reading_goal": "exam",
  "reading_variant": "cet4"
}
```

**dictionary 场景**（必填）：

```json
{
  "word": "bank",
  "phonetic": "/bæŋk/",
  "current_meaning": "银行；金融机构",
  "dict_source": "tecd3",
  "dict_entry_id": 12345,
  "context_sentence": "The bank of the river was covered with wildflowers.",
  "disambiguation_chosen": "地理术语义",
  "reading_variant": "cet4"
}
```

**analysis_result 场景**（可选）：

```json
{
  "reading_goal": "exam",
  "reading_variant": "cet4",
  "source_text_length": 1500,
  "annotation_count": { "vocab": 12, "phrase": 5 },
  "user_facing_state": "normal"
}
```

**app 场景**（可选）：

```json
{
  "app_area": "input_page",
  "app_version": "1.0.0"
}
```

## API Design

### 用户侧 API

#### POST /api/feedback

提交反馈（核心接口）。

请求体：

```python
class FeedbackCreateRequest(BaseModel):
    feedback_scope: Literal["analysis_result", "annotation", "dictionary", "app"]
    target_id: str
    analysis_record_id: UUID | None = None
    sentiment: Literal["positive", "negative", "neutral"]
    feedback_type: str
    annotation_type: str | None = None
    content: str | None = None
    context_json: dict = {}
    app_version: str | None = None
```

校验规则：

- `feedback_scope='dictionary'` 时，`sentiment` 必须为 `'negative'`
- `feedback_scope='annotation'` 时，`annotation_type` 必填
- `feedback_scope` 为 `'analysis_result'` 或 `'annotation'` 时，`analysis_record_id` 必填
- `feedback_type` 必须在对应 scope 的枚举值范围内
- `sentiment` 必须与 `feedback_type` 所在的情感分组一致

响应体：

```python
class FeedbackResponse(BaseModel):
    id: UUID
    feedback_scope: str
    target_id: str
    sentiment: str
    feedback_type: str
    status: str
    created_at: datetime
```

Upsert 语义：UNIQUE 约束 `(user_id, target_id, feedback_type)` 冲突时更新 `sentiment`、`content`、`context_json`、`annotation_type`。

#### GET /api/feedback

查询当前用户的反馈列表（分页，供"我的反馈"使用）。

查询参数：

- `cursor`: 游标（feedback id，可选）
- `limit`: 每页条数，默认 20
- `feedback_scope`: 按作用域筛选（可选）

响应体：

```python
class FeedbackListItem(BaseModel):
    id: UUID
    feedback_scope: str
    feedback_type: str
    sentiment: str
    content: str | None
    status: str
    reward_points: int
    created_at: datetime

class FeedbackListResponse(BaseModel):
    items: list[FeedbackListItem]
    cursor: str | None
    has_more: bool
```

#### DELETE /api/feedback/{id}

删除反馈（仅限自己的、pending 状态的）。

#### GET /api/me/credit/ledger

查询积分流水（分页）。

查询参数：

- `cursor`: 游标（ledger id，可选）
- `limit`: 每页条数，默认 20

响应体：

```python
class LedgerEntryResponse(BaseModel):
    id: UUID
    entry_type: str
    points: int
    bucket_type: str
    balance_after: int
    description: str
    article_title: str | None
    created_at: datetime

class LedgerListResponse(BaseModel):
    items: list[LedgerEntryResponse]
    cursor: str | None
    has_more: bool
```

description 生成规则：

| entry_type | description |
|------------|-------------|
| `analysis_deduct` | "分析扣减"（+ article_title） |
| `feedback_reward` | "反馈奖励 · 你的反馈已被采纳" |
| `daily_grant` | "每日常规额度刷新" |
| `bonus_grant` | "奖励积分到账" |
| `refund` | "分析失败 · 积分退回" |
| `manual_adjust` | "管理员调整" |

article_title 通过 task_id JOIN analysis_records 获取。

### 内部管理 API

供云后台调用，使用 API Key 认证（非用户 session）。

#### PATCH /api/internal/feedback/{id}/status

更新反馈状态。

请求体：

```python
class FeedbackStatusUpdateRequest(BaseModel):
    status: Literal["adopted", "resolved", "dismissed"]
    admin_note: str | None = None
```

#### POST /api/internal/feedback/{id}/reward

发放反馈奖励积分。

请求体：

```python
class FeedbackRewardRequest(BaseModel):
    points: int  # 必须 > 0
```

处理逻辑：

1. UPDATE feedback SET status='adopted', reward_points=N, reward_granted_at=NOW()
2. credit_service.grant_bonus_credits(user_id, points, 'feedback_reward', metadata)
3. 无推送、无通知、无弹窗（静音）

#### GET /api/internal/feedback/stats

反馈统计概览。

## Credit Service Extension

### grant_bonus_credits 函数

```python
async def grant_bonus_credits(
    user_id: UUID,
    points: int,
    entry_type: str = "feedback_reward",
    metadata: dict[str, Any] | None = None,
) -> int:
```

关键设计：

- `task_id` 设为 NULL（反馈奖励不关联分析任务）
- `bucket_type` 为 `'bonus'`（发放到 bonus 桶，长期有效）
- `points` 为正数
- 在事务内完成：读取账户 → 更新 bonus_points → 写入 ledger
- 返回实际发放积分数

### 每日重置补充 daily_grant 写入

当前每日重置只更新 `user_credit_accounts.daily_used_points = 0`，不写入 ledger。建议在本次改造中补充：每日重置时写入一条 `daily_grant` 类型的 ledger 记录，让积分明细页能展示"每日发放"流水。

## Frontend Design

### F1：结果页整体反馈

位置：结果页底部操作栏区域。

交互流程：

1. 显示 👍 / 👎 按钮
2. 点击 👍 → 直接提交 `feedback_scope='analysis_result'`, `sentiment='positive'`, `feedback_type='thumbs_up'`
3. 点击 👎 → 展开负面选项面板（5 个选项 + 可选文本输入 + 提交按钮）
4. 提交后按钮状态变化（已反馈标识），toast 确认

### F2：批注级反馈

入口 A：长按 InlineMark 标注 → 弹出操作浮层（含反馈选项）

入口 B：AnalysisCard 展开后右上角反馈图标 → 弹出反馈选项

反馈选项：

- 正面：有帮助
- 负面：标注有误、释义不准确、标注范围有误、不该标注、其他

提交时自动捕获 context_json（从当前 sceneData 中提取标注数据）。

### F3：应用功能反馈

位置：个人配置页 → "意见反馈" 菜单项 → 独立反馈页面。

页面结构：

1. 反馈分类选择（6 个 chip）
2. 问题描述文本框（必填）
3. 提交按钮
4. 底部"我的反馈"入口

不收集联系方式。

### F4：词典反馈

位置：WordPopup full 模式底部操作栏。

布局调整：[收藏] [反馈] [记入生词本]，三按钮各占 flex: 1。

点击"反馈"后弹出负面选项（仅负面）：

- 释义错误、释义缺失、词性标注有误、音标有误、例句不当、其他

提交时自动捕获 context_json（单词、音标、释义、词典来源、所在句子）。

### F5：积分明细页

位置：个人配置页 → 点击额度明细区域 → 跳转积分明细页。

页面结构：

1. 顶部摘要：当前可用（每日常规 + 奖励）
2. 流水列表（按时间倒序，按日期分组）
3. 每条流水：图标 + 类型标签 + 积分变动（颜色区分）+ 描述 + 余额 + 时间
4. 滚动加载更多

entry_type 展示映射：

| entry_type | 颜色 | 中文标签 |
|------------|------|---------|
| analysis_deduct | 红色 | 分析扣减 |
| feedback_reward | 绿色 | 反馈奖励 |
| daily_grant | 绿色 | 每日发放 |
| bonus_grant | 绿色 | 奖励到账 |
| refund | 蓝色 | 积分退回 |
| manual_adjust | 灰色 | 管理员调整 |

### F6：我的反馈

位置：应用功能反馈页底部 → "我的反馈"入口。

列表展示：反馈类型、内容预览、状态标签、提交时间。已采纳的反馈显示奖励积分徽标。

## Code Architecture

### Backend Modules

新增文件：

- `server/db/migrations/0002_feedback_system.sql` — feedback 表 + credit_ledger 扩展
- `server/app/schemas/feedback.py` — Pydantic models
- `server/app/services/feedback/service.py` — 反馈业务逻辑
- `server/app/api/routes/feedback.py` — 用户侧反馈路由
- `server/app/api/routes/internal_feedback.py` — 内部管理路由

修改文件：

- `server/app/api/router.py` — 注册新路由
- `server/app/services/analysis/credit_service.py` — 新增 grant_bonus_credits + 补充 daily_grant
- `server/app/api/routes/quota.py` — 新增 GET /me/credit/ledger

### Frontend Modules

新增文件：

- `client/src/pages/feedback/index.tsx` — 应用功能反馈页
- `client/src/pages/feedback/my-feedback.tsx` — 我的反馈列表
- `client/src/pages/credit-detail/index.tsx` — 积分明细页
- `client/src/components/FeedbackWidget/index.tsx` — 结果页 👍👎 组件
- `client/src/components/AnnotationFeedback/index.tsx` — 批注级反馈浮层
- `client/src/components/DictionaryFeedback/index.tsx` — 词典反馈选项浮层
- `client/src/services/api/feedback.client.ts` — 反馈 API client
- `client/src/services/api/credit.client.ts` — 积分明细 API client

修改文件：

- `client/src/app.config.ts` — 注册新页面
- `client/src/pages/result/index.tsx` — 集成 FeedbackWidget
- `client/src/components/ParagraphBlock/index.tsx` — 长按反馈入口
- `client/src/components/AnalysisCard/index.tsx` — 反馈图标入口
- `client/src/components/WordPopup/index.tsx` — 词典反馈按钮
- `client/src/pages/profile/index.tsx` — 额度区域点击跳转 + 反馈菜单项

## Rollout Strategy

按三阶段交付：

### Phase 1 — 数据库与后端 API

- 创建 migration
- feedback schema + service + routes
- grant_bonus_credits + credit ledger API
- 内部管理 API

### Phase 2 — 前端反馈组件与页面

- 结果页整体反馈组件
- 批注级反馈组件
- WordPopup 词典反馈
- 应用功能反馈页 + 我的反馈
- 积分明细页
- 个人设置页改造

### Phase 3 — 验证与收尾

- 编译检查
- 手工验证链路

## Test Strategy

- Python: 编译检查新增 schema / route / service
- TypeScript: `tsc --noEmit`
- 手工验证链路：
  - 结果页 👍👎 → 数据库有记录
  - 长按标注 → 反馈选项 → 提交成功
  - WordPopup 反馈按钮 → 词典负面反馈 → 提交成功
  - 应用功能反馈页 → 提交 → 我的反馈列表可见
  - 积分明细页 → 显示 analysis_deduct / feedback_reward / daily_grant
  - 内部 API 标记采纳 → 积分到账 → 积分明细可见

## Open Questions (Resolved)

1. **词典反馈是否需要正面选项**
   → 不需要。词典为静态数据，不需要 LLM 参与，无正例样本需求，仅收集负面反馈用于修正词典数据。

2. **反馈采纳后是否推送通知**
   → 不推送。工具类小程序不应打扰用户，反馈采纳后静音发放奖励积分，用户在积分明细页自然发现。

3. **是否收集联系方式**
   → 不收集。微信小程序合规要求严格，反馈功能非核心服务，联系方式非必要信息。

4. **是否引入 AI 智能标签**
   → 初期不引入。按反馈入口硬编码问题分类枚举即可，后续有需要再扩展。
